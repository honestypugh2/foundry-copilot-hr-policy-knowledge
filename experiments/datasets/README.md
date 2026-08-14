# Benchmark Datasets

`hr-policy-decision-v1.json` is the sanitized architecture-decision dataset.
It contains no private policy text. Cases prefixed with `gold-` are the initial
human-reviewed calibration subset; deterministic source, refusal, router, and
permission assertions remain authoritative when an LLM judge disagrees.

`synthetic-migration-smoke.json` and its response map are contract fixtures,
not quality or performance evidence.

`copilot-hr-policy-v1-copilot-studio.csv` is the seven-case import file for a
Copilot Studio standard-harness **Single response** evaluation. Its ordered
`Question,Expected response` columns support **Compare meaning** in addition to
**General quality**. Running the repository Direct Line benchmark does not
populate Copilot Studio Evaluation; import this file and select **Evaluate** in
the authenticated agent UI, then export the result for durable evidence.

`copilot-hr-policy-release-v2.json`, its `-evaluation.json` specification, and
its `-copilot-studio.csv` import are the correlated release set. They contain
seven quality cases plus prompt-injection and secret-disclosure cases. Use all
nine questions for both the Direct Line run and the native standard-harness
replay. The Power Platform API or Microsoft Copilot Studio connector can trigger
the saved test set and populate **Recent results**; the exported UI CSV is still
required to run deterministic checks against actual responses.