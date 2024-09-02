# tsupdater.py
# 
# Timeseries updating tools.
#
#  created  19 Jul 2024
#  by Maximilian Stephan for Auxspace eV.
#

import json
import time

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from telhelp_auxspace.data_format import DataFormat
from . import STDOUT_OUTPUT_NOT_SET_SYMBOL, STDOUT_OUTPUT_SYMBOL


def _update_ts(single_line: str, timebase: int) -> str:
    """
    Update a single line in the InfluxDB Line protocol with an absolute timestamp.

    Args:
      - single_line (str): Input line with relative timestamp
      - timebase (int): timestamp in ms the original timestamp should be relative to.

    Returns:
      str: updated InfluxDB Line protocol string
    """
    timestamp_str: str = ""
    timestamp: int = 0
    elements: list[str] = single_line.split()

    # First, see if there is at least three elements (measurement, fields, timestamp)
    if len(elements) < 3:
        raise ValueError(f"Cannot update timestamp for line {single_line}. No timestamp found.")

    # Remove the last element, since that is the timestamp
    timestamp_str = elements.pop()
    try:
        # Try converting the timestamp to an integer.
        timestamp = int(timestamp_str)
    except ValueError as e:
        raise ValueError(f"Cannot convert timestamp from line {single_line}") from e

    # Add the "relative" timestamp to the given "absolute" timebase
    timestamp += timebase
    timestamp = int(timestamp)

    # Since we popped off the old timestamp, append the new one instead
    elements.append(str(timestamp))

    # Return all elements as a single InfluxDB Line string, seperated by spaces
    return " ".join(elements)


def get_earliest_and_latest_stamp(timeseries: list[str]) -> tuple[int, int]:
    """
    In a list of InfluxDB lines, get the latest timestamp.

    Args:
        timeseries (list[str]): List of InlfuxDB Line Protocol lines

    Returns:
        tuple[int, int]: Earliest and latest timestamp from list.
    """
    ts_strings: list[str] = [ts.split()[-1] for ts in timeseries]
    ts_ints: list[int] = [ 0 for _ in ts_strings ]
    try:
        ts_ints = [int(ts) for ts in ts_strings]
    except ValueError as err:
        print(f"Could not determine max timestamp: {err}")
    return min(ts_ints), max(ts_ints)


def timeseries2str(timeseries: Any, data_format: DataFormat) -> str:
    """
    Create a file writeable string from timeseries data.
    
    Args:
        timeseries (Any): Timeseries data
        data_format (DataFormat): Format of the timeseries source data.

    Returns:
        str: single formatted String to write into a file or STDOUT.
    """
    output: str = ""
    match (data_format):
        case DataFormat.json:
            output = json.dumps(timeseries, indent=4)
        case DataFormat.json_lines:
            output = "\n".join([json.dumps(line) for line in timeseries])
        case DataFormat.csv | DataFormat.multi_csv | DataFormat.influxdb_lines:
            output = "\n".join(timeseries)
        case _:
            print(f"No such DataFormat: {data_format}")
            output = json.dumps(timeseries, indent=4)
    return output


def influxdb_lines_convert(
    _lines: list[str], data_format: DataFormat = DataFormat.influxdb_lines,
) -> Iterable:
    """
    Convert the data from influxdb-line protocol format to the desired format.
    
    Args:
        _lines (list[str]): input in influxdb-line protocol format.
        data_format (DataFormat): Data format of the desired output.
            Defaults to DataFormat.influxdb_lines.

    Returns:
        Any: The data in the desired output format.
            E.g. JSON returns dict[str, Any], whereas csv returns list[str].
    """
    return data_format.convert_lines(_lines)


def update_timeseries(
    input_file: Path,
    output_files: list[Union[Path, str]],
    timebase: Optional[int] = None,
    in_place: bool = False,
    data_format: DataFormat = DataFormat.influxdb_lines,
) -> list[str]:
    """
    Update the timeseries Data from input_file using timebase and put the output into output_files.

    Args:
        input_file (Path): File containing the telemetry data as InfluxDB Lines.
        output_files (list[Union[Path, str]]): list of files to write the converted data to.
        timebase (Optional[int]): Absolute start of the relative timestamps from input_file.
            Defaults to None (auto).
        in_place (bool): Overwrite input_file with updated contents.
            Defaults to False.
        data_format (DataFormat): Data format of the desired output.
            Defaults to DataFormat.influxdb-lines

    Returns:
        list[str]: Converted InfluxDB Lines.
    """
    orig_timeseries: list[str] = []
    updated_timeseries_lines: list[str] = []
    _updated_timeseries_formatted: Iterable = []
    ts_out_str: str = ""
    earliest_stamp: int = 0
    latest_stamp: int = 0

    # Read input file into orig_timeseries as list of strings
    with open(input_file, mode="r", encoding="UTF-8") as datafile:
        orig_timeseries = [line for line in datafile.read().splitlines() if line]

    # Get newest and oldest timestamp
    earliest_stamp, latest_stamp = get_earliest_and_latest_stamp(orig_timeseries)

    # Autogenerate timebase if none is given
    if not timebase:
        timebase = (time.time_ns() // 1e6) - latest_stamp

    earliest_stamp_abs: int = earliest_stamp + timebase
    latest_stamp_abs: int = latest_stamp + timebase

    # Update all timestamps and convert them to a single string
    updated_timeseries_lines = [
        _update_ts(ts, timebase) for ts in orig_timeseries
    ]
    _updated_timeseries_formatted = influxdb_lines_convert(updated_timeseries_lines, data_format)
    ts_out_str = timeseries2str(_updated_timeseries_formatted, data_format)

    # In-place means output = input
    if in_place:
        output_files.append(input_file)

    for output_file in output_files:
        # Write output to file, if specified
        if isinstance(output_file, Path):
            with open(output_file, mode="w", encoding="UTF-8") as outfile:
                outfile.write(ts_out_str)
        # else, write to stdout
        elif isinstance(output_file, str):
            if output_file == STDOUT_OUTPUT_SYMBOL or (
                output_file == STDOUT_OUTPUT_NOT_SET_SYMBOL and not in_place
            ):
                print(ts_out_str)
        # Print state
        print(f"Processed {latest_stamp} ms ({latest_stamp / 1_000 / 60} min) worth of data.")
        print()
        print(f"Oldest stamp is {earliest_stamp_abs} ({datetime.fromtimestamp(earliest_stamp_abs / 1_000)})")
        print(f"Newest stamp is {latest_stamp_abs} ({datetime.fromtimestamp(latest_stamp_abs / 1_000)})")

    return updated_timeseries_lines
