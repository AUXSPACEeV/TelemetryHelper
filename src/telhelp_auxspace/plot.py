# plot.py
#
# Matplotlib plotting functions for Auxspace telemetry data.
#
#  created 02 Sep 2024
#  by Maximilian Stephan for Auxspace eV.
#

import math
import re

import matplotlib.pyplot as plt
import mplcursors
import numpy as np

from datetime import datetime
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter, AutoDateLocator, num2date as matplotlib_num2date
from matplotlib.ticker import AutoMinorLocator
from typing import Any, Callable, Optional

from telhelp_auxspace.audit import Flight
from telhelp_auxspace.data_format import parse_influxdb_line


STATE_COLORS: dict[str, str] = {
    "IDLE": "#6b7280",
    "ARMED": "#d97706",
    "BOOST": "#dc2626",
    "BURNOUT": "#7c3aed",
    "APOGEE": "#2563eb",
    "MAIN": "#059669",
    "LANDED": "#92400e",
}


# ---------------------------------------------------------------------------
# Display configuration
# ---------------------------------------------------------------------------
# Every known measurement can declare one or more logical "groups". Each group
# becomes its own subplot so that quantities with different scales / units do
# not share a y-axis (e.g. ~970 hPa pressure vs. ~35 °C temperature).
#
# Each group entry:
#   title   – subplot title
#   ylabel  – y-axis label with units
#   fields  – mapping of raw field name -> (display label, colour)
#   derived – optional callable(field_data) -> (label, values) producing an
#             extra trace such as the acceleration magnitude.
# ---------------------------------------------------------------------------

FieldSpec = dict[str, tuple[str, str]]
GroupSpec = dict[str, Any]


def _accel_magnitude(field_data: dict[str, list[float]]) -> tuple[str, list[float]]:
    xs = field_data.get("accel_x", [])
    ys = field_data.get("accel_y", [])
    zs = field_data.get("accel_z", [])
    n = min(len(xs), len(ys), len(zs))
    mag = [math.sqrt(xs[i] ** 2 + ys[i] ** 2 + zs[i] ** 2) for i in range(n)]
    return "‖a‖", mag


def _xyz_magnitude(field_data: dict[str, list[float]]) -> tuple[str, list[float]]:
    xs = field_data.get("x", [])
    ys = field_data.get("y", [])
    zs = field_data.get("z", [])
    n = min(len(xs), len(ys), len(zs))
    mag = [math.sqrt(xs[i] ** 2 + ys[i] ** 2 + zs[i] ** 2) for i in range(n)]
    return "‖a‖", mag


MEASUREMENT_DISPLAY: dict[str, str] = {
    "dps310": "DPS310 Barometric Sensor",
    "bno08x": "BNO08x IMU",
    "telemetry,type=accel": "Accelerometer",
    "telemetry,type=gyro": "Gyroscope",
    "telemetry,type=mag": "Magnetometer",
    "telemetry,type=baro": "Barometer",
}


# Per-field units used when a measurement has no explicit PLOT_LAYOUT entry.
FIELD_UNITS: dict[str, str] = {
    "pressure": "hPa",
    "temp": "°C",
    "temperature": "°C",
    "humidity": "%",
    "altitude": "m",
    "accel_x": "m/s²",
    "accel_y": "m/s²",
    "accel_z": "m/s²",
    "gyro_x": "rad/s",
    "gyro_y": "rad/s",
    "gyro_z": "rad/s",
    "mag_x": "µT",
    "mag_y": "µT",
    "mag_z": "µT",
    "voltage": "V",
    "current": "A",
}


