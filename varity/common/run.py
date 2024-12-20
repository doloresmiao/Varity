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
RECORD_RUNTIME = cfg.RECORD_RUNTIME


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
    if RECORD_RUNTIME:
        (cmd, results, lock, batch_runtime) = config
        compiler_name = cmd.split()[0].split('-')[1]
    else:
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

        try:
            if RECORD_RUNTIME:
                if compiler_name not in batch_runtime:
                    batch_runtime[compiler_name] = 0
                batch_runtime[compiler_name] += runtime
                results.append(cmd + " " + res + " time:" + str(runtime))
            else:
                results.append(cmd + " " + res)
        finally:
            lock.release()

    except subprocess.CalledProcessError as outexc:
        print("\nError at runtime:", outexc.returncode, outexc.output.decode('ascii'))
        print("CMD", cmd)
        exit(1)


def runTests():
    global PROG_PER_TEST, PROG_RESULTS
    print("Total programs: ", len(PROG_PER_TEST.keys()))
    manager = mp.Manager()
    lock = manager.Lock()
    cpuCount = 16
    c = 1
    batch_runtime = manager.dict()

    for k in PROG_PER_TEST.keys():
        fullProgName = k
        results = manager.list()
        inputsList = []
        for n in range(cfg.INPUT_SAMPLES_PER_RUN):
            inputs = generateInputs(fullProgName)
            for t in PROG_PER_TEST[k]:
                cmd = t + " " + inputs
                if RECORD_RUNTIME:
                    config = (cmd, results, lock, batch_runtime)
                else:
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
    return dict(batch_runtime)


def runTestsSerial():
    global PROG_PER_TEST, PROG_RESULTS

    print("Total programs: ", len(PROG_PER_TEST.keys()))
    count = 1
    batch_runtime = {}

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
                        compiler_name = cmd.split()[0].split('-')[1]
                        if compiler_name not in batch_runtime:
                            batch_runtime[compiler_name] = 0
                        batch_runtime[compiler_name] += runtime

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
    return batch_runtime


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


