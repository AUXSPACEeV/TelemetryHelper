# plot.py
# 
# Matplotlib plotting functions.
#
#  created 02 Sep 2024
#  by Maximilian Stephan for Auxspace eV.
#

import math
import matplotlib.pyplot as plt

from datetime import datetime
from matplotlib.dates import DateFormatter
from typing import Any, Optional

from telhelp_auxspace.data_format import parse_influxdb_line


def _plot_influxdb_data(lines: list[str], ax: Any, date_format: str = '%H:%M'):
    """
    Parses an array of InfluxDB line protocol strings and plots all fields dynamically.

    Args:
        lines (list[str]): List of InfluxDB lines.
        ax (plt.axes.Axes): Axes to plot the graph onto.
        date_format (str): Format of the date on the graph's y-axis.
            Defaults to '%H:%M'.
    """
    # Initialize a dictionary to store lists of data for each field
    field_data: dict[str, Any] = {}
    timestamps: list[datetime] = []
    measurement: Optional[str] = None

    # Parse each line and store the data in the dictionary
    for line in lines:
        measurement, fields, timestamp = parse_influxdb_line(line)
        if measurement and fields and timestamp:
            # Convert timestamps to datetime for displaying purposes
            timestamps.append(datetime.fromtimestamp(timestamp / 1_000))
            for key, value in fields.items():
                if key not in field_data:
                    field_data[key] = []
                field_data[key].append(value)

    # Plotting the data on the given axis
    for field, values in field_data.items():
        ax.plot(timestamps, values, label=f'{field.capitalize()}', marker='o')

    ax.set_title(f'{measurement.capitalize()} Fields Over Time')
    ax.set_xlabel('Time')
    ax.set_ylabel('Value')
    ax.legend()
    ax.grid(True)

    ax.xaxis.set_major_formatter(DateFormatter(date_format))


def _group_lines_by_measurement(lines: list[str]) -> dict[str, list[str]]:
    """
    Groups the input lines by their measurement name.

    Args:
        lines (list[str]): List of InfluxDB Lines.

    Returns:
        dict[str, list[str]]: a dictionary where each key is a measurement name,
            and each value is a list of lines for that measurement.
    """
    grouped_lines: dict[str, list[str]] = {}

    for line in lines:
        # Parse InfluxDB line, but only measurement is relevant for grouping
        measurement, _, _ = parse_influxdb_line(line)
        if measurement:
            if measurement not in grouped_lines:
                grouped_lines[measurement] = []
            grouped_lines[measurement].append(line)

    return grouped_lines


def plot_data(lines: list[str], date_format: str = '%H:%M'):
    """
    Plot the InfluxDB Lines.

    Args:
        lines (list[str]): InfluxDB Line Protocol lines to plot.
        date_format (str): Format of the date on the graph's y-axis.
            Defaults to '%H:%M'
    """
    grouped_lines: dict[str, list[str]] = _group_lines_by_measurement(lines)
    # Determine grid size
    num_measurements: int = len(grouped_lines)
    cols: int = math.ceil(math.sqrt(num_measurements))
    rows: int = math.ceil(num_measurements / cols)

    # Create a grid of subplots
    fig, axs = plt.subplots(rows, cols, figsize=(10, 6))
    axs = axs.flatten()  # Flatten to easily iterate

    for i, (measurement, measurement_lines) in enumerate(grouped_lines.items()):
        print(f"Plotting data for measurement: {measurement}")
        _plot_influxdb_data(measurement_lines, axs[i], date_format)

    # Hide any unused subplots
    for j in range(i + 1, len(axs)):
        fig.delaxes(axs[j])

    plt.tight_layout()
    plt.show()
