# data_format.py
# 
# Data formats and conversion functions.
#
#  created 02 Sep 2024
#  by Maximilian Stephan for Auxspace eV.
#

from enum import Enum
from typing import Any, Iterable, Optional


class DataFormat(Enum):
    """Output Data Formats."""
    json = "json"
    json_lines = "json-lines"
    csv = "csv"
    multi_csv = "multi-csv"
    influxdb_lines = "influxdb-lines"
    
    @staticmethod
    def _convert_json(_lines: list[str]) -> dict[str, dict[str, list[dict[str, Any]]]]:
        """Convert the data structure from InfluxDB Lines into JSON syntax.

        Args:
            _lines (list[str]): Data as InfluxDB Lines

        Returns:
            dict[str, Any]: JSON syntaxed line data. E.g:
                {
                    "dps310": {
                        "pressure": [
                            {
                                "value": 972.715,
                                "timestamp": 1725197514418
                            },
                        ],
                        "temp": [
                            {
                                "value": 35.769,
                                "timestamp": 1725197514418
                            },
                        ],
                    },
                    "bno08x": {
                        "accel_x": [
                            {
                                "value": 0.496094,
                                "timestamp": 1725197514509
                            },
                        ],
                        "accel_y": [
                            {
                                "value": -9.72656,
                                "timestamp": 1725197514509
                            },
                        ],
                        "accel_z": [
                            {
                                "value": 0.304688,
                                "timestamp": 1725197514509
                            },
                        ],
                    },
                }
        """
        output: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for line in _lines:
            measurement, fields, timestamp = parse_influxdb_line(line)
            if not output.get(measurement):
                output[measurement] = {}
            for key, value in fields.items():
                if not output[measurement].get(key):
                    output[measurement][key] = []
                field_dict = {
                    "value": value,
                    "timestamp": timestamp,
                }
                output[measurement][key].append(field_dict)
        return output

    @staticmethod
    def _convert_jsonlines(_lines: list[str]) -> list[dict[str, Any]]:
        """Convert the data structure from InfluxDB Lines into JSON Lines.

        Args:
            _lines (list[str]): Data as InfluxDB Lines

        Returns:
            list[dict[str, Any]]: JSONL syntaxed line data list. E.g:
                [
                    {
                        "measurement": "dps310",
                        "fields": {
                            "pressure": 972.715,
                            "temp": 35.769,
                        },
                        "timestamp": 1725197542829,
                    },
                    {
                        "measurement": "bno08x",
                        "fields": {
                            "accel_z": 0.304688,
                            "accel_x": 0.496094,
                            "accel_y": -9.72656,
                        },
                        "timestamp": 1725197542920,
                    },
                ]
        """
        output: list[dict[str, Any]] = []
        for line in _lines:
            measurement, fields, timestamp = parse_influxdb_line(line)
            json_line = {
                "measurement": measurement,
                "fields": fields,
                "timestamp": timestamp,
            }
            output.append(json_line)
        return output

    @staticmethod
    def _convert_csv(_lines: list[str]) -> list[str]:
        """Convert the data structure from InfluxDB Lines into CSV syntax.

        Args:
            _lines (list[str]): Data as InfluxDB Lines

        Returns:
            list[dict[str, Any]]: CSV syntaxed line data list with one header. E.g:
                [
                    "dps310_pressure,dps310_temp,bno08x_accel_z,bno08x_accel_x,bno08x_accel_y,timestamp",
                    "972.715,35.769,,,,1725197552414",
                    ",,0.304688,0.496094,-9.72656,1725197552505",
                ]
        """
        output: list[str] = []
        jsonline_data: list[dict[str, Any]] = DataFormat._convert_jsonlines(_lines)
        csv_dict_lines: list[dict[str, Any]] = []
        csv_header_names: list[str] = []

        # First find out about header names and their data
        for line in jsonline_data:
            fields: dict[str, Any] = line["fields"]
            data_line: dict[str, Any] = {
                "timestamp": line["timestamp"],
            }
            for field, value in fields.items():
                csv_header_name = f'{line["measurement"]}_{field}'
                if csv_header_name not in csv_header_names:
                    csv_header_names.append(csv_header_name)
                data_line[csv_header_name] = value
            csv_dict_lines.append(data_line)

        # Then add the header
        csv_header: str = f'{",".join(csv_header_names)},timestamp'
        output.append(csv_header)

        # At last, fill in the data in the right format (sorted by timestamp)
        for line in sorted(csv_dict_lines, key=lambda l: l["timestamp"]):
            local_keys: list[str] = line.keys()
            # Fill in the missing metrics with ""
            for name in csv_header_names:
                if name not in local_keys:
                    line[name] = ""
            data: str = ",".join([ str(line[name]) for name in csv_header_names ])
            output.append(f'{data},{line["timestamp"]}')
        return output

    @staticmethod
    def _convert_csv_multiline(_lines: list[str]):
        """Convert the data structure from InfluxDB Lines into CSV syntax.

        Args:
            _lines (list[str]): Data as InfluxDB Lines

        Returns:
            list[dict[str, Any]]: CSV syntaxed line data list with multiple headers. E.g:
                [
                    "pressure,temp,timestamp",
                    "972.715,35.769,1725197597376",
                    "972.713,35.7713,1725197597568",
                    "",
                    "accel_x,accel_y,accel_z,timestamp",
                    "0.496094,-9.72656,0.304688,1725197597467",
                    "0.726563,-9.88672,-0.152344,1725197597628",
                ]
        """
        output: list[str] = []
        csv_multi: dict[str, Any] = __influxdb_line2csv_like_json(_lines)
        for _, value in csv_multi.items():
            output.extend(value)
            output.append("")  # One empty line to show that another table is following
        return output

    def convert_lines(self, _lines: list[str]) -> Iterable:
        """
        Convert the data from influxdb-line protocol format to the desired format.
    
        Args:
            _lines (list[str]): input in influxdb-line protocol format.
            data_format (DataFormat): Data format of the desired output.
                Defaults to DataFormat.influxdb_lines.

        Returns:
            Iterable: The data in the desired iterable output format.
                E.g. JSON returns dict[str, Any], whereas csv returns list[str].
        """
        output: Iterable = ""
        match(self):
            case DataFormat.influxdb_lines:
                output = _lines
            case DataFormat.json:
                output = DataFormat._convert_json(_lines)
            case DataFormat.json_lines:
                output = DataFormat._convert_jsonlines(_lines)
            case DataFormat.csv:
                output = DataFormat._convert_csv(_lines)
            case DataFormat.multi_csv:
                output = DataFormat._convert_csv_multiline(_lines)
            case _:
                print(f"DataFormat {self} is not known.")
        return output

    def __str__(self):
        return self.value


