# Varity

**Varity** is a framework to identify variations in floating-point programs through randomized differential testing.
Varity generates random tests that include floating-point operations and compile these tests with different compilers in
a system. It also generates random floating-point inputs for the tests. When tests are executed, the results are
compared to identify variations in the results. Varity helps users of a system to identify the compilers that produce
the most similar results in the system.

## Sample Tests

A random floating-point test in Varity looks like the following code:

 ```c
void compute(double comp, double var_1, double var_2, double var_3, int var_4,
             double var_5, double var_6, double var_7, double var_8,
             double var_9, double var_10, double var_11) {
  if (comp <= -1.8713E305 + cos(-1.8213E-314 + -1.2746E306 * (var_1 * +0.0))) {
    if (comp < var_2 + (+1.9467E212 - -1.5888E-306 - (var_3 / +1.4018E-312))) {
      comp += atan((+1.4283E-306 * log10((+1.0403E-318 / var_5))));
      comp += +1.1409E305 / var_6 *
              (var_7 + sinh((var_8 + +1.8913E306 / (var_9 / -1.0257E-211))));
      for (int i = 0; i < var_4; ++i) {
        comp += (var_10 - var_11 * asin(-1.7743E-310));
        comp += (-1.7207E-199 / (-1.8883E-306 + -1.6191E-318));
      }
    }
  }
  printf("%.17g\n", comp);
}
```

A `compute` function is generated, which takes as arguments floating-point or integer variables. The function body
can contain arithmetic expressions, for loops, conditions, math function calls, and the use of temporal variables.
The function computes a `comp` variables and the value stored in this variable is printed at the end of the test
function.

# Getting Started
 
## Requirements

You will need C compilers, such as clang or gcc, or any other C compiler that you want to test in the system. Other
compilers we have tested successfully are PGI, NVIDIA nvcc, AMD hipcc and the Intel compiler. You will also need Python 3. There
are no other dependencies.

## Using Varity

The main Python script is `varity.py` and is located in the `./varity` directory. For now, the main script should be
executed from that directory.

### Configuration

The main configuration file is `cfg.py`; note that this is a Python file. The following are some of the most important
configuration options:

- `COMPILERS = [(name_1, path_1), (name_2, path_2), ...]`: This is the most important option. It specifies the compiler
  names (name_1, name_2, ...) to test and their paths in the system (path_1, path_2, ...). Names can use
  underscore ('_'), but not dashes ('-'). Paths should be absolute paths.
- `NUM_GROUPS`: Random tests are grouped in different directories. This defines the number of groups (or directories).
  This helps avoiding creating many files in a single directory; if many files per directory is not a problem you can
  use 1.
- `TESTS_PER_GROUP`: Number of tests per group. The total number of generated tests is `NUM_GROUPS*TESTS_PER_GROUP`.
- `INPUT_SAMPLES_PER_RUN`: Number of random inputs per test.
- `REAL_TYPE`: It defines the type for floating-point variables ("float" or "double").
- `SKIP_VALUES`: List of strings representing the values to skip when checking for divergences (e.g., [`nan`, `inf`]).

### Running

After configuring you can simply move to the `varity/` directory and run `python3 varity.py` there. This will execute
three steps: (1) it will generate the random tests; (2) it will compile the tests (producing executables); (3) it will
run the executables with random inputs. If you do this, you should expect to see an output like this:

 ```sh
 $ python3 varity.py 
 Creating dir: mylaptop_22359
 Generating 5 groups, 3 tests... 
 done!
 Compiling tests...
 Total tests to compile:  15
 --> Compiling test: 38
 Total programs:  15
 --> On program: 15
 Saving runs results...
 done
 ```

In this case, Varity created a directory named `mylaptop_22359` to store the results. The name of the directory is
created by joining the hostname, "_", and the process ID of the run. Inside this directory, you will find a file
named `results.json` with the results.

Alternatively, instead of executing the previous three steps inmediately (i.e., test generation, copmilation, and
execution), you can perform these steps separataley using the -g, -c, and -r options; you can see the script options by
running `python3 varity.py -h`:

 ```sh
$ python3 varity.py -h
usage: varity.py [-h] [-g] [-c COMPILE] [-r RUN] [-re RERUN] [-d DIVERGENCE COMPILER_ONE COMPILER_TWO] [-s SUMMARY [SUMMARY ...]]

optional arguments:
  -h, --help            show this help message and exit
  -g, --generate        generate programs
  -c COMPILE, --compile COMPILE
                        compile programs in dir: COMPILE
  -r RUN, --run RUN     run programs in dir: RUN
  -re RERUN, --rerun RERUN
                        run saved programs in dir: RERUN
  -d DIVERGENCE COMPILER_ONE COMPILER_TWO, --divergence DIVERGENCE COMPILER_ONE COMPILER_TWO
                        check divergence in dir: DIVERGENCE using COMPILER_ONE and COMPILER_TWO
  -s SUMMARY [SUMMARY ...], --summary SUMMARY [SUMMARY ...]
                        summarise and make a report in dirs: SUMMARY
 ```

### Results File

