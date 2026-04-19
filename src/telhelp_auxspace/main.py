#!/usr/bin/env python3
#
# telhelp_auxspace main.py
#
# InfluxDB Line Protocol timestamp updater,
# plotter and formatter for Auxspace telemetry data.
#
# Simple Python program that converts the relative timestamps
# from the collected telemetry data to absolute ones.
#
# In addition, this can be used as a plotter and formatter for the data as well.
#
# The format:
#   Incoming data has to be in the InfluxDB Line protocol format
#   <https://docs.influxdata.com/influxdb/cloud/reference/syntax/line-protocol/>
#   (see telemetry project's "data.txt")
#
#   <measurement>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]] <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>]
#
#  created  19 Jul 2024
#  by Maximilian Stephan for Auxspace eV.
#

import argparse
import sys

from pathlib import Path
from typing import Union

from telhelp_auxspace.audit import find_flights, parse_audit, shift_audit
from telhelp_auxspace.parser import get_argv
from telhelp_auxspace.plot import plot_data, plot_flights
from telhelp_auxspace.tsupdater import (
    update_timeseries, get_earliest_and_latest_stamp
)
from . import (
    STDOUT_OUTPUT_NOT_SET_SYMBOL, STDOUT_OUTPUT_SYMBOL, PRINT_SECONDS_THRESHHOLD,
)


def _telhelp(args: argparse.Namespace) -> int:
    """
    Main entrypoint for the timestamp updater with parsed commandline args.

    Args:
      args (argparse.Namespace): Parsed commandline arguments

    Returns:
      int: program exit code
    """
    input_file: Path = args.input_file
    output_files: list[Union[Path, str]] = []
    lines: list[str] = []
    timebase: int = args.timebase or 0

    if args.show_only and args.no_show:
        print("--show-only and --no-show are conflicting options. Choose one.")
        return 1

    # Configure which files to send output to.
    if args.output_file in (
        STDOUT_OUTPUT_SYMBOL, STDOUT_OUTPUT_NOT_SET_SYMBOL
    ):
        # If no output file is specified or the user just wants to print to STDOUT,
        # dont parse it as Path object, but a string.
        output_files.append(args.output_file)
    else:
        # If the user specified a path, add it as a Path object.
        output_files.append(Path(args.output_file))

    if args.show_only:
        # If "show-only", don't convert the lines, just read them from input_file
        with open(input_file, mode="r", encoding="UTF-8") as datafile:
            lines = [line for line in datafile.read().splitlines() if line]
    else:
        # But if the option is not specified, update all timeseries data
        lines, timebase = update_timeseries(
            input_file, output_files, args.timebase, args.in_place, args.data_format,
        )
    if not args.no_show:
        # Plot the data if desired
        earliest_stamp, latest_stamp = get_earliest_and_latest_stamp(lines)
        # Add seconds to graph, if the time difference is very small (< 10 mins)
        date_format = (
            '%H:%M:%S' if latest_stamp - earliest_stamp <= PRINT_SECONDS_THRESHHOLD else '%H:%M'
        )
        if args.audit:
            audit_entries = parse_audit(args.audit)
            if args.show_only and not args.timebase:
                print(
                    "--audit with --show-only requires --timebase so the audit "
                    "timestamps can be aligned with the (already absolute) telemetry."
                )
                return 1
            audit_abs = shift_audit(audit_entries, timebase)
            idle_timeout_ms = (
                int(args.idle_timeout * 1_000) if args.idle_timeout is not None else None
            )
            pre_boost_ms = int(args.pre_boost * 1_000)
            flights = find_flights(
                audit_abs,
                idle_timeout_ms=idle_timeout_ms,
                pre_boost_ms=pre_boost_ms,
            )
            plot_flights(lines, flights, date_format)
        else:
            plot_data(lines, date_format)
    return 0


def main() -> int:
    """
    Main entrypoint for the timestamp updater,
    parsing arguments and starting telhelp.

    Returns:
        int: program exit code
    """
    return _telhelp(get_argv())


if __name__ == "__main__":
    sys.exit(main())