def __influxdb_line2csv_like_json(_lines: list[str]) -> dict[str, list[str]]:
    """
    Convert InfluxDB line protocol formatted list of strings
    into a dictionary with CSV-formatted content.

    Args:
        _lines (list[str]): InfluxDB line protocol formatted list of strings.

    Returns:
        dict[str, list[str]]: Dictionary with CSV-formatted content.
            E.g.:
                {
                    "bno08x": [
                        "accel_x,accel_y,accel_z,timestamp",
                        "0.496094,-9.72656,0.304688,1725191547084",
                        "0.726563,-9.88672,-0.152344,1725191547245",
                        "0.652344,-9.76563,0.113281,1725191547431",
                        "1.07422,-9.80859,0.613281,1725191547586",
                    ],
                    "dps310": [
                        "pressure,temp,timestamp",
                        "972.715,35.769,1725191546993",
                        "972.713,35.7713,1725191547185",
                        "972.711,35.7708,1725191547365",
                        "972.712,35.7708,1725191547521",
                    ]
                }
    """
    output: dict[str, list[str]] = {}
    jsonized_output: dict[str, Any] = DataFormat._convert_json(_lines)
    for measurement, metrics in jsonized_output.items():
        # Sort keys, so that HEADER and the corresponding values are correctly aligned
        metric_keys: list[str] = sorted(metrics.keys())
        csv_header: str = ",".join(sorted(metric_keys)) + ",timestamp"
        output[measurement] = [csv_header]

        # Sort by timestamp ascending
        sorted_data_fields: dict[str, list[dict[str, Any]]] = {
            key: sorted(value, key=lambda fields: fields["timestamp"])
            for key, value in metrics.items()
        }

        # Little "cheat" since all keys in metric dict have the same amount of values
        for i, _ in enumerate(sorted_data_fields[metric_keys[0]]):
            csv_line: str = ""
            for metric in metric_keys:
                csv_line += f"{sorted_data_fields[metric][i]["value"]},"
            csv_line += f"{sorted_data_fields[metric_keys[0]][i]["timestamp"]}"
            output[measurement].append(csv_line)

    return output


def parse_influxdb_line(line) -> tuple[Optional[str], Optional[dict[str, Any]], Optional[int]]:
    """
    Parse a single line in InfluxDB line protocol format.

    Returns:
        tuple[Optional[str], Optional[dict], Optional[int]]:
            measurement, fields dictionary, and timestamp.
    """
    try:
        # Split the line into its components: measurement, fields, and timestamp
        measurement, fields, timestamp_str = line.split()

        # Parse fields into a dictionary
        field_dict: dict[str, Any] = {}
        for field in fields.split(','):
            key, value = field.split('=')
            field_dict[key] = float(value)

        # Convert timestamp from str to int
        timestamp: int = int(timestamp_str)

        return measurement, field_dict, timestamp

    except Exception as e:
        raise ValueError(f"Error parsing line: {line}") from e
