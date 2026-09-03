"""
Export Bob usage evidence from the local Bob session store.
Read-only: never modifies the database.
Writes docs/bob-evidence/bob-usage-evidence.json.
No message bodies are exported (privacy and size).

Usage: uv run python scripts/export_bob_evidence.py
"""
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DB_PATH = Path.home() / ".bob" / "db" / "bob.db"
OUT_PATH = Path(__file__).parent.parent / "docs" / "bob-evidence" / "bob-usage-evidence.json"
WORKSPACE = str(Path(__file__).parent.parent.resolve())


def parse_costs(costs_str: str | None) -> dict:
    if not costs_str:
        return {}
    try:
        return json.loads(costs_str)
    except Exception:
        return {}


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        print(f"Bob db not found at {DB_PATH}; writing empty evidence file")
        OUT_PATH.write_text(json.dumps({
            "generated_at": datetime.now(UTC).isoformat(),
            "workspace": WORKSPACE,
            "note": "Bob db not found",
            "task_count": 0,
            "total_cost_usd": 0,
            "attribution_log_count": 0,
        }, indent=2))
        return

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # All tasks (directory filtering unreliable in this db version - tasks have empty dir)
    tasks = conn.execute(
        "SELECT id, title, status, costs, created_at, updated_at FROM tasks ORDER BY created_at"
    ).fetchall()

    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    task_summaries = []
    for t in tasks:
        costs = parse_costs(t["costs"])
        cost_usd = costs.get("total_cost", costs.get("cost", 0)) or 0
        input_tok = costs.get("input_tokens", 0) or 0
        output_tok = costs.get("output_tokens", 0) or 0
        total_cost += float(cost_usd)
        total_input_tokens += int(input_tok)
        total_output_tokens += int(output_tok)
        task_summaries.append({
            "id": t["id"],
            "title": (t["title"] or "")[:80],
            "status": t["status"],
            "cost_usd": float(cost_usd),
            "input_tokens": int(input_tok),
            "output_tokens": int(output_tok),
            "created_at": t["created_at"],
        })

    # Attribution logs
    attr_count = conn.execute("SELECT COUNT(*) FROM attribution_logs").fetchone()[0]

    conn.close()

    evidence = {
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace": WORKSPACE,
        "note": (
            "task_count includes all Bob tasks in this install, not only HOLD tasks, "
            "because the directory field is empty in this Bob db version. "
            "Visual corroboration: Bobcoin gauge screenshots in this directory."
        ),
        "task_count": len(tasks),
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "attribution_log_count": attr_count,
        "tasks": task_summaries,
    }

    OUT_PATH.write_text(json.dumps(evidence, indent=2))
    print(f"Wrote {OUT_PATH}")
    print(f"  tasks: {len(tasks)}, cost: ${total_cost:.4f}, "
          f"tokens in/out: {total_input_tokens}/{total_output_tokens}")


if __name__ == "__main__":
    main()
