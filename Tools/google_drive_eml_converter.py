#!/usr/bin/env python3
"""
Google Drive EML -> PDF Converter (gog-based).

Downloads .eml files from a Drive folder, converts to PDFs, and uploads
the PDFs to a target Drive folder. No OAuth prompts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def _load_drive_account() -> Optional[str]:
    config_path = Path(__file__).parent.parent / "config" / "notebooklm.json"
    if not config_path.exists():
        return None
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError:
        return None
    drive_cfg = config.get("drive", {})
    return drive_cfg.get("account")


def _gog_json(args: List[str]) -> Dict:
    cmd = ["gog"] + args + ["--json", "--no-input"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gog command failed")
    payload = result.stdout.strip()
    return json.loads(payload) if payload else {}


def _list_eml_files(account: str, folder_id: str) -> List[Dict]:
    query = "name contains '.eml' and trashed=false"
    data = _gog_json([
        "drive", "ls",
        "--account", account,
        "--parent", folder_id,
        "--query", query,
        "--max", "1000",
    ])
    return data.get("files", [])


def _download_drive_file(account: str, file_id: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "gog", "drive", "download",
        file_id,
        "--account", account,
        "--out", str(out_path),
        "--no-input",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gog drive download failed")


def _upload_drive_file(account: str, file_path: Path, parent_id: str) -> None:
    cmd = [
        "gog", "drive", "upload",
        str(file_path),
        "--account", account,
        "--parent", parent_id,
        "--name", file_path.name,
        "--json",
        "--no-input",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gog drive upload failed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Drive .eml files to PDF and upload via gog."
    )
    parser.add_argument("source_folder_id", help="Drive folder ID containing .eml files")
    parser.add_argument("output_folder_id", help="Drive folder ID to upload PDFs")
    parser.add_argument("--account", default=None, help="Google Drive account email")
    parser.add_argument("--keep-files", action="store_true", help="Keep downloaded files")
    args = parser.parse_args()

    account = args.account or _load_drive_account()
    if not account:
        print("Missing Drive account. Set config.drive.account or pass --account.")
        return 2

    from Tools.eml_to_pdf_converter import convert_eml_to_pdf

    temp_dir = Path(__file__).resolve().parents[1] / "eml_to_pdf_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        eml_files = _list_eml_files(account, args.source_folder_id)
        if not eml_files:
            print("No .eml files found.")
            return 0

        converted = 0
        for file_info in eml_files:
            file_id = file_info.get("id")
            name = file_info.get("name") or f"{file_id}.eml"
            if not file_id:
                continue
            eml_path = temp_dir / name
            _download_drive_file(account, file_id, eml_path)
            pdf_path = Path(convert_eml_to_pdf(str(eml_path), str(temp_dir)))
            _upload_drive_file(account, pdf_path, args.output_folder_id)
            converted += 1

        print(f"Converted and uploaded {converted} EML files.")
        return 0
    finally:
        if not args.keep_files:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
