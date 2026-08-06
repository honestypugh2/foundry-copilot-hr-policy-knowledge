# Benchmark Datasets

`hr-policy-decision-v1.json` is the sanitized architecture-decision dataset.
It contains no private policy text. Cases prefixed with `gold-` are the initial
human-reviewed calibration subset; deterministic source, refusal, router, and
permission assertions remain authoritative when an LLM judge disagrees.

`synthetic-migration-smoke.json` and its response map are contract fixtures,
not quality or performance evidence.