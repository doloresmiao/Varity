import os
import sys
import glob
import subprocess
import time

import gen_inputs
import cfg
import json
import multiprocessing as mp

from type_checking import isTypeReal, isTypeRealPointer

PROG_PER_TEST = {}
PROG_RESULTS = {}
RECORD_RUNTIME = True


def getInputTypes(fullProgName):
    inputFile = fullProgName + ".input"
    with open(inputFile, 'r') as fd:
        types = fd.readlines()[0][:-1].split(",")
    return types


def generateInputs(fullProgName):
    types = getInputTypes(fullProgName)
    ret = ""
    for t in types:
        if isTypeReal(t) or isTypeRealPointer(t):
            i = gen_inputs.InputGenerator.genInput()
            ret = ret + i + " "
        elif t == "int":
            ret = ret + "5 "
    return ret


def getAllTests(fullProgName):
    global PROG_PER_TEST
    base_name = os.path.splitext(fullProgName)[0]
    allTests = [test for test in glob.glob(base_name + "*.exe") if
                os.path.basename(test).startswith(os.path.basename(base_name) + ".")]
    PROG_PER_TEST[base_name] = allTests


def spawnProc(config):
    (cmd, results, lock) = config
    try:
        if RECORD_RUNTIME:
            start_time = time.perf_counter()
            out = subprocess.check_output(cmd, shell=True)
            end_time = time.perf_counter()
            runtime = int((end_time - start_time) * 1e6)  # Calculate runtime in microseconds
        else:
            out = subprocess.check_output(cmd, shell=True)

        res = out.decode('ascii')[:-1]
        lock.acquire()

        if RECORD_RUNTIME:
            results.append(cmd + " " + res + " time:" + str(runtime))
        else:
            results.append(cmd + " " + res)

        lock.release()
    except subprocess.CalledProcessError as outexc:
        print("\nError at runtime:", outexc.returncode, outexc.output)
        print("CMD", cmd)
        exit()


def runTests():
    global PROG_PER_TEST, PROG_RESULTS
    print("Total programs: ", len(PROG_PER_TEST.keys()))
    manager = mp.Manager()
    lock = manager.Lock()
    cpuCount = 16
    c = 1

    for k in PROG_PER_TEST.keys():
        fullProgName = k
        results = manager.list()
        inputsList = []
        for n in range(cfg.INPUT_SAMPLES_PER_RUN):
            inputs = generateInputs(fullProgName)
            for t in PROG_PER_TEST[k]:
                cmd = t + " " + inputs
                config = (cmd, results, lock)
                inputsList.append(config)

        for i in range(0, len(inputsList), cpuCount):
            print("\r--> Running program: {}".format(c), end='')
            sys.stdout.flush()
            workLoad = inputsList[i:i + cpuCount]
            with mp.Pool(cpuCount) as myPool:
                myPool.map(spawnProc, workLoad)

        PROG_RESULTS[k] = results
        c = c + 1
    print("")


def runTestsSerial():
    global PROG_PER_TEST, PROG_RESULTS

    print("Total programs: ", len(PROG_PER_TEST.keys()))
    count = 1
    for base_name in PROG_PER_TEST.keys():

        # --- print progress ---
        print("\r--> On program: {}".format(count), end='')
        sys.stdout.flush()
        count = count + 1

        # ----------------------
        results = []
        for n in range(cfg.INPUT_SAMPLES_PER_RUN):
            inputs = generateInputs(base_name)
            for exe_file in PROG_PER_TEST[base_name]:
                try:
                    cmd = exe_file + " " + inputs
                    if RECORD_RUNTIME:
                        start_time = time.perf_counter()
                        out = subprocess.check_output(cmd, shell=True)
                        end_time = time.perf_counter()
                        runtime = int((end_time - start_time) * 1e6)
                    else:
                        out = subprocess.check_output(cmd, shell=True)

                    res = out.decode('ascii')[:-1]
                    if RECORD_RUNTIME:
                        results.append(exe_file + " " + inputs + " " + res + " time:" + str(runtime))
                    else:
                        results.append(exe_file + " " + inputs + " " + res)

                except subprocess.CalledProcessError as outexc:
                    print("\nError at runtime:", outexc.returncode, outexc.output)
                    print("CMD", cmd)
                    exit()

        PROG_RESULTS[base_name] = results

    print("")


