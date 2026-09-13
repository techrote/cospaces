# Repository support tools

These scripts support development, hardening and external qualification. They are not additional `cospaces` product subcommands and do not change the eight-tool programme.

- `hardening_smoke.py` — CI-enforced network-free T1–T4 hardening suite.
- `live_codespace_smoke.py` — explicit opt-in live integration smoke against one named existing Codespace.
- `external_workload.py` — bounded repository-owned warm workload for measurement by an external host/orchestrator. See [`../docs/EXTERNAL_WORKLOAD.md`](../docs/EXTERNAL_WORKLOAD.md).

The external workload contains no host-provider logic, credentials, remote-access implementation or evidence-policy decisions. External systems choose the host and commit, perform any cold clone/install measurement, schedule longer sampling, and interpret the emitted `cospaces.external-workload/v1` record.
