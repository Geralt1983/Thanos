#!/usr/bin/env python3
"""
Google Drive PDF Ingestor (Drive -> OpenAI RAG).

Deprecated OAuth flow removed. This wrapper syncs Drive PDFs via
openai_file_search.py (gog-based, no OAuth prompts).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _build_command(args: argparse.Namespace) -> list[str]:
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "Tools" / "openai_file_search.py"
    venv_python = project_root / ".venv" / "bin" / "python"
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    cmd = [python_bin, str(script_path), "sync-drive", "--ensure-folders"]
    if args.key:
        cmd += ["--key", args.key]
    if args.account:
        cmd += ["--account", args.account]
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Google Drive PDFs into OpenAI RAG."
    )
    parser.add_argument(
        "folder_id",
        nargs="?",
        help="Deprecated (ignored). Drive folder resolved by key.",
    )
    parser.add_argument(
        "--key",
        default="drive_inbox",
        help="Notebook key (e.g., drive_inbox, orders_hod, versacare, NCDHHS Radiology)",
    )
    parser.add_argument("--account", default=None, help="Google Drive account email")
    args, _unknown = parser.parse_known_args()

    cmd = _build_command(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "RAG ingest failed").strip()
        print(output)
        return result.returncode

    output = (result.stdout or "Drive sync complete.").strip()
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
