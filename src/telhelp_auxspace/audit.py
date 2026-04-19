# audit.py
#
# State-machine audit log parsing and flight-window extraction.
#
#  created 19 Apr 2026
#  by Maximilian Stephan for Auxspace eV.
#

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


FLIGHT_START_STATE = "BOOST"
FLIGHT_END_STATES = {"IDLE", "LANDED"}


@dataclass(frozen=True)
class AuditEntry:
    """A single row from the state-machine audit log."""
    timestamp_ms: int
    kind: str          # "transition" or "event"
    source: str        # previous state
    target: str        # new state (transition) or event text


@dataclass(frozen=True)
class Flight:
    """A contiguous telemetry window delimited by BOOST → {IDLE,LANDED}."""
    index: int
    start_ms: int
    end_ms: int
    transitions: list[AuditEntry]   # only "transition" entries within [start,end]
    ended_by: str = ""              # target state that terminated the flight


def parse_audit(path: Path) -> list[AuditEntry]:
    """Parse a state-machine audit log file into structured entries.

    Lines look like:
        1383080      transition   ARMED        BOOST
        547035       event        ARMED        orientation below threshold
    """
    entries: list[AuditEntry] = []
    with open(path, mode="r", encoding="UTF-8") as fh:
        for raw in fh.read().splitlines():
            line = raw.strip()
            if not line:
                continue
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue
            try:
                ts = int(parts[0])
            except ValueError:
                continue
            kind = parts[1].lower()
            if kind not in ("transition", "event"):
                continue
            entries.append(
                AuditEntry(timestamp_ms=ts, kind=kind, source=parts[2], target=parts[3])
            )
    return entries


def shift_audit(entries: list[AuditEntry], timebase: int) -> list[AuditEntry]:
    """Shift all audit timestamps by `timebase` ms (relative → absolute)."""
    return [
        AuditEntry(
            timestamp_ms=e.timestamp_ms + timebase,
            kind=e.kind,
            source=e.source,
            target=e.target,
        )
        for e in entries
    ]


def find_flights(
    entries: list[AuditEntry],
    idle_timeout_ms: Optional[int] = None,
    pre_boost_ms: int = 0,
) -> list[Flight]:
    """Extract flight windows: BOOST → next IDLE/LANDED transition.

    If `idle_timeout_ms` is given and a flight terminates in IDLE (i.e. the
    state machine timed out rather than detecting LANDED), the end of the
    window is capped at `last_non_idle_transition_ms + idle_timeout_ms`, so
    the trailing empty gap does not dominate the plot.
    """
    flights: list[Flight] = []
    i = 0
    idx = 0
    while i < len(entries):
        e = entries[i]
        if e.kind == "transition" and e.target == FLIGHT_START_STATE:
            start_ms = e.timestamp_ms - pre_boost_ms
            end_ms: Optional[int] = None
            ended_by = ""
            window = [e]
            j = i + 1
            while j < len(entries):
                ne = entries[j]
                if ne.kind == "transition":
                    window.append(ne)
                    if ne.target in FLIGHT_END_STATES:
                        end_ms = ne.timestamp_ms
                        ended_by = ne.target
                        break
                j += 1
            if end_ms is None:
                end_ms = window[-1].timestamp_ms
                ended_by = window[-1].target

            if idle_timeout_ms is not None and ended_by == "IDLE":
                pre_idle = [t.timestamp_ms for t in window if t.target != "IDLE"]
                anchor = max(pre_idle) if pre_idle else start_ms
                end_ms = min(end_ms, anchor + idle_timeout_ms)

            flights.append(
                Flight(
                    index=idx,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    transitions=window,
                    ended_by=ended_by,
                )
            )
            idx += 1
            i = j + 1
        else:
            i += 1
    return flights
