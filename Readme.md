# `Telhelp Auxspace`

> InfluxDB Line Protocol timestamp updater, plotter and formatter for Auxspace telemetry data.

## General Info

This python program updates the relative timestamps from the telemetry
project to absolute ones.

Since the microcontroller that is used in the rocket doesn't have an RTC,
the time data in data.txt is only relative to its launch.

This program helps updating these relative timestamps to dates,
in case the data has to be transferred into a timeseries database.

## Example

A quick exmple can be found in the **example/** directory.
**data.txt** is the data from the Microcontroller, containing relative
timestamps generated by the monotonic clock.
There is no info about the date yet, but the updated version called
**data_updated.txt** has this info added by `tsupdate.py`.

![example.png](/doc/timeseries-updater/example.png)

The diagram shows the data from **data_updated.txt**, which was obtained
on the Launch day of METER-1 (2024-08-31) by the sensors in the Rocket.

Other examples under **example/** show the different output formats of the
program, such as `json`, `json-lines` and `csv`.

## Setup

Run a quick setup using `python3-venv`:

```bash
# Setup and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# OPTIONAL: recompile requirements
# > pip3 install pip-tools
# > pip-compile requirements.in

# Install requirements
pip3 install -r requirements.txt

# Install pybuild
python3 -m pip install --upgrade build
```

**Note:** This program has been developed with Python version `3.12`.

## Build

The project wheel can be build with pybuild:

```bash
python3 -m build
```

## Install

After building, install the wheel with pip:

```bash
pip install ./dist/telhelp_auxspace-<VERSION>.whl
```

## Testing

Currently there is no testing environment set up.
This is a feature for the future.

## Usage

```bash
telhelp --help
```

## Plotter

To make it easier for users to access the data than to load them into
an InfluxDB first, looking for the right timespan and querying for the data,
this program can also plot the data for you.

![plotter.png](/doc/timeseries-updater/plotter.png)

To only use this funciton without converting timestamps, either set
`--timebase 0` or `--show-only`:

```bash
python3 ./tsupdater.py --show-only <DATA_FILE>
```

The plotter function is enabled by default, disable it via `--no-show`.

```bash
python3 ./tsupdater.py --no-show [<OTHER_OPTIONS>] <DATA_FILE>
```

## Data Formatter

In case that the output data is wanted in another format than the
InfluxDB Line Protocol, the program can also convert it into different
formats.
There are multiple examples about the different output formats
in the **example/** directory.

**Tipp:** If you only want to convert data inbetween different formats,
use `--timebase 0`, which lets the timestamps untouched:

```bash
# Example for only updating the data format without timestamp conversion
python3 ./tsupdater.py \
    --no-show \
    --timebase 0 \
    --output ~/Documents/METER-1-launch.csv \
    --data-format csv \
    ./example/data_updated.txt
```