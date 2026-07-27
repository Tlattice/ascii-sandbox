# inventory

Item storage and transfer: pickup, drop, stacking, and slot management for players and containers.

| File | Purpose |
|------|---------|
| [`inventory.go`](inventory.go) | Implementation |
| [`inventory_test.go`](inventory_test.go) | Unit and replay tests |
| [`contract.yaml`](contract.yaml) | Public API and guarantees |
| [`replay.json`](replay.json) | Deterministic input sequence |
| [`snapshot.txt`](snapshot.txt) | Expected ASCII state after replay |