PLOT_LAYOUT: dict[str, list[GroupSpec]] = {
    "dps310": [
        {
            "title": "Barometric Pressure",
            "ylabel": "Pressure (hPa)",
            "fields": {"pressure": ("Pressure", "#1f77b4")},
        },
        {
            "title": "Temperature",
            "ylabel": "Temperature (°C)",
            "fields": {"temp": ("Temperature", "#d62728")},
        },
    ],
    "bno08x": [
        {
            "title": "Linear Acceleration",
            "ylabel": "Acceleration (m/s²)",
            "fields": {
                "accel_x": ("X", "#1f77b4"),
                "accel_y": ("Y", "#2ca02c"),
                "accel_z": ("Z", "#d62728"),
            },
            "derived": _accel_magnitude,
            "derived_color": "#555555",
        },
    ],
    "telemetry,type=accel": [
        {
            "title": "Linear Acceleration",
            "ylabel": "Acceleration (m/s²)",
            "fields": {
                "x": ("X", "#1f77b4"),
                "y": ("Y", "#2ca02c"),
                "z": ("Z", "#d62728"),
            },
            "derived": lambda fd: _xyz_magnitude(fd),
            "derived_color": "#555555",
        },
    ],
    "telemetry,type=gyro": [
        {
            "title": "Angular Velocity",
            "ylabel": "Angular velocity (rad/s)",
            "fields": {
                "x": ("X", "#1f77b4"),
                "y": ("Y", "#2ca02c"),
                "z": ("Z", "#d62728"),
            },
        },
    ],
    "telemetry,type=mag": [
        {
            "title": "Magnetic Field",
            "ylabel": "Magnetic field (µT)",
            "fields": {
                "x": ("X", "#1f77b4"),
                "y": ("Y", "#2ca02c"),
                "z": ("Z", "#d62728"),
            },
        },
    ],
    "telemetry,type=baro": [
        {
            "title": "Barometric Pressure",
            "ylabel": "Pressure (hPa)",
            "fields": {"pres": ("Pressure", "#1f77b4")},
        },
        {
            "title": "Temperature",
            "ylabel": "Temperature (°C)",
            "fields": {"temp": ("Temperature", "#d62728")},
        },
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _humanize_field(raw: str) -> str:
    return raw.replace("_", " ").title()


_UNIT_GROUP_TITLE: dict[str, str] = {
    "hPa": "Barometric Pressure",
    "°C": "Temperature",
    "%": "Humidity",
    "m": "Altitude",
    "m/s²": "Linear Acceleration",
    "rad/s": "Angular Velocity",
    "µT": "Magnetic Field",
    "V": "Voltage",
    "A": "Current",
}


def _default_groups(fields: list[str]) -> list[GroupSpec]:
    """Fallback layout for unknown measurements.

    Fields are partitioned by unit so that quantities with unrelated scales
    (e.g. pressure vs. temperature) become separate subplots.
    """
    palette = plt.get_cmap("tab10").colors
    buckets: dict[str, list[str]] = {}
    for name in fields:
        unit = FIELD_UNITS.get(name, "")
        buckets.setdefault(unit, []).append(name)

    groups: list[GroupSpec] = []
    color_idx = 0
    for unit, names in buckets.items():
        ylabel = f"Value ({unit})" if unit else "Value"
        title = _UNIT_GROUP_TITLE.get(unit) or (
            _humanize_field(names[0]) if len(names) == 1 else "Fields"
        )
        field_spec: FieldSpec = {}
        for name in names:
            field_spec[name] = (
                _humanize_field(name), palette[color_idx % len(palette)],
            )
            color_idx += 1
        groups.append({"title": title, "ylabel": ylabel, "fields": field_spec})
    return groups


def _parse_lines(
    lines: list[str],
) -> tuple[dict[str, list[datetime]], dict[str, dict[str, list[float]]]]:
    """Bucket lines per measurement.

    Returns:
        timestamps: measurement -> list[datetime]
        fields:     measurement -> field_name -> list[float]
    """
    timestamps: dict[str, list[datetime]] = {}
    fields: dict[str, dict[str, list[float]]] = {}

    for line in lines:
        measurement, field_dict, ts = parse_influxdb_line(line)
        if not (measurement and field_dict and ts):
            continue
        timestamps.setdefault(measurement, []).append(
            datetime.fromtimestamp(ts / 1_000)
        )
        bucket = fields.setdefault(measurement, {})
        for key, value in field_dict.items():
            bucket.setdefault(key, []).append(value)
    return timestamps, fields


def _annotate_extrema(ax: Axes, ts: list[datetime], values: list[float], color: str):
    """Mark the min and max of a trace with a small annotation."""
    if not values:
        return
    arr = np.asarray(values)
    i_max = int(arr.argmax())
    i_min = int(arr.argmin())
    for i, marker, dy in ((i_max, "^", 10), (i_min, "v", -14)):
        ax.annotate(
            f"{arr[i]:.2f}",
            xy=(ts[i], arr[i]),
            xytext=(0, dy),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=color,
            alpha=0.9,
        )
        ax.plot(ts[i], arr[i], marker=marker, color=color, markersize=5, alpha=0.9)


def _unit_from_ylabel(ylabel: str) -> str:
    m = re.search(r"\(([^)]+)\)\s*$", ylabel or "")
    return m.group(1) if m else ""


def _plot_group(
    ax: Axes,
    measurement: str,
    group: GroupSpec,
    ts: list[datetime],
    field_data: dict[str, list[float]],
    date_format: str,
    dense: bool,
):
    fields: FieldSpec = group["fields"]
    linewidth = 1.0 if dense else 1.4
    marker = None if dense else "o"
    markersize = 0 if dense else 3
    hover_lines: list[Any] = []

    for raw_name, (label, color) in fields.items():
        values = field_data.get(raw_name)
        if not values:
            continue
        (line,) = ax.plot(
            ts[: len(values)],
            values,
            label=label,
            color=color,
            linewidth=linewidth,
            marker=marker,
            markersize=markersize,
        )
        hover_lines.append(line)
        if len(fields) == 1:
            _annotate_extrema(ax, ts[: len(values)], values, color)

    derived: Optional[Callable] = group.get("derived")
    if derived:
        label, values = derived(field_data)
        if values:
            (line,) = ax.plot(
                ts[: len(values)],
                values,
                label=label,
                color=group.get("derived_color", "#333333"),
                linewidth=1.0,
                linestyle="--",
                alpha=0.8,
            )
            hover_lines.append(line)

    display_name = MEASUREMENT_DISPLAY.get(measurement, measurement.upper())
    ax.set_title(f"{display_name} — {group['title']}", fontsize=11, pad=8)
    ax.set_xlabel("Time")
    ax.set_ylabel(group["ylabel"])
    ax.grid(True, which="major", linestyle="-", alpha=0.35)
    ax.grid(True, which="minor", linestyle=":", alpha=0.2)
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter(date_format))
    ax.tick_params(axis="x", labelrotation=0)

    legend = ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=False,
        fontsize=9,
    )
    if legend:
        legend.set_title(group["title"], prop={"size": 9, "weight": "bold"})

    if hover_lines:
        unit = _unit_from_ylabel(group["ylabel"])
        cursor = mplcursors.cursor(hover_lines, hover=True)

        @cursor.connect("add")
        def _on_add(sel, _unit=unit, _fmt=date_format):
            label = sel.artist.get_label() or ""
            x, y = sel.target
            try:
                ts_str = matplotlib_num2date(x).strftime(_fmt)
            except Exception:
                ts_str = f"{x:.3f}"
            value_str = f"{y:.4g}" + (f" {_unit}" if _unit else "")
            sel.annotation.set_text(f"{label}\n{ts_str}\n{value_str}")
            sel.annotation.get_bbox_patch().set(fc="#ffffff", ec="#333333", alpha=0.9)