def saveResults(rootDir):
    global PROG_RESULTS

    os.chdir(rootDir)
    with open("./results.json", "w") as f:
        print("{", file=f)
        for k in PROG_RESULTS.keys():
            lastTest = list(PROG_RESULTS.keys())[-1]
            print('  "' + k + '": {', file=f)
            key_input = {}
            for r in PROG_RESULTS[k]:
                if RECORD_RUNTIME:
                    parts = r.split()
                    compiler = parts[0].split('-')[1]
                    opt = parts[0].split('-')[2].split('.')[0]
                    input = " ".join(parts[1:-2])
                    output = parts[-2]
                    runtime = parts[-1]
                else:
                    compiler = r.split()[0].split('-')[1]
                    opt = r.split()[0].split('-')[2].split('.')[0]
                    input = " ".join(r.split()[1:-1])
                    output = r.split()[-1:][0]

                if input in key_input.keys():
                    key_comp = key_input[input]
                    if compiler in key_comp.keys():
                        if RECORD_RUNTIME:
                            key_input[input][compiler][opt] = output + " " + runtime
                        else:
                            key_input[input][compiler][opt] = output
                    else:
                        if RECORD_RUNTIME:
                            key_input[input][compiler] = {opt: output + " " + runtime}
                        else:
                            key_input[input][compiler] = {opt: output}
                else:
                    if RECORD_RUNTIME:
                        key_input[input] = {compiler: {opt: output + " " + runtime}}
                    else:
                        key_input[input] = {compiler: {opt: output}}

            for i in key_input.keys():
                lastInput = list(key_input.keys())[-1]
                print('    "' + i + '": {', file=f)
                for c in key_input[i].keys():
                    lastComp = list(key_input[i].keys())[-1]
                    print('      "' + c + '": {', file=f)
                    for o in key_input[i][c].keys():
                        val = key_input[i][c][o]
                        lastOpt = list(key_input[i][c].keys())[-1]
                        line = '        "' + o + '": "' + val
                        if o != lastOpt:
                            print(line + '",', file=f)
                        else:
                            print(line + '"', file=f)
                    if c != lastComp:
                        print('      },', file=f)
                    else:
                        print('      }', file=f)
                if i != lastInput:
                    print('    },', file=f)
                else:
                    print('    }', file=f)
            if k != lastTest:
                print('  },', file=f)
            else:
                print('  }', file=f)
        print("}", file=f)


def run(dir):
    global PROG_PER_TEST

    for dirName, subdirList, fileList in os.walk(dir):
        for fname in fileList:
            if fname.endswith('.c'):
                fullPath = dirName + "/" + fname
                getAllTests(fullPath)
    runTestsSerial()
    print("Saving runs results...")
    saveResults(dir)
    print("done")


def saved_run(dir):
    global PROG_PER_TEST

    results_file = os.path.join(dir, "results.json")
    if not os.path.exists(results_file):
        print("No results saved. Run the basic -r!")
        return

    with open(results_file, "r") as f:
        saved_results = json.load(f)

    print("Looking for new executables...")

    for dirName, subdirList, fileList in os.walk(dir):
        for fname in fileList:
            if fname.endswith('.c'):
                fullPath = dirName + "/" + fname
                getAllTests(fullPath)

    for fullProgName in PROG_PER_TEST.keys():
        if fullProgName not in saved_results:
            continue

        for t in PROG_PER_TEST[fullProgName]:
            base_name = fullProgName.split("-")[0]
            compiler_name = t.split("-")[1]
            opt_level = t.split("-")[2].split(".")[0]

            inputsList = []
            for input_vals in saved_results[base_name].keys():
                if compiler_name in saved_results[base_name][input_vals]:
                    if opt_level in saved_results[base_name][input_vals][compiler_name]:
                        continue
                cmd = t + " " + input_vals
                inputsList.append((cmd, input_vals))

            manager = mp.Manager()
            results = manager.list()
            lock = manager.Lock()

            cpuCount = mp.cpu_count()
            for i in range(0, len(inputsList), cpuCount):
                workLoad = inputsList[i:i + cpuCount]
                with mp.Pool(cpuCount) as myPool:
                    myPool.map(spawnProc, [(cmd, results, lock) for cmd, _ in workLoad])

            for cmd, input_vals in inputsList:
                for result in results:
                    if cmd in result:
                        if RECORD_RUNTIME:
                            parts = result.split(" ")
                            res = parts[-2] + " " + parts[-1]
                        else:
                            res = result.split(" ")[-1]

                        if input_vals not in saved_results[base_name]:
                            saved_results[base_name][input_vals] = {}
                        if compiler_name not in saved_results[base_name][input_vals]:
                            saved_results[base_name][input_vals][compiler_name] = {}
                        saved_results[base_name][input_vals][compiler_name][opt_level] = res

    with open(results_file, "w") as f:
        json.dump(saved_results, f, indent=2)

    print("The results.json is updated successfully after rerunning on different machine!")