def saveRunData(rootDir, batch_runtime=None, rerun=False):
    num_groups = cfg.NUM_GROUPS
    tests_per_group = cfg.TESTS_PER_GROUP
    input_samples_per_run = cfg.INPUT_SAMPLES_PER_RUN
    total_programs = num_groups * tests_per_group
    total_runs = total_programs * input_samples_per_run

    user = os.getenv('USER') or os.getenv('USERNAME')
    if not user:
        user = "Unknown User"

    compilers = {name: path for name, path in cfg.COMPILERS}
    optimization = cfg.OPT_LEVELS

    if batch_runtime:
        batch_runtime_minutes = {compiler: runtime / (60 * 1e6) for compiler, runtime in batch_runtime.items()}
    else:
        batch_runtime_minutes = {}

    run_data = {
        "Number of groups": num_groups,
        "Tests per group": tests_per_group,
        "Input samples per run": input_samples_per_run,
        "Total programs": total_programs,
        "Total runs": total_runs,
        "Directory name": rootDir,
        "Compilers": compilers,
        "Optimization": optimization,
        "Batch Runtime (minutes)": batch_runtime_minutes,
        "Created By": user,
        "Created at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "Last Modified By": "",
        "Last Modified at": "",
    }

    if not rerun:
        run_data_file = os.path.join(os.getcwd(), "run_data.json")
    else:
        run_data_file = os.path.join(os.getcwd(), rootDir, "run_data.json")

    if os.path.exists(run_data_file):
        with open(run_data_file, "r") as f:
            existing_data = json.load(f)

        existing_data["Last Modified By"] = user
        existing_data["Last Modified at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        existing_compilers = existing_data.get("Compilers", {})
        for compiler, path in compilers.items():
            if compiler not in existing_compilers:
                existing_compilers[compiler] = path

        existing_data["Compilers"] = existing_compilers
        existing_data["Optimization"] = optimization
        if batch_runtime_minutes:
            existing_data["Batch Runtime (minutes)"].update(batch_runtime_minutes)
        run_data = existing_data

    with open(run_data_file, "w") as f:
        json.dump(run_data, f, indent=2)

    print("Run-data saved to run_data.json!")


def run(dir):
    global PROG_PER_TEST

    for dirName, subdirList, fileList in os.walk(dir):
        for fname in fileList:
            if fname.endswith('.c'):
                fullPath = dirName + "/" + fname
                getAllTests(fullPath)
    batch_runtime = runTestsSerial()
    print("Saving runs results...")
    saveResults(dir)
    saveRunData(dir, batch_runtime=batch_runtime)
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

    manager = mp.Manager()
    lock = manager.Lock()
    batch_runtime = manager.dict()
    cpuCount = mp.cpu_count()

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

            results = manager.list()
            for i in range(0, len(inputsList), cpuCount):
                workLoad = inputsList[i:i + cpuCount]
                with mp.Pool(cpuCount) as myPool:
                    if RECORD_RUNTIME:
                        myPool.map(spawnProc, [(cmd, results, lock, batch_runtime) for cmd, _ in workLoad])
                    else:
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

    saveRunData(dir, batch_runtime=dict(batch_runtime), rerun=True)
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

    skip = cfg.SKIP_VALUES

    def is_skipped_value(first_op, second_op):
        if first_op == "0" and second_op == "-0":
            return True
        if first_op == "-0" and second_op == "0":
            return True
        if first_op == "nan" and second_op == "-nan":
            return True
        if first_op == "-nan" and second_op == "nan":
            return True
        if first_op == "inf" and second_op == "-inf":
            return True
        if first_op == "-inf" and second_op == "inf":
            return True
        return False

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

                        if skip and is_skipped_value(output_one, output_two):
                            continue

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


def categorize_discrepancy(output_one, output_two):
    def categorize(value):
        value_lower = value.lower()
        if value_lower in ["nan", "-nan"]:
            return "nan"
        elif value_lower in ["inf", "+inf", "-inf"]:
            return "inf"
        elif value_lower == "0" or value_lower == "-0":
            return "zero"
        else:
            return "num"

    category_one = categorize(output_one)
    category_two = categorize(output_two)

    if (category_one == "nan" and category_two == "inf") or (category_one == "inf" and category_two == "nan"):
        return "nan_vs_inf", category_one, category_two
    elif (category_one == "nan" and category_two == "zero") or (category_one == "zero" and category_two == "nan"):
        return "nan_vs_zero", category_one, category_two
    elif (category_one == "nan" and category_two == "num") or (category_one == "num" and category_two == "nan"):
        return "nan_vs_num", category_one, category_two
    elif (category_one == "inf" and category_two == "zero") or (category_one == "zero" and category_two == "inf"):
        return "inf_vs_zero", category_one, category_two
    elif (category_one == "inf" and category_two == "num") or (category_one == "num" and category_two == "inf"):
        return "inf_vs_num", category_one, category_two
    elif (category_one == "num" and category_two == "zero") or (category_one == "zero" and category_two == "num"):
        return "num_vs_zero", category_one, category_two
    else:
        return "num_vs_num", "num1", "num2"


def report_discrepancies(dirs):
    report_lines = []
    header = "Base name with input\t\t\tCompiler\tOption\t\tResult\t\t\tTime\n"
    separator = "-" * 120 + "\n"
    report_lines.append(header)
    report_lines.append(separator)

    total_programs = 0
    total_runs = 0
    total_discrepancies = 0
    discrepancies_per_option = {}
    divergences = {}
    compilers_set = set()

    for dir in dirs:
        divergences_file = os.path.join(dir, "divergences.json")
        run_data_file = os.path.join(dir, "run_data.json")

        if not os.path.exists(divergences_file):
            print(f"No divergences found in {dir}")
            continue

        with open(divergences_file, "r") as f:
            divergences.update(json.load(f))

        if os.path.exists(run_data_file):
            with open(run_data_file, "r") as f:
                run_data = json.load(f)
                total_programs += run_data.get("Total programs", 0)
                total_runs += run_data.get("Total runs", 0)

        for base_name, inputs in divergences.items():
            for input_vals, compilers in inputs.items():
                full_base_name_with_input = f"{base_name} {input_vals}"
                report_lines.append(f"{full_base_name_with_input}\n")
                grouped_by_option = {}
                for compiler, options in compilers.items():
                    compilers_set.add(compiler)
                    for opt, result in options.items():
                        if opt not in grouped_by_option:
                            grouped_by_option[opt] = []
                        result_parts = result.split(" time:")
                        output = result_parts[0]
                        run_time = result_parts[1] if len(result_parts) > 1 else "N/A"
                        grouped_by_option[opt].append((compiler, output, run_time))

                for opt, entries in grouped_by_option.items():
                    if opt not in discrepancies_per_option:
                        discrepancies_per_option[opt] = {
                            "total": 0,
                            "nan_vs_inf": {"total": 0, "nan": {compiler: 0 for compiler in compilers_set},
                                           "inf": {compiler: 0 for compiler in compilers_set}},
                            "nan_vs_zero": {"total": 0, "nan": {compiler: 0 for compiler in compilers_set},
                                            "zero": {compiler: 0 for compiler in compilers_set}},
                            "nan_vs_num": {"total": 0, "nan": {compiler: 0 for compiler in compilers_set},
                                           "num": {compiler: 0 for compiler in compilers_set}},
                            "inf_vs_zero": {"total": 0, "inf": {compiler: 0 for compiler in compilers_set},
                                            "zero": {compiler: 0 for compiler in compilers_set}},
                            "inf_vs_num": {"total": 0, "inf": {compiler: 0 for compiler in compilers_set},
                                           "num": {compiler: 0 for compiler in compilers_set}},
                            "num_vs_zero": {"total": 0, "num": {compiler: 0 for compiler in compilers_set},
                                            "zero": {compiler: 0 for compiler in compilers_set}},
                            "num_vs_num": {"total": 0, "num1": {compiler: 0 for compiler in compilers_set},
                                           "num2": {compiler: 0 for compiler in compilers_set}},
                        }

                    discrepancies_per_option[opt]["total"] += len(entries)
                    total_discrepancies += len(entries)

                    for idx, (compiler, output, run_time) in enumerate(entries):
                        if idx == 0:
                            report_lines.append(f"\t\t\t{compiler}\t{opt}\t\t{output}\t\t\t{run_time}\n")
                        else:
                            report_lines.append(f"\t\t\t{compiler}\t{opt}\t\t{output}\t\t\t{run_time}\n")

                        if idx > 0:
                            previous_compiler, previous_output, _ = entries[idx - 1]
                            category, cat_one, cat_two = categorize_discrepancy(previous_output, output)
                            discrepancies_per_option[opt][category]["total"] += 1
                            discrepancies_per_option[opt][category][cat_one][previous_compiler] += 1
                            discrepancies_per_option[opt][category][cat_two][compiler] += 1
                            if category == "num_vs_num":
                                discrepancies_per_option[opt][category][cat_two][previous_compiler] += 1
                                discrepancies_per_option[opt][category][cat_one][compiler] += 1
                                
                report_lines.append(separator)
            report_lines.append(separator)

    total_discrepancies //= 2
    discrepancies_per_option = {opt: {**val, "total": val["total"] // 2} for opt, val in
                                discrepancies_per_option.items()}

    number_of_compilers = len(compilers_set)

    summary = {
        "Total Programs": total_programs,
        "Total Runs per Option per Compiler": total_runs,
        "Total Runs per Option": total_runs * number_of_compilers,
        "Total Runs": total_runs * number_of_compilers * len(discrepancies_per_option),
        "Total Discrepancies": total_discrepancies,
        "Discrepancies per Option": discrepancies_per_option,
        "Discrepancies": divergences
    }

    report_file = "discrepancy_report.txt"
    with open(report_file, "w") as f:
        f.writelines(report_lines)

    summary_file = "discrepancy_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Discrepancy report generated and saved as {report_file}.")
    print(f"Discrepancy summary generated and saved as {summary_file}.")


if __name__ == "__main__":
    d = sys.argv[1]
    run(d)
