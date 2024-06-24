###############################################################################
# Program generation options
###############################################################################

MAX_EXPRESSION_SIZE = 5
MAX_NESTING_LEVELS = 3
MAX_LINES_IN_BLOCK = 3
ARRAY_SIZE = 10
MAX_SAME_LEVEL_BLOCKS = 2
MATH_FUNC_ALLOWED = True
MATH_FUNC_PROBABILITY = 0.05

###############################################################################
# Compilation options
###############################################################################

# Number of directories per experiment.
# Each directory is a group.
NUM_GROUPS = 2

# Number of tests per group
TESTS_PER_GROUP = 200

# Set of compilers to test.
# COMPILERS is a list containing tuples (x, y), 
# where x is a string with the compiler name, and y is the path to the compiler
# COMPILERS = [("clang_80", "/usr/tce/packages/clang/clang-upstream-2019.03.26/bin/clang"), ("gcc_721", "/usr/tce/packages/gcc/gcc-7.2.1-redhat/bin/gcc"), ("xlc", "/usr/tce/packages/xl/xl-2019.02.07/bin/xlc"), ("nvcc_92", "/usr/tce/packages/cuda/cuda-9.2.148/bin/nvcc")]
# COMPILERS = [("clang_7", "/Users/lagunaperalt1/projects/GPU_work/latest_llvm/llvm-7.0/install/bin/clang"), ("gcc_7", "/opt/local/bin/gcc-mp-7")]
# COMPILERS = [("my_clang", "/usr/tce/packages/clang/clang-ibm-16.0.6-cuda-11.2.0-gcc-8.3.1/bin/clang"), ("my_gcc", "/usr/tcetmp/packages/base-gcc/base-gcc-8.3.1/bin/gcc"), ("my_nvcc", "/usr/tce/packages/cuda/cuda-11.2.0/bin/nvcc")]
# COMPILERS = [("my_clang", "/usr/lib64/ccache/clang"), ("my_gcc", "/usr/tce/bin/gcc"), ("my_hipcc", "/opt/rocm-6.0.3/bin/hipcc")]
# COMPILERS = [("my_clang", "/usr/bin/clang")]
# COMPILERS = [("my_clang", "/usr/bin/clang"), ("my_gcc", "/usr/bin/gcc"), ("my_hipcc", "/opt/rocm-6.0.3/bin/hipcc")]
COMPILERS = [("my_nvcc", "/usr/tce/packages/cuda/cuda-11.2.0/bin/nvcc")]
# COMPILERS = [("my_hipcc", "/opt/rocm-6.0.3/bin/hipcc")]

# Levels of optimization to try
# OPT_LEVELS = [("-O0", 1), ("-O0", 0), ("-O1", 0), ("-O2", 0), ("-O3", 0)]
# OPT_LEVELS = ["-O0", "-O1"]
OPT_LEVELS = [("-O0", 1), ("-O0", 0)]
# OPT_LEVELS = [("-O0", 1)]
# Name of root directory 
TESTS_DIR = "_tests"

###############################################################################
# Running options
###############################################################################

# Number of random inputs per run
INPUT_SAMPLES_PER_RUN = 4

###############################################################################
# Floating-point types
###############################################################################

REAL_TYPE = "double"
# REAL_TYPE = "float"

# Values to skip during divergence checks
SKIP_VALUES = ["nan", "inf"]
# SKIP_VALUES = []
# RECORD_RUNTIME = False
RECORD_RUNTIME = True
