import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'common')))

# Varity modules
import gen_program
import cfg
import run
import type_checking

# Python modules
import subprocess
import socket
import multiprocessing as mp
import argparse


def writeProgramCode(fileName):
    # Write C code
    p = gen_program.Program()
    (code, allTypes) = p.printCode()
    writeInputFile(fileName, allTypes)
    with open(fileName, "w") as f:
        f.write(code)

    # Write CUDA code
    (code, allTypes) = p.printCode(True)
    with open(fileName + "u", "w") as f:
        f.write(code)

    # Write HIP code
    (code, allTypes) = p.printCode(True, hip=True)
    with open(fileName.replace(".c", ".hip"), "w") as f:
        f.write(code)


def writeInputFile(fileName, allTypes):
    input_file_name = fileName.rsplit(".", 1)[0] + ".input"
    with open(input_file_name, "w") as f:
        f.write(type_checking.getTypeString() + ",")
        f.write(allTypes + "\n")


def isCUDACompiler(compiler_name):
    return "nvcc" in compiler_name


def isHIPCompiler(compiler_name):
    return "hipcc" in compiler_name


def getExtraOptimization(compiler_name, e: int):
    ret = ""
    if "clang" in compiler_name:
        if e == 1:
            ret = "-ffp-contract=off"
        ret = ret + " -std=c99"
    elif "gcc" in compiler_name:
        if e == 1:
            ret = "-ffp-contract=off"
        ret = ret + " -std=c99"
    elif "pgi" in compiler_name:
        if e == 1:
            ret = "-nofma"
        ret = ret + " -c99"
    elif "nvcc" in compiler_name:
        if e == 1:
            ret = "--fmad=false"
        ret = ret + " -arch=sm_60"
    elif "xlc" in compiler_name:
        if e == 1:
            ret = "-qfloat=nomaf"
    elif "hipcc" in compiler_name:
        if e == 1:
            ret = "--amdgpu-no-fma"
        ret = ret + " --amdgpu-target=gfx906"

    return ret


def compileCode(config):
    (compiler_name, compiler_path, op_level, other_op, dirName, fileName) = config
    try:
        pwd = os.getcwd()
        os.chdir(dirName)
        libs = " -lm "
        more_ops = getExtraOptimization(compiler_name, other_op)
        extra_name = ""
        if other_op == 1:
            extra_name = "_nofma"

        if isCUDACompiler(compiler_name):
            fileName = fileName + "u"

        if isHIPCompiler(compiler_name):
            fileName = fileName.replace(".c", ".hip")

        compilation_arguments = [compiler_path, op_level, more_ops, libs, "-o",
                                 fileName + "-" + compiler_name + op_level + extra_name + ".exe", fileName]
        cmd = " ".join(compilation_arguments)
        
        out = subprocess.check_output(cmd, shell=True)
        os.chdir(pwd)
    except subprocess.CalledProcessError as outexc:
        print("Error at compile time:", outexc.returncode, outexc.output)
        print("FAILED: ", cmd)


def generateTests():
    dir = getTargetDirectory()
    print("Generating {} groups, {} tests... ".format(cfg.NUM_GROUPS, cfg.TESTS_PER_GROUP))
    fileNameList = []
    for g in range(cfg.NUM_GROUPS):
        # Create directory
        p = dir + "/" + cfg.TESTS_DIR + "/_group_" + str(g + 1)
        try:
            os.makedirs(p)
        except FileExistsError:
            pass  # directory already exists

        # Write the program source code
        for t in range(cfg.TESTS_PER_GROUP):
            fileName = p + "/_test_" + str(t + 1) + ".c"
            fileNameList.append(fileName)

    cpuCount = mp.cpu_count()
    for i in range(0, len(fileNameList), cpuCount):
        workLoad = fileNameList[i:i + cpuCount]
        with mp.Pool(cpuCount) as myPool:
            myPool.map(writeProgramCode, workLoad)
            # writeProgramCode(fileName)
    print("done!")
    return dir


def compileTests(path):
    print("Compiling tests...")
    print("Total tests to compile: ", cfg.NUM_GROUPS * cfg.TESTS_PER_GROUP)

    # Check if the compilers exist
    existing_compilers = []
    for compiler_name, compiler_path in cfg.COMPILERS:
        if os.path.exists(compiler_path):
            existing_compilers.append((compiler_name, compiler_path))
            print(f"\033[92mCompiler {compiler_name} with path {compiler_path} exists and will be used.\033[0m")
        else:
            print(
                f"\033[1;91mCompiler {compiler_name} with path {compiler_path} does not exist and will be skipped.\033[0m")

    compileConfigList = []
    for g in range(cfg.NUM_GROUPS):
        p = path + "/" + cfg.TESTS_DIR + "/_group_" + str(g + 1)
        for t in range(cfg.TESTS_PER_GROUP):
            fileName = "_test_" + str(t + 1) + ".c"
            for c in existing_compilers:
                compiler_name = c[0]
                compiler_path = c[1]
                for opts in cfg.OPT_LEVELS:
                    (op, other_op) = opts
                    config = (compiler_name, compiler_path, op, other_op, p, fileName)
                    compileConfigList.append(config)

    cpuCount = mp.cpu_count()
    for i in range(0, len(compileConfigList), cpuCount):
        print("\r--> Compiling test: {}".format(int(i / cpuCount) + 1), end='')
        sys.stdout.flush()
        workLoad = compileConfigList[i:i + cpuCount]
        with mp.Pool(cpuCount) as myPool:
            myPool.map(compileCode, workLoad)

    print("")


def dirName():
    return socket.gethostname() + "_" + str(os.getpid())


def getTargetDirectory():
    p = dirName()
    print("Creating dir:", p)
    try:
        os.mkdir(p)
    except OSError:
        print("Creation of the directory %s failed" % p)
        exit()
    return p


def runTests(dir):
    # p = getTargetDirectory()
    # cfg.TESTS_DIR = p + "/" + cfg.TESTS_DIR
    # p = dir
    run.run(dir)


def saved_run(dir):
    run.saved_run(dir)


def check_divergence(dir, compiler_one, compiler_two):
    run.check_divergence(dir, compiler_one, compiler_two)


def get_summary(dirs):
    run.report_discrepancies(dirs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--generate", help="generate programs", action="store_true")
    parser.add_argument("-c", "--compile", type=str, help="compile programs in dir: COMPILE")
    parser.add_argument("-r", "--run", type=str, help="run programs in dir: RUN")
    parser.add_argument("-re", "--rerun", type=str, help="run saved programs in dir: RERUN")
    parser.add_argument("-d", "--divergence", nargs=3, metavar=("DIVERGENCE", "COMPILER_ONE", "COMPILER_TWO"),
                        help="check divergence in dir: DIVERGENCE using COMPILER_ONE and COMPILER_TWO")
    parser.add_argument("-s", "--summary", nargs='+', help="summarise and make a report in dirs: SUMMARY")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        working_directory = generateTests()
        compileTests(working_directory)
        runTests(working_directory)
    else:
        if args.generate:
            generateTests()
        if args.compile:
            compileTests(args.compile)
        if args.run:
            runTests(args.run)
        if args.rerun:
            saved_run(args.rerun)
        if args.divergence:
            divergence_dir, compiler_one, compiler_two = args.divergence
            check_divergence(divergence_dir, compiler_one, compiler_two)
        if args.summary:
            get_summary(args.summary)


if __name__ == '__main__':
    main()
