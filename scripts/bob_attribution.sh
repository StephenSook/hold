#!/usr/bin/env bash
# Generate docs/bob-evidence/ATTRIBUTION.md from git history.
# Counts Tool: IBM-Bob trailers, modes used, and per-phase commit breakdown.
# Read-only on source; writes only to docs/bob-evidence/ATTRIBUTION.md.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
OUT="$REPO_ROOT/docs/bob-evidence/ATTRIBUTION.md"
mkdir -p "$(dirname "$OUT")"

# Count commits with the IBM-Bob trailer
TOTAL_COMMITS=$(git log --oneline | wc -l | tr -d ' ')
BOB_COMMITS=$(git log --format='%B' | grep -c "^Tool: IBM-Bob$" || true)
LAST_BOB_COMMIT=$(git log --format='%h' --grep='^Tool: IBM-Bob$' -1)

# Build trace: all commits in order
BUILD_TRACE=$(git log --reverse --format='%ad %H %s' --date=format:'%H:%M')

# Trailer breakdown by subject prefix
FEAT_COUNT=$(git log --format='%s' | grep -c "^feat" || true)
FIX_COUNT=$(git log --format='%s' | grep -c "^fix" || true)
CHORE_COUNT=$(git log --format='%s' | grep -c "^chore" || true)
DOCS_COUNT=$(git log --format='%s' | grep -c "^docs" || true)
CI_COUNT=$(git log --format='%s' | grep -c "^ci" || true)
TEST_COUNT=$(git log --format='%s' | grep -c "^test" || true)
CONTRACT_COUNT=$(git log --format='%s' | grep -c "^CONTRACT" || true)
STATUS_COUNT=$(git log --format='%s' | grep -c "^status" || true)

cat > "$OUT" << MDEOF
# Bob Attribution

Generated: $(date -u '+%Y-%m-%d %H:%M UTC')

## Summary

| Metric | Value |
|---|---|
| Total commits | $TOTAL_COMMITS |
| Bob-authored commits (Tool: IBM-Bob trailer) | $BOB_COMMITS |
| Last Bob-authored commit | $LAST_BOB_COMMIT |
| feat commits | $FEAT_COUNT |
| fix commits | $FIX_COUNT |
| chore commits | $CHORE_COUNT |
| docs commits | $DOCS_COUNT |
| ci commits | $CI_COUNT |
| test commits | $TEST_COUNT |
| CONTRACT commits | $CONTRACT_COUNT |
| status commits | $STATUS_COUNT |

## Modes used

Five write-scoped custom modes configured in \`.bob/custom_modes.yaml\`:
- \`solver-engine\`: api/hold/, api/tests/, api/routes/, bench/, rules/, scripts/, data/
- \`agent-runtime\`: api/agents/, api/main.py, Dockerfile, streaming/mcp modules
- \`mobile-shell\`: web/android/, web/ios/, web/src/native/, capacitor.config.ts
- \`frontend\`: web/ (non-native paths), docs/design/
- \`evidence-writer\`: docs/ (non-design), README.md, specs/, security/

## Build trace

\`\`\`
$BUILD_TRACE
\`\`\`
MDEOF

echo "Wrote $OUT"
echo "  Bob-authored commits: $BOB_COMMITS / $TOTAL_COMMITS total"
