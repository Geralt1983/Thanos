#!/usr/bin/env python3
"""
OpenAI File Search helper for Thanos.

Provides vector store management and querying helpers for the NotebookLM
replacement workflow.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config" / "notebooklm.json"
ENV_PATH = PROJECT_ROOT / ".env"
STATE_PATH = PROJECT_ROOT / "memory" / "cache" / "openai_file_search_drive_state.json"

DEFAULT_MAX_RESULTS = 20
DEFAULT_SCORE_THRESHOLD = 0.25
DEFAULT_CONTEXT_RESULTS = 3
DEFAULT_CONTEXT_CHARS = 4000
DEFAULT_STRICT = True
DEFAULT_INCLUDE_RESULTS = True

try:
    import openai
except ImportError:  # pragma: no cover - optional dependency
    openai = None  # type: ignore[assignment]
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]


class OpenAIFileSearchClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4.1-mini", timeout: int = 120) -> None:
        if load_dotenv and ENV_PATH.exists():
            load_dotenv(ENV_PATH, override=False)
        if openai is None:
            raise ImportError("openai package not installed. Install with: pip install openai")
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment.")
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout)
        self._model = model

    def query(
        self,
        prompt: str,
        vector_store_id: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        include_results: bool = DEFAULT_INCLUDE_RESULTS,
        ranking_options: Optional[Dict[str, Any]] = None,
        strict: bool = DEFAULT_STRICT,
        score_threshold: Optional[float] = DEFAULT_SCORE_THRESHOLD,
        context_results: int = DEFAULT_CONTEXT_RESULTS,
        context_chars: int = DEFAULT_CONTEXT_CHARS,
        instructions: Optional[str] = None,
        tool_choice: Optional[Any] = None,
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        try:
            if strict and not include_results:
                include_results = True
            file_search_tool: Dict[str, Any] = {
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": max_results,
            }
            if ranking_options:
                file_search_tool["ranking_options"] = ranking_options
            tools = [file_search_tool]
            include = ["file_search_call.results"] if include_results else None
            request: Dict[str, Any] = {
                "model": self._model,
                "input": prompt,
                "tools": tools,
            }
            if include is not None:
                request["include"] = include
            if instructions:
                request["instructions"] = instructions
            if tool_choice is not None:
                request["tool_choice"] = tool_choice

            response = self._client.responses.create(**request)
            text = self._extract_text(response)
            results = self._extract_results(response) if include_results else []
            if strict:
                required_terms = _extract_terms(prompt)
                filtered = _filter_results(results, score_threshold, required_terms)
                if not filtered:
                    return True, "Not found in documents.", results
                filtered = _sort_results(filtered)
                filtered_context = filtered[:context_results]
                context = _build_context(filtered_context, context_results, context_chars)
                followup_instructions = instructions or (
                    "Answer ONLY using the provided context. "
                    "If the answer is not explicitly present, respond: 'Not found in documents.'"
                )
                followup = self._client.responses.create(
                    model=self._model,
                    input=f"{prompt}\n\nContext:\n{context}",
                    instructions=followup_instructions,
                )
                final_text = self._extract_text(followup)
                return True, final_text, filtered_context
            return True, text, results
        except Exception as exc:  # pragma: no cover - network/provider errors
            return False, f"OpenAI File Search failed: {exc}", []

    @staticmethod
    def _extract_text(response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text).strip()

        output = getattr(response, "output", None)
        if not output:
            return str(response).strip()

        texts: List[str] = []
        for item in output:
            item_type = _get_attr(item, "type")
            if item_type == "output_text":
                text = _get_attr(item, "text")
                if text:
                    texts.append(str(text))
            elif item_type == "message":
                for content in _get_attr(item, "content", []) or []:
                    content_type = _get_attr(content, "type")
                    if content_type in ("output_text", "text"):
                        text = _get_attr(content, "text")
                        if text:
                            texts.append(str(text))

        return "\n".join(texts).strip() or str(response).strip()

    @staticmethod
    def _extract_results(response: Any) -> List[Dict[str, Any]]:
        data = _as_dict(response)
        output = data.get("output", []) if isinstance(data, dict) else []
        for item in output:
            if isinstance(item, dict) and item.get("type") == "file_search_call":
                results = item.get("results") or item.get("search_results")
                if isinstance(results, list):
                    return results
        return []


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_dict(obj: Any) -> Any:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj


def _load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def _normalize_key(raw: str) -> str:
    key = raw.strip().lower()
    key = re.sub(r"[^a-z0-9_-]+", "_", key)
    return key.strip("_") or "drive_inbox"


def _ensure_notebook_config(config: Dict[str, Any], raw_key: str) -> str:
    notebooks = config.setdefault("notebooks", {})
    key = _normalize_key(raw_key)
    if key in notebooks:
        return key

    title = raw_key.strip() or key.replace("_", " ").title()
    local_cache = PROJECT_ROOT / "data" / "galaxy_docs" / key
    notebooks[key] = {
        "title": title if title else key.replace("_", " ").title(),
        "drive_folder_name": key,
        "local_cache_dir": str(local_cache),
        "source_paths": [str(local_cache)],
    }
    _save_config(config)
    return key


def _save_config(config: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, sort_keys=False)
        f.write("\n")


def _load_state() -> Dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"version": 1, "stores": {}}


def _save_state(state: Dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=False) + "\n")


def _collect_files(paths: Iterable[str]) -> List[Path]:
    files: List[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            files.extend(sorted(path.rglob("*.pdf")))
        elif path.is_file():
            files.append(path)
        else:
            for match in Path().glob(raw):
                if match.is_file():
                    files.append(match)
    return files


def _chunk(items: List[Path], size: int) -> Iterable[List[Path]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _require_client(model: str, timeout: int) -> OpenAIFileSearchClient:
    return OpenAIFileSearchClient(model=model, timeout=timeout)


def _get_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    defaults = config.get("file_search_defaults", {})
    return {
        "max_results": defaults.get("max_results", DEFAULT_MAX_RESULTS),
        "score_threshold": defaults.get("score_threshold", DEFAULT_SCORE_THRESHOLD),
        "context_results": defaults.get("context_results", DEFAULT_CONTEXT_RESULTS),
        "context_chars": defaults.get("context_chars", DEFAULT_CONTEXT_CHARS),
        "strict": defaults.get("strict", DEFAULT_STRICT),
        "include_results": defaults.get("include_results", DEFAULT_INCLUDE_RESULTS),
        "ranking_options": defaults.get("ranking_options"),
    }


def _resolve_store(config: Dict[str, Any], key: Optional[str], vector_store_id: Optional[str]) -> Tuple[str, str]:
    if vector_store_id:
        return vector_store_id, vector_store_id
    if not key:
        raise ValueError("Provide --key or --vector-store-id.")
    notebook = config.get("notebooks", {}).get(key)
    if not notebook:
        raise KeyError(f"Unknown notebook key: {key}")
    store_id = notebook.get("vector_store_id")
    if not store_id:
        raise ValueError(f"Missing vector_store_id for key '{key}'.")
    return store_id, key


def _apply_query_hints(prompt: str, hints: Optional[List[str]]) -> str:
    if not hints:
        return prompt
    hint_text = ", ".join(hints)
    return f"{prompt}\n\nSearch focus terms: {hint_text}"


def _gog_json(args: List[str]) -> Dict[str, Any]:
    cmd = ["gog"] + args + ["--json", "--no-input"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gog command failed")
    payload = result.stdout.strip()
    return json.loads(payload) if payload else {}


def _find_drive_folder(account: str, name: str, parent_id: str) -> Optional[str]:
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    data = _gog_json(["drive", "ls", "--account", account, "--parent", parent_id, "--query", query, "--max", "200"])
    for item in data.get("files", []):
        if item.get("name") == name:
            return item.get("id")
    return None


def _create_drive_folder(account: str, name: str, parent_id: str) -> str:
    data = _gog_json(["drive", "mkdir", name, "--account", account, "--parent", parent_id])
    file_info = data.get("file") or data.get("folder") or data.get("resource") or data
    folder_id = file_info.get("id") if isinstance(file_info, dict) else None
    if not folder_id:
        raise RuntimeError("Failed to parse folder id from gog drive mkdir")
    return folder_id


def _ensure_drive_path(account: str, parts: List[str]) -> str:
    parent_id = "root"
    for part in parts:
        existing = _find_drive_folder(account, part, parent_id)
        if existing:
            parent_id = existing
            continue
        parent_id = _create_drive_folder(account, part, parent_id)
    return parent_id


def _list_drive_pdfs(account: str, folder_id: str) -> List[Dict[str, Any]]:
    query = "mimeType='application/pdf' and trashed=false"
    data = _gog_json(["drive", "ls", "--account", account, "--parent", folder_id, "--query", query, "--max", "1000"])
    return data.get("files", [])


def _download_drive_file(account: str, file_id: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["gog", "drive", "download", file_id, "--account", account, "--out", str(out_path), "--no-input"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gog drive download failed")


def _create_store(config: Dict[str, Any], key: str, name: Optional[str], timeout: int) -> str:
    client = _require_client(model="gpt-4.1-mini", timeout=timeout)
    notebook = config.get("notebooks", {}).get(key)
    if not notebook:
        raise KeyError(f"Unknown notebook key: {key}")
    store_name = name or notebook.get("title") or key
    store = client._client.vector_stores.create(name=store_name)
    notebook["vector_store_id"] = store.id
    _save_config(config)
    return store.id


def _upload_files(
    vector_store_id: str,
    files: List[Path],
    timeout: int,
    batch_size: int,
) -> None:
    client = _require_client(model="gpt-4.1-mini", timeout=timeout)

    for batch in _chunk(files, batch_size):
        file_streams = [open(path, "rb") for path in batch]
        try:
            file_batches = client._client.vector_stores.file_batches
            if hasattr(file_batches, "upload_and_poll"):
                file_batches.upload_and_poll(vector_store_id=vector_store_id, files=file_streams)
            else:
                file_ids = [
                    client._client.files.create(file=stream, purpose="assistants").id
                    for stream in file_streams
                ]
                if hasattr(file_batches, "create_and_poll"):
                    file_batches.create_and_poll(vector_store_id=vector_store_id, file_ids=file_ids)
                else:
                    batch_obj = file_batches.create(vector_store_id=vector_store_id, file_ids=file_ids)
                    _poll_batch(file_batches, vector_store_id, batch_obj.id)
        finally:
            for stream in file_streams:
                stream.close()


def _poll_batch(file_batches: Any, vector_store_id: str, batch_id: str, timeout: int = 600) -> None:
    start = time.time()
    while True:
        batch = file_batches.retrieve(vector_store_id=vector_store_id, batch_id=batch_id)
        status = getattr(batch, "status", None) or batch.get("status")
        if status in {"completed", "failed", "cancelled"}:
            if status != "completed":
                raise RuntimeError(f"File batch ended with status: {status}")
            return
        if time.time() - start > timeout:
            raise TimeoutError("Timed out waiting for vector store ingestion.")
        time.sleep(2)


def _format_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return ""
    lines = ["Sources:"]
    for result in results:
        filename = (
            result.get("filename")
            or (result.get("file") or {}).get("filename")
            or result.get("file_id")
            or "Unknown file"
        )
        snippet = _extract_snippet(result)
        if snippet:
            snippet = snippet[:240]
            lines.append(f"- {filename}: {snippet}")
        else:
            lines.append(f"- {filename}")
    return "\n".join(lines)


def _extract_snippet(result: Dict[str, Any]) -> str:
    snippet = result.get("text") or result.get("content") or (result.get("document") or {}).get("text") or ""
    if isinstance(snippet, list):
        snippet = " ".join(
            str(part.get("text"))
            for part in snippet
            if isinstance(part, dict) and part.get("text")
        )
    return " ".join(str(snippet).split())


def _extract_terms(prompt: str) -> List[str]:
    stopwords = {
        "what", "which", "that", "this", "these", "those", "there", "their",
        "about", "from", "with", "using", "used", "into", "over", "under",
        "list", "explicitly", "named", "involved", "involving"
    }
    tokens = []
    current = []
    for ch in prompt.lower():
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))

    terms = [t for t in tokens if len(t) >= 4 and t not in stopwords]
    return terms[:12]


def _filter_results(
    results: List[Dict[str, Any]],
    score_threshold: Optional[float],
    required_terms: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    if not results:
        return []
    if score_threshold is None:
        score_threshold = -1
    filtered: List[Dict[str, Any]] = []
    term_list = [term.lower() for term in (required_terms or [])]
    for result in results:
        score = result.get("score")
        if score is not None and score < score_threshold:
            continue
        if term_list:
            snippet = _extract_snippet(result).lower()
            if not any(term in snippet for term in term_list):
                continue
        filtered.append(result)
    return filtered


def _sort_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not results:
        return []
    return sorted(results, key=lambda r: r.get("score") or 0, reverse=True)


def _build_context(results: List[Dict[str, Any]], max_results: int, max_chars: int) -> str:
    chunks: List[str] = []
    total = 0
    for result in results[:max_results]:
        filename = (
            result.get("filename")
            or (result.get("file") or {}).get("filename")
            or result.get("file_id")
            or "Unknown file"
        )
        snippet = _extract_snippet(result)
        if not snippet:
            continue
        entry = f"[{filename}]\n{snippet}\n"
        if total + len(entry) > max_chars:
            remaining = max_chars - total
            if remaining <= 0:
                break
            entry = entry[:remaining]
        chunks.append(entry)
        total += len(entry)
        if total >= max_chars:
            break
    return "\n".join(chunks).strip()


def _sync_drive_notebook(
    config: Dict[str, Any],
    notebook_key: str,
    data: Dict[str, Any],
    account: str,
    ensure_folders: bool,
    timeout: int,
    batch_size: int,
    dry_run: bool,
    state: Dict[str, Any],
) -> None:
    vector_store_id = data.get("vector_store_id")
    if not vector_store_id:
        vector_store_id = _create_store(config, notebook_key, None, timeout)
        data["vector_store_id"] = vector_store_id

    drive_folder_id = data.get("drive_folder_id")
    if not drive_folder_id:
        if not ensure_folders:
            raise ValueError(f"Missing drive_folder_id for {notebook_key}")
        root_name = config.get("drive", {}).get("root_folder", "Thanos")
        base_name = config.get("drive", {}).get("base_folder", "GalaxyDocs")
        folder_name = data.get("drive_folder_name") or notebook_key
        drive_folder_id = _ensure_drive_path(account, [root_name, base_name, folder_name])
        data["drive_folder_id"] = drive_folder_id
        _save_config(config)

    local_cache = Path(data.get("local_cache_dir") or (PROJECT_ROOT / "data" / "galaxy_docs" / notebook_key))
    local_cache.mkdir(parents=True, exist_ok=True)

    files = _list_drive_pdfs(account, drive_folder_id)
    store_state = state.setdefault("stores", {}).setdefault(vector_store_id, {"drive_files": {}})
    drive_files_state = store_state.setdefault("drive_files", {})

    to_download: List[Tuple[Dict[str, Any], Path]] = []
    for file_info in files:
        file_id = file_info.get("id")
        name = file_info.get("name") or f"{file_id}.pdf"
        modified = file_info.get("modifiedTime")
        if not file_id:
            continue
        existing = drive_files_state.get(file_id)
        if existing and existing.get("modifiedTime") == modified:
            continue
        safe_name = name.replace("/", "_")
        out_path = local_cache / f"{file_id}__{safe_name}"
        to_download.append((file_info, out_path))

    if dry_run:
        for file_info, out_path in to_download:
            print(f"[{notebook_key}] would download {file_info.get('name')} -> {out_path}")
        if not to_download:
            print(f"[{notebook_key}] no new PDFs found.")
        return

    downloaded_paths: List[Path] = []
    for file_info, out_path in to_download:
        _download_drive_file(account, file_info["id"], out_path)
        downloaded_paths.append(out_path)

    if downloaded_paths:
        _upload_files(vector_store_id, downloaded_paths, timeout, batch_size)

    for file_info, out_path in to_download:
        drive_files_state[file_info["id"]] = {
            "name": file_info.get("name"),
            "modifiedTime": file_info.get("modifiedTime"),
            "size": file_info.get("size"),
            "local_path": str(out_path),
            "last_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    _save_state(state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage OpenAI File Search vector stores.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create-store", help="Create a vector store and update config.")
    create_parser.add_argument("--key", required=True, help="Notebook key in config/notebooklm.json")
    create_parser.add_argument("--name", help="Optional vector store name override")
    create_parser.add_argument("--timeout", type=int, default=120, help="API timeout in seconds")

    upload_parser = subparsers.add_parser("upload", help="Upload PDFs to a vector store.")
    upload_parser.add_argument("--key", help="Notebook key in config/notebooklm.json")
    upload_parser.add_argument("--vector-store-id", help="Vector store ID (overrides key)")
    upload_parser.add_argument("--path", action="append", help="File or directory (repeatable)")
    upload_parser.add_argument("--batch-size", type=int, default=25, help="Number of files per batch")
    upload_parser.add_argument("--timeout", type=int, default=120, help="API timeout in seconds")
    upload_parser.add_argument("--dry-run", action="store_true", help="Show files without uploading")

    query_parser = subparsers.add_parser("query", help="Query a vector store via File Search.")
    query_parser.add_argument("--key", help="Notebook key in config/notebooklm.json")
    query_parser.add_argument("--vector-store-id", help="Vector store ID (overrides key)")
    query_parser.add_argument("--question", required=True, help="Prompt to send")
    query_parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model")
    query_parser.add_argument("--max-results", type=int, help="Max file search results")
    query_parser.add_argument("--timeout", type=int, default=120, help="API timeout in seconds")
    query_parser.add_argument("--include-sources", action="store_true", default=None, help="Include source snippets")
    query_parser.add_argument("--no-include-sources", action="store_true", help="Disable source snippets")
    query_parser.add_argument("--strict", action="store_true", default=None, help="Only answer using retrieved text")
    query_parser.add_argument("--no-strict", action="store_true", help="Disable strict mode")

    list_parser = subparsers.add_parser("list", help="List notebook keys and vector stores.")

    sync_parser = subparsers.add_parser("sync-drive", help="Sync PDFs from Google Drive folders.")
    sync_parser.add_argument("--key", action="append", help="Notebook key(s) to sync (repeatable)")
    sync_parser.add_argument("--account", help="Google account email for Drive access")
    sync_parser.add_argument("--ensure-folders", action="store_true", help="Create Drive folders if missing")
    sync_parser.add_argument("--timeout", type=int, default=120, help="API timeout in seconds")
    sync_parser.add_argument("--batch-size", type=int, default=25, help="Number of files per batch")
    sync_parser.add_argument("--dry-run", action="store_true", help="Show actions without downloading/uploading")

    args = parser.parse_args()
    config = _load_config()

    if args.command == "create-store":
        store_id = _create_store(config, args.key, args.name, args.timeout)
        print(f"Created vector store for '{args.key}': {store_id}")
        return

    if args.command == "upload":
        store_id, key = _resolve_store(config, args.key, args.vector_store_id)
        paths = args.path
        if not paths:
            if not key:
                raise ValueError("Provide --path or set source_paths in config.")
            notebook = config.get("notebooks", {}).get(key)
            paths = notebook.get("source_paths") if notebook else None
        if not paths:
            raise ValueError("No paths provided. Use --path or set source_paths in config.")
        files = _collect_files(paths)
        if not files:
            print("No files found.")
            return
        if args.dry_run:
            for path in files:
                print(path)
            print(f"Found {len(files)} files.")
            return
        _upload_files(store_id, files, args.timeout, args.batch_size)
        print(f"Uploaded {len(files)} files to {store_id}.")
        return

    if args.command == "query":
        store_id, key = _resolve_store(config, args.key, args.vector_store_id)
        defaults = _get_defaults(config)
        hints = None
        if key:
            notebook = config.get("notebooks", {}).get(key)
            hints = notebook.get("query_hints") if notebook else None
        question = _apply_query_hints(args.question, hints)
        max_results = args.max_results if args.max_results is not None else defaults["max_results"]
        if args.no_include_sources:
            include_sources = False
        elif args.include_sources is True:
            include_sources = True
        else:
            include_sources = defaults["include_results"]

        if args.no_strict:
            strict = False
        elif args.strict is True:
            strict = True
        else:
            strict = defaults["strict"]

        if strict:
            include_sources = True

        ranking_options = defaults.get("ranking_options")
        score_threshold = defaults.get("score_threshold")
        context_results = defaults.get("context_results", DEFAULT_CONTEXT_RESULTS)
        context_chars = defaults.get("context_chars", DEFAULT_CONTEXT_CHARS)
        instructions = None
        if strict:
            instructions = (
                "Answer ONLY using the retrieved file search results. "
                "If the answer is not explicitly present, respond: 'Not found in documents.'"
            )
        client = _require_client(model=args.model, timeout=args.timeout)
        ok, text, results = client.query(
            prompt=question,
            vector_store_id=store_id,
            max_results=max_results,
            include_results=include_sources,
            ranking_options=ranking_options,
            strict=strict,
            score_threshold=score_threshold,
            context_results=context_results,
            context_chars=context_chars,
            instructions=instructions,
        )
        if not ok:
            print(text)
            return
        print(text)
        if include_sources:
            sources = _format_results(results)
            if sources:
                print("\n" + sources)
        return

    if args.command == "list":
        notebooks = config.get("notebooks", {})
        for key, data in notebooks.items():
            title = data.get("title") or key
            store_id = data.get("vector_store_id") or "missing"
            print(f"{key}: {title} -> {store_id}")
        return

    if args.command == "sync-drive":
        state = _load_state()
        drive_config = config.get("drive", {})
        account = args.account or drive_config.get("account")
        if not account:
            raise ValueError("Missing Drive account. Set config.drive.account or pass --account.")

        keys = args.key
        if not keys:
            default_key = drive_config.get("default_notebook")
            if default_key:
                keys = [default_key]
            else:
                keys = list(config.get("notebooks", {}).keys())
        for key in keys:
            raw_key = key
            normalized_key = _ensure_notebook_config(config, key)
            if raw_key != normalized_key:
                notebook = config.get("notebooks", {}).get(normalized_key, {})
                notebook["title"] = raw_key.strip() or notebook.get("title", normalized_key)
                config["notebooks"][normalized_key] = notebook
                _save_config(config)
            notebook = config.get("notebooks", {}).get(normalized_key)
            if not notebook:
                print(f"Unknown notebook key: {normalized_key}")
                continue
            _sync_drive_notebook(
                config=config,
                notebook_key=normalized_key,
                data=notebook,
                account=account,
                ensure_folders=args.ensure_folders,
                timeout=args.timeout,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
                state=state,
            )
        return


if __name__ == "__main__":
    main()
