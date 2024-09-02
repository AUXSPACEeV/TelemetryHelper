# telhelp_auxspace
#
# Common variables, classes and functions.
#
#  created 02 Sep 2024
#  by Maximilian Stephan for Auxspace eV.
#

# Symbol to set output to STDOUT instead of a file.
# This can be used by the user as an argument.
STDOUT_OUTPUT_SYMBOL: str = '-'
# Symbol to clarify, that the user did not set any special output file.
STDOUT_OUTPUT_NOT_SET_SYMBOL: str = ''

# Time-difference of earliest and latest timestamp in seconds
# at which the timestamps are displayed as %H%M%S instead of %H%M
PRINT_SECONDS_THRESHHOLD: int = 60 * 10  # 10 minutes
