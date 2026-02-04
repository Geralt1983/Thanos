"""Run all OpenClaw cron jobs with extended timeouts and capture last-run summaries."""

import json
import subprocess
import time
from pathlib import Path

DEFAULT_TIMEOUT_MS = 300000  # 5 minutes per job


def _extract_json(text: str) -> dict:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON found in output")
    return json.loads(text[start:])


def main() -> int:
    raw = subprocess.check_output(["openclaw", "cron", "list", "--json"], text=True)
    jobs = _extract_json(raw).get("jobs", [])

    results = []
    results_path = Path("/tmp/cron-test-results.json")

    for job in jobs:
        job_id = job["id"]
        name = job.get("name", "")
        print(f"RUN {name} {job_id}", flush=True)

        try:
            subprocess.run(
                [
                    "openclaw",
                    "cron",
                    "run",
                    job_id,
                    "--force",
                    "--timeout",
                    str(DEFAULT_TIMEOUT_MS),
                ],
                check=True,
                text=True,
                timeout=(DEFAULT_TIMEOUT_MS / 1000) + 30,
            )
        except subprocess.TimeoutExpired:
            results.append(
                {
                    "name": name,
                    "id": job_id,
                    "run_status": "run_timeout",
                }
            )
            continue
        except subprocess.CalledProcessError as exc:
            results.append(
                {
                    "name": name,
                    "id": job_id,
                    "run_status": "run_failed",
                    "run_error": str(exc),
                }
            )
            continue

        time.sleep(2)

        try:
            runs_raw = subprocess.check_output(
                ["openclaw", "cron", "runs", "--id", job_id, "--limit", "1"],
                text=True,
                timeout=30,
            )
            runs = _extract_json(runs_raw)
            entries = runs.get("entries", [])
            if entries:
                last = entries[0]
                results.append(
                    {
                        "name": name,
                        "id": job_id,
                        "run_status": last.get("status", "unknown"),
                        "run_at": last.get("runAtMs"),
                        "duration_ms": last.get("durationMs"),
                        "summary_preview": (last.get("summary") or "")[:200],
                    }
                )
            else:
                results.append({"name": name, "id": job_id, "run_status": "no_run_entry"})
        except Exception as exc:  # pragma: no cover - defensive
            results.append(
                {
                    "name": name,
                    "id": job_id,
                    "run_status": "runs_failed",
                    "run_error": str(exc),
                }
            )

        results_path.write_text(json.dumps(results, indent=2))

    results_path.write_text(json.dumps(results, indent=2))
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
