import argparse

from pathlib import Path

from telhelp_auxspace.data_format import DataFormat
from . import STDOUT_OUTPUT_NOT_SET_SYMBOL


def get_argv() -> argparse.Namespace:
    """
    Return arguments from the commandline.
    """
    # Setup the argument parser and parse args
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path of data.txt with telemetry data.",
    )
    parser.add_argument(
        "--timebase",
        type=int,
        default=None,
        help="Absolute timestamp in ms to add to all relative timestamps from the input file. "
        "If none is specified, the current time is used (last timestamp -> current timestamp).",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Replace timestamps in the input file directly, without creating a new one. "
        "Combining this option with --output-file results in both the original file being modified "
        "and the output being written to the desired output file.",
    )
    parser.add_argument(
        "--data-format",
        type=DataFormat,
        choices=list(DataFormat),
        default=DataFormat.influxdb_lines,
        help="Specify the format of the data to output."
        "Defaults to 'influxdb-line'.",
    )
    parser.add_argument(
        "--show-only",
        action="store_true",
        help="Only show data, don't convert it. Conflicts with --no-show."
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not show data. Conflicts with --show-only."
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        default=STDOUT_OUTPUT_NOT_SET_SYMBOL,
        help="Specify the Path for the output file. Leave blank or set '-' to display output on STDOUT.",
    )
    return parser.parse_args()
