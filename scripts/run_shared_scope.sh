#!/usr/bin/env bash
# Re-run all five patterns through the Copilot Studio front door on ONE shared
# comparison scope so Compare shows 4/4 and Pareto ranks them together.
#
# The five front-door manifests are already scope-identical (same dataset,
# corpus/index fingerprint, reps, boundary). The only fields that still differ
# are git_commit and dirty_worktree, so this script re-pins them to the current
# clean commit and runs each lane.
#
# PRECONDITIONS (live, owned by you):
#   1. A2 Direct Line returns non-empty answers (the earlier empty-answer run was invalid).
#   2. Patterns B and Hosted answer THROUGH Copilot Studio (front-door route), not
#      only their deployed/local runtimes.
#   3. .env has, per lane: COPILOT_STUDIO_AGENT_SCHEMA_<LANE> and a secret
#      (COPILOT_STUDIO_TOKEN_SECRET_<LANE> or COPILOT_STUDIO_DIRECTLINE_SECRET_<LANE>).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"

DATASET="experiments/datasets/copilot-hr-policy-release-v2.json"
DATE="$(date -u +%Y%m%d)"
OUT_ROOT="experiments/reports/decision-system-$DATE/copilot-front-door/shared"
STAGE=".run/shared-scope"   # intermediate manifests (git-ignored)

# pattern | source front-door manifest (already scope-aligned) | Copilot Studio lane
PATTERNS=(
  "A|experiments/manifests/copilot-pattern-a-release-v2-45-20260811.json|A"
  "A2|experiments/manifests/copilot-front-door-a2-45-20260811.json|A2"
  "B|experiments/manifests/copilot-front-door-b-45-20260811.json|B"
  "C|experiments/manifests/copilot-pattern-c-release-v2-45-20260811.json|C"
  "Hosted|experiments/manifests/copilot-front-door-hosted-45-20260811.json|HOSTED"
)

[[ -x "$PY" ]] || { echo "ERROR: venv missing at $ROOT/.venv"; exit 1; }
[[ -f "$DATASET" ]] || { echo "ERROR: shared dataset $DATASET not found"; exit 1; }
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: worktree is dirty. Commit first so every run records dirty_worktree=false"
  echo "       (a clean worktree is a release-readiness gate)."; exit 1
fi

COMMIT="$(git rev-parse HEAD)"
mkdir -p "$STAGE"
echo "Shared scope -> commit=$COMMIT  dataset=$DATASET  reps=5  boundary=copilot_studio_direct_line"

for row in "${PATTERNS[@]}"; do
  IFS='|' read -r pattern src lane <<<"$row"
  [[ -f "$src" ]] || { echo "SKIP $pattern: source manifest $src not found"; continue; }
  staged="$STAGE/${pattern,,}.json"
  "$PY" - "$src" "$staged" "$COMMIT" "$pattern" "$DATE" <<'PYEOF'
import datetime, json, sys
src, dst, commit, pattern, date = sys.argv[1:6]
manifest = json.load(open(src, encoding="utf-8"))
manifest["git_commit"] = commit
manifest["dirty_worktree"] = False
manifest["experiment_id"] = f"shared-{pattern.lower()}-front-door-45-{date}"
manifest["created_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump(manifest, open(dst, "w", encoding="utf-8"), indent=2)
PYEOF
  out="$OUT_ROOT/${pattern,,}"
  echo "=== $pattern (lane $lane) -> $out ==="
  "$PY" -m src.benchmarking.cli \
    --manifest "$staged" \
    --cases "$DATASET" \
    --output-dir "$out" \
    --copilot-studio --copilot-lane "$lane"
done

echo ""
echo "All five front-door runs complete on one shared scope."
echo "Next: attach native quality/security evaluation to each run, then verify all"
echo "five share one comparison_scope at /api/benchmarking/experiments (Compare = 4/4)."