The results stored in the `results.json` look like this. The first level
key (`"mylaptop_22359/_tests/_group_1/_test_3.c"`) is the C file with the random test. The second level key is the input
used to execte the test (values are separated by comma). The third level key (`"clang_7"`) is the compiler name. The
fourth level keys are the optimization levels used to compile tests; thei values are the floating-point results of the
tests.

 ```jason
 
 ...{
 "lassen35_50911/_tests/_group_2/_test_98": {
    "-1.1358E305 5 +0.0 -1.9313E-322 +1.7961E51 +1.6731E-307 -1.3933E-316 +1.3544E305 -0.0 +1.4456E-307 -1.1261E-306 +1.4187E305": {
      "my_nvcc": {
        "O0_nofma": "-inf time:294996",
        "O0": "-inf time:302437",
        "O3": "-inf time:296305",
        "O1": "-inf time:312062",
        "O2": "-inf time:308007"
      },
      "my_hipcc": {
        "O1": "-inf time:510588",
        "O2": "-inf time:508802",
        "O0": "-inf time:435790",
        "O0_nofma": "-inf time:430321",
        "O3": "-inf time:426978"
      }
    },
    "+1.7021E-172 5 +1.3000E140 -1.1588E305 +1.7282E-323 +1.1652E-322 +1.3648E-307 +1.3285E-151 +1.1327E305 +1.7402E306 +1.6240E-306 +1.3870E-307": {
      "my_nvcc": {
        "O0_nofma": "6.1500000000003377e+303 time:298396",
        "O0": "6.1500000000003377e+303 time:290039",
        "O3": "6.1500000000003377e+303 time:289967",
        "O1": "6.1500000000003377e+303 time:299895",
        "O2": "6.1500000000003377e+303 time:290125"
      },
      "my_hipcc": {
        "O1": "6.1500000000003377e+303 time:414005",
        "O2": "6.1500000000003377e+303 time:492239",
        "O0": "6.1500000000003377e+303 time:431277",
        "O0_nofma": "6.1500000000003377e+303 time:439891",
        "O3": "6.1500000000003377e+303 time:435288"
      }
    },
    "+1.2364E-307 5 +1.2043E306 -1.9738E-320 -1.3695E-306 +1.4977E-306 -1.7077E-307 +0.0 -0.0 -1.3832E305 -1.8479E306 -1.1078E-59": {
      "my_nvcc": {
        "O0_nofma": "9.9651000000000002e+306 time:288911",
        "O0": "9.9651000000000002e+306 time:289811",
        "O3": "9.9651000000000002e+306 time:290040",
        "O1": "9.9651000000000002e+306 time:341185",
        "O2": "9.9651000000000002e+306 time:288869"
      },
      "my_hipcc": {
        "O1": "9.9651000000000002e+306 time:485105",
        "O2": "9.9651000000000002e+306 time:416223",
        "O0": "9.9651000000000002e+306 time:517683",
        "O0_nofma": "9.9651000000000002e+306 time:501775",
        "O3": "9.9651000000000002e+306 time:477161"
      }
    },
    "+1.8549E305 5 -1.7298E306 +0.0 +0.0 -0.0 -0.0 -1.7260E-319 -1.8361E-318 -0.0 +1.0542E174 -1.2210E306": {
      "my_nvcc": {
        "O0_nofma": "inf time:293873",
        "O0": "inf time:343814",
        "O3": "inf time:282594",
        "O1": "inf time:300848",
        "O2": "inf time:277492"
      },
      "my_hipcc": {
        "O1": "inf time:503403",
        "O2": "inf time:475779",
        "O0": "inf time:478535",
        "O0_nofma": "inf time:520629",
        "O3": "inf time:513008"
      }
    },
    "+1.2611E305 5 +1.9595E-319 -1.6500E-313 +1.7813E87 -1.7812E-307 +1.4791E-197 +1.5034E-320 -1.1871E21 -1.5207E-313 +0.0 +1.5721E-311": {
      "my_nvcc": {
        "O0_nofma": "9.2735000000000005e+306 time:302572",
        "O0": "9.2735000000000005e+306 time:296186",
        "O3": "9.2735000000000005e+306 time:300411",
        "O1": "9.2735000000000005e+306 time:290002",
        "O2": "9.2735000000000005e+306 time:291458"
      },
      "my_hipcc": {
        "O1": "9.2735000000000005e+306 time:452586",
        "O2": "9.2735000000000005e+306 time:453861",
        "O0": "9.2735000000000005e+306 time:491848",
        "O0_nofma": "9.2735000000000005e+306 time:474034",
        "O3": "9.2735000000000005e+306 time:491174"
      }
    }
  },
...
 ```

### Contact

For questions, contact Ignacio Laguna <ilaguna@llnl.gov>.

## Cite

To cite this work, please use:

 ```
 Laguna, Ignacio. "Varity: Quantifying Floating-point Variations in HPC Systems 
 Through Randomized Testing." In 2020 IEEE International Parallel and Distributed 
 Processing Symposium (IPDPS), pp. 622-633. IEEE, 2020.
 ```

## License

Varity is distributed under the terms of the MIT license. All new contributions must be made under the MIT license.

See LICENSE and NOTICE for details.

LLNL-CODE-798680

