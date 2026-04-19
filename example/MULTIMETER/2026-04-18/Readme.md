# `Multimeter Test flight 2026-04-18`

## Info

### Version

- `telhelp`: `208b75b3665d4c4e953fd211de637d928c89456c`
- `aurora`: `0.2.1`

### Compile command

```bash
telhelp example/MULTIMETER/2026-04-18/flights.influx \
	--audit example/MULTIMETER/2026-04-18/state_audit \
	--idle-timeout 3 \
	--pre-boost 3
```

## Flight Protocol

Two flights are recorded in [flights.influx](./flights.influx).

- Flight1:
  - parachute opened too late
  - state machine didn't go from MAIN to REDUNDAND
- Flight2:
  - parachute didn't open; pyro fired on the ground
  - state machine didn't go from MAIN to REDUNDAND