def _format_duration(delta_seconds: float) -> str:
    if delta_seconds < 60:
        return f"{delta_seconds:.1f} s"
    minutes, seconds = divmod(int(delta_seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    return f"{minutes}m {seconds:02d}s"


def _suptitle(
    fig: plt.Figure,
    timestamps: dict[str, list[datetime]],
    fields: dict[str, dict[str, list[float]]],
    title: str = "Auxspace Telemetry",
):
    all_stamps = [t for series in timestamps.values() for t in series]
    if not all_stamps:
        fig.suptitle(title, fontsize=15, fontweight="bold")
        return
    start = min(all_stamps)
    end = max(all_stamps)
    total_samples = sum(len(series) for series in timestamps.values())
    per_measurement = ", ".join(
        f"{MEASUREMENT_DISPLAY.get(m, m)}: {len(ts)}"
        for m, ts in timestamps.items()
    )
    duration = _format_duration((end - start).total_seconds())
    subtitle = (
        f"{start:%Y-%m-%d %H:%M:%S} → {end:%H:%M:%S}   "
        f"({duration}, {total_samples:,} samples)\n{per_measurement}"
    )
    fig.suptitle(
        title,
        fontsize=16,
        fontweight="bold",
        color="#1a5fb4",
        y=0.995,
    )
    fig.text(0.5, 0.955, subtitle, ha="center", va="top", fontsize=9, color="#505460")


# ---------------------------------------------------------------------------
# Theme / state markers
# ---------------------------------------------------------------------------

def _apply_theme():
    # Palette aligned with aurora's Furo docs theme: brand blue #1a5fb4,
    # accent #6ea8fe, neutral #333333 on #f8f9fa panels with #dce0e5 borders.
    plt.rcParams.update({
        "figure.facecolor": "#f8f9fa",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#dce0e5",
        "axes.linewidth": 0.8,
        "axes.labelcolor": "#1e2028",
        "axes.labelsize": 10,
        "axes.labelweight": "semibold",
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlecolor": "#1a5fb4",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": plt.cycler(
            color=[
                "#1a5fb4",  # aurora brand blue
                "#6ea8fe",  # aurora accent blue
                "#26a269",  # green
                "#c64600",  # orange
                "#9141ac",  # purple
                "#e5a50a",  # amber
                "#865e3c",  # brown
            ]
        ),
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "grid.color": "#dce0e5",
        "grid.linewidth": 0.6,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "legend.frameon": False,
        "legend.fontsize": 9,
    })


def _draw_state_markers(axes: list[Axes], transitions) -> None:
    """Overlay vertical lines for each state transition on every axis.

    Labels are placed on the topmost axis only to avoid clutter.
    """
    if not transitions:
        return
    top_ax = axes[0]
    for entry in transitions:
        if entry.kind != "transition":
            continue
        color = STATE_COLORS.get(entry.target, "#444444")
        t = datetime.fromtimestamp(entry.timestamp_ms / 1_000)
        for ax in axes:
            ax.axvline(
                t,
                color=color,
                linestyle="--",
                linewidth=0.9,
                alpha=0.55,
                zorder=0,
            )
        top_ax.annotate(
            entry.target,
            xy=(t, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(2, -2),
            textcoords="offset points",
            ha="left",
            va="top",
            fontsize=8,
            color=color,
            fontweight="bold",
            rotation=90,
        )


def _build_groups(
    fields: dict[str, dict[str, list[float]]],
) -> list[tuple[str, GroupSpec]]:
    groups: list[tuple[str, GroupSpec]] = []
    for measurement, field_data in fields.items():
        layout = PLOT_LAYOUT.get(measurement)
        if layout is None:
            for group in _default_groups(list(field_data.keys())):
                groups.append((measurement, group))
            continue
        for group in layout:
            if any(name in field_data for name in group["fields"]):
                groups.append((measurement, group))
    return groups


def _draw_figure(
    timestamps: dict[str, list[datetime]],
    fields: dict[str, dict[str, list[float]]],
    date_format: str,
    transitions=None,
    title: str = "Auxspace Telemetry",
):
    groups = _build_groups(fields)
    n = len(groups)
    if n == 0:
        return
    fig, axes = plt.subplots(
        n, 1, figsize=(10.0, 3.2 * n + 1.0), squeeze=False, sharex=True,
    )
    flat_axes = [ax for row in axes for ax in row]
    for idx, (ax, (measurement, group)) in enumerate(zip(flat_axes, groups)):
        ts = timestamps[measurement]
        dense = len(ts) > 500
        _plot_group(ax, measurement, group, ts, fields[measurement], date_format, dense)
        if idx != n - 1:
            ax.set_xlabel("")
        print(f"Plotting {measurement}: {group['title']}")

    _draw_state_markers(flat_axes, transitions or [])
    _suptitle(fig, timestamps, fields, title=title)
    fig.tight_layout(rect=(0, 0, 1, 0.93))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plot_data(lines: list[str], date_format: str = "%H:%M"):
    """Plot Auxspace telemetry data from InfluxDB Line Protocol records.

    Args:
        lines (list[str]): InfluxDB Line Protocol lines to plot.
        date_format (str): Strftime format for the x-axis tick labels.
    """
    _apply_theme()
    timestamps, fields = _parse_lines(lines)
    if not timestamps:
        print("No valid telemetry lines to plot.")
        return
    _draw_figure(timestamps, fields, date_format)
    plt.show()


def plot_flights(
    lines: list[str],
    flights: list[Flight],
    date_format: str = "%H:%M:%S",
):
    """Plot one figure per flight, with state-transition markers overlayed.

    Each flight is delimited by a BOOST transition and a subsequent IDLE/LANDED
    transition (see `audit.find_flights`). Telemetry outside any flight window
    is skipped.
    """
    if not flights:
        print("No flights detected in audit log.")
        return
    _apply_theme()

    timestamps, fields = _parse_lines(lines)
    if not timestamps:
        print("No valid telemetry lines to plot.")
        return

    for flight in flights:
        sub_ts: dict[str, list[datetime]] = {}
        sub_fields: dict[str, dict[str, list[float]]] = {}
        start_dt = datetime.fromtimestamp(flight.start_ms / 1_000)
        end_dt = datetime.fromtimestamp(flight.end_ms / 1_000)
        for measurement, series in timestamps.items():
            keep = [
                i for i, t in enumerate(series) if start_dt <= t <= end_dt
            ]
            if not keep:
                continue
            sub_ts[measurement] = [series[i] for i in keep]
            sub_fields[measurement] = {
                name: [values[i] for i in keep if i < len(values)]
                for name, values in fields[measurement].items()
            }
        if not sub_ts:
            print(f"Flight {flight.index + 1}: no telemetry in window, skipping.")
            continue
        kept_transitions = [
            t for t in flight.transitions
            if flight.start_ms <= t.timestamp_ms <= flight.end_ms
        ]
        title = f"Auxspace Telemetry — Flight {flight.index + 1}"
        _draw_figure(sub_ts, sub_fields, date_format, kept_transitions, title)

    plt.show()