def check_divergence(folder_path, compiler_one, compiler_two):
    results_file = os.path.join(folder_path, "results.json")
    divergences_file = os.path.join(folder_path, "divergences.json")

    if not os.path.exists(results_file):
        print("No results.json found in the specified folder!")
        return

    with open(results_file, "r") as f:
        results = json.load(f)

    print("Looking for the differences...")

    divergences = {}
    compiler_one_missing = True
    compiler_two_missing = True

    for base_name, inputs in results.items():
        for input_vals, compilers in inputs.items():
            if compiler_one in compilers:
                compiler_one_missing = False
            if compiler_two in compilers:
                compiler_two_missing = False
            if not compiler_one_missing and not compiler_two_missing:
                break
        if not compiler_one_missing and not compiler_two_missing:
            break

    if compiler_one_missing:
        print(f"Compiler {compiler_one} is missing in the results.json!")
        return

    if compiler_two_missing:
        print(f"Compiler {compiler_two} is missing in the results.json!")
        return

    for base_name, inputs in results.items():
        for input_vals, compilers in inputs.items():
            if compiler_one in compilers and compiler_two in compilers:
                for opt_level in compilers[compiler_one]:
                    if opt_level in compilers[compiler_two]:
                        result_one = compilers[compiler_one][opt_level]
                        result_two = compilers[compiler_two][opt_level]
                        if RECORD_RUNTIME:
                            parts_one = result_one.rsplit(" ", 1)
                            parts_two = result_two.rsplit(" ", 1)
                            output_one = parts_one[0]
                            output_two = parts_two[0]
                        else:
                            output_one = result_one
                            output_two = result_two

                        if output_one != output_two:
                            if base_name not in divergences:
                                divergences[base_name] = {}
                            if input_vals not in divergences[base_name]:
                                divergences[base_name][input_vals] = {}
                            if compiler_one not in divergences[base_name][input_vals]:
                                divergences[base_name][input_vals][compiler_one] = {}
                            if compiler_two not in divergences[base_name][input_vals]:
                                divergences[base_name][input_vals][compiler_two] = {}
                            divergences[base_name][input_vals][compiler_one][opt_level] = result_one
                            divergences[base_name][input_vals][compiler_two][opt_level] = result_two

    with open(divergences_file, "w") as f:
        json.dump(divergences, f, indent=2)

    print("Divergences saved to divergences.json!")


def report_discrepancies(dir):
    divergences_file = os.path.join(dir, "divergences.json")
    if not os.path.exists(divergences_file):
        print("No divergences.json found in the specified folder. Run the divergence analysis first.")
        return

    with open(divergences_file, "r") as f:
        divergences = json.load(f)

    total_programs = len(glob.glob(os.path.join(dir, '**/*.c'), recursive=True))
    total_bugs = sum(len(inputs) for inputs in divergences.values())

    report = []
    report.append("Discrepancy Report\n")
    report.append("Summary\n")
    report.append(f"Total number of programs: {total_programs}\n")
    report.append(f"Total number of bugs found: {total_bugs}\n\n")

    for base_name, inputs in divergences.items():
        test_folder = os.path.dirname(base_name)
        test_file = os.path.basename(base_name)

        c_file_path = os.path.join(test_folder, test_file + ".c")
        cu_file_path = os.path.join(test_folder, test_file + ".cu")
        hip_file_path = os.path.join(test_folder, test_file + ".hip")

        report.append(f"\nTest: {test_file}\n\n")

        with open(c_file_path, "r") as f:
            report.append(f"Content of {test_file}.c:\n" + f.read() + "\n\n")
        if os.path.exists(cu_file_path):
            with open(cu_file_path, "r") as f:
                report.append(f"Content of {test_file}.cu:\n" + f.read() + "\n\n")
        if os.path.exists(hip_file_path):
            with open(hip_file_path, "r") as f:
                report.append(f"Content of {test_file}.hip:\n" + f.read() + "\n\n")

        for input_vals, compilers in inputs.items():
            report.append(f"\nInput: {input_vals}\n")

            report.append("Compiler | Optimization | Result\n")
            report.append("-" * 40 + "\n")
            for compiler, optimizations in compilers.items():
                for opt_level, result in optimizations.items():
                    report.append(f"{compiler} | {opt_level} | {result}\n\n")

    with open(os.path.join(dir, "discrepancy_report.txt"), "w") as f:
        f.writelines(report)

    print("Discrepancy report generated and saved as discrepancy_report.txt.")


if __name__ == "__main__":
    d = sys.argv[1]
    run(d)
