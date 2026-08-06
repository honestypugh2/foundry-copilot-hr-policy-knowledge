# Benchmark Load Testing

Load tests are capacity experiments, not sequential benchmark repetitions or
production telemetry. Their results use the separate `LoadTestReport` contract.

Install the optional dependency in the project environment:

```bash
uv sync --extra load
```

Start the local backend in synthetic/offline mode, then run a smoke profile:

```bash
USE_AZURE_SERVICES=false uv run uvicorn src.backend.main:app --port 8000
uv run locust -f locustfile.py --host http://localhost:8000 --headless \
  --users 2 --spawn-rate 1 --run-time 10s --csv artifacts/load/smoke
```

Remote targets require `LOAD_TEST_CONFIRM_TARGET` to equal the exact hostname
and `LOAD_TEST_ENVIRONMENT` must not be `prod` or `production`. Production
targets are intentionally rejected. Store credentials outside the Locust file.

Use `import_locust_csv` on Locust's `*_stats.csv` artifact to normalize endpoint
throughput, failures, and p50/p95/p99. Azure Load Testing can run the same file;
its operational detail remains in the native Azure experience.