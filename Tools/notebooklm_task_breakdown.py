#!/usr/bin/env python3
"""
OpenAI File Search Task Breakdown Helper

Pulls WorkOS tasks and uses OpenAI File Search vector stores to generate
step-by-step breakdowns for Epic Orders/HOD and VersaCare work.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Tools.core.workos_gateway import WorkOSGateway  # noqa: E402
from Tools.openai_file_search import OpenAIFileSearchClient  # noqa: E402
CONFIG_PATH = PROJECT_ROOT / "config" / "notebooklm.json"
DEFAULT_TIMEOUT = 120
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_MAX_RESULTS = 20


def _load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def _normalize_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _match_notebook(task: Dict[str, Any], config: Dict[str, Any]) -> Optional[str]:
    title = _normalize_text(task.get("title"))
    description = _normalize_text(task.get("description"))
    client = _normalize_text(task.get("client_name") or task.get("client"))

    combined = " ".join(part for part in [title, description, client] if part)

    for key, keywords in config.get("matching", {}).items():
        for keyword in keywords:
            if keyword.lower() in combined:
                return key
    return None


def _build_prompt(task: Dict[str, Any]) -> str:
    title = task.get("title") or "Untitled"
    description = task.get("description") or ""
    client = task.get("client_name") or task.get("client") or ""

    prompt_parts = [
        "You are an Epic build assistant.",
        "Break down the task into 3-7 concrete Epic build steps.",
        "Include validation checks and any key stakeholders to loop in.",
        "If details are missing, list 2-4 clarification questions.",
        "Return in this exact format:",
        "Steps:",
        "- ...",
        "Validation:",
        "- ...",
        "Questions:",
        "- ...",
        "",
        f"Task: {title}",
    ]

    if client:
        prompt_parts.append(f"Client: {client}")

    if description:
        prompt_parts.append(f"Notes: {description}")

    return "\n".join(prompt_parts)


def _apply_query_hints(prompt: str, hints: Optional[List[str]]) -> str:
    if not hints:
        return prompt
    hint_text = ", ".join(hints)
    return f"{prompt}\n\nSearch focus terms: {hint_text}"


def _run_file_search(
    client: OpenAIFileSearchClient,
    vector_store_id: str,
    prompt: str,
    max_results: int,
    include_sources: bool,
    ranking_options: Optional[Dict[str, Any]] = None,
    strict: bool = False,
    score_threshold: Optional[float] = None,
    context_results: int = 6,
    context_chars: int = 4000,
    instructions: Optional[str] = None,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    return client.query(
        prompt=prompt,
        vector_store_id=vector_store_id,
        max_results=max_results,
        include_results=include_sources,
        ranking_options=ranking_options,
        strict=strict,
        score_threshold=score_threshold,
        context_results=context_results,
        context_chars=context_chars,
        instructions=instructions,
    )


async def _fetch_tasks(statuses: Iterable[str], limit: int) -> List[Dict[str, Any]]:
    gateway = WorkOSGateway()
    tasks: List[Dict[str, Any]] = []

    try:
        for status in statuses:
            status_tasks = await gateway.get_tasks(status=status, limit=limit)
            if isinstance(status_tasks, list):
                tasks.extend(status_tasks)
    finally:
        await gateway.close()

    # Deduplicate by id
    seen = set()
    unique_tasks = []
    for task in tasks:
        task_id = task.get("id")
        if task_id in seen:
            continue
        seen.add(task_id)
        unique_tasks.append(task)

    return unique_tasks


def _filter_tasks(
    tasks: List[Dict[str, Any]],
    config: Dict[str, Any],
    notebook_key: Optional[str],
    task_ids: Optional[set[int]],
) -> List[Tuple[Dict[str, Any], str]]:
    filtered: List[Tuple[Dict[str, Any], str]] = []

    for task in tasks:
        task_id = task.get("id")
        if task_ids and task_id not in task_ids:
            continue

        if notebook_key:
            match_key = notebook_key
        else:
            match_key = _match_notebook(task, config)

        if not match_key:
            continue

        filtered.append((task, match_key))

    return filtered


def _format_output(section_title: str, content: str) -> str:
    return f"## {section_title}\n\n{content.strip()}\n"


def _get_file_search_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    defaults = config.get("file_search_defaults", {})
    return {
        "max_results": defaults.get("max_results", DEFAULT_MAX_RESULTS),
        "include_results": defaults.get("include_results", True),
        "strict": defaults.get("strict", True),
        "ranking_options": defaults.get("ranking_options"),
        "score_threshold": defaults.get("score_threshold"),
        "context_results": defaults.get("context_results"),
        "context_chars": defaults.get("context_chars"),
    }


def _format_sources(results: List[Dict[str, Any]]) -> str:
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
        snippet = (
            result.get("text")
            or result.get("content")
            or (result.get("document") or {}).get("text")
            or ""
        )
        if isinstance(snippet, list):
            snippet = " ".join(
                str(part.get("text"))
                for part in snippet
                if isinstance(part, dict) and part.get("text")
            )
        snippet = " ".join(str(snippet).split())
        if snippet:
            snippet = snippet[:240]
            lines.append(f"- {filename}: {snippet}")
        else:
            lines.append(f"- {filename}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate File Search task breakdowns for Epic Orders/HOD and VersaCare work."
    )
    parser.add_argument(
        "--status",
        default="active,queued",
        help="Comma-separated WorkOS statuses to scan (default: active,queued)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max tasks to fetch per status (default: 50)",
    )
    parser.add_argument(
        "--notebook",
        choices=["orders_hod", "versacare"],
        help="Force a specific notebook mapping",
    )
    parser.add_argument(
        "--task-id",
        type=int,
        action="append",
        help="Limit to specific WorkOS task IDs (can repeat)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=5,
        help="Max tasks to process after filtering (default: 5)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="OpenAI API timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model for responses (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        help="Max File Search results to retrieve",
    )
    parser.add_argument(
        "--include-sources",
        action="store_true",
        default=None,
        help="Include source snippets from File Search results",
    )
    parser.add_argument(
        "--no-include-sources",
        action="store_true",
        help="Disable source snippets from File Search results",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=None,
        help="Only answer using retrieved text",
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Disable strict mode",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show matched tasks without calling OpenAI File Search",
    )
    parser.add_argument(
        "--output",
        help="Write markdown output to file (default: output/notebooklm_task_breakdown_YYYYMMDD.md)",
    )

    args = parser.parse_args()
    config = _load_config()

    statuses = [status.strip() for status in args.status.split(",") if status.strip()]
    task_ids = set(args.task_id) if args.task_id else None

    tasks = asyncio.run(_fetch_tasks(statuses=statuses, limit=args.limit))
    matched = _filter_tasks(tasks, config, args.notebook, task_ids)

    if not matched:
        print("No matching tasks found.")
        return

    matched = matched[: args.max]

    if args.dry_run:
        for task, key in matched:
            print(f"{task.get('id')}: {task.get('title')} -> {key}")
        return

    output_sections: List[str] = []
    defaults = _get_file_search_defaults(config)
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
    context_results = defaults.get("context_results")
    context_chars = defaults.get("context_chars")
    instructions = None
    if strict:
        instructions = (
            "Answer ONLY using the retrieved file search results. "
            "If the answer is not explicitly present, respond: 'Not found in documents.'"
        )

    client = OpenAIFileSearchClient(model=args.model, timeout=args.timeout)
    for task, key in matched:
        notebook = config["notebooks"].get(key)
        if not notebook:
            print(f"Skipping task {task.get('id')} - missing notebook mapping: {key}")
            continue

        vector_store_id = notebook.get("vector_store_id")
        if not vector_store_id:
            print(f"Skipping task {task.get('id')} - missing vector_store_id for {key}")
            continue

        prompt = _build_prompt(task)
        prompt = _apply_query_hints(prompt, notebook.get("query_hints"))
        ok, response, results = _run_file_search(
            client,
            vector_store_id,
            prompt,
            max_results=max_results,
            include_sources=include_sources,
            ranking_options=ranking_options,
            strict=strict,
            score_threshold=score_threshold,
            context_results=context_results or 6,
            context_chars=context_chars or 4000,
            instructions=instructions,
        )

        header = f"Task {task.get('id')}: {task.get('title')}"
        notebook_title = notebook.get("title") or key
        meta = f"Vector Store: {notebook_title} ({vector_store_id})"

        if ok:
            section = f"{meta}\n\n{response}"
            if args.include_sources and results:
                sources = _format_sources(results)
                if sources:
                    section = f"{section}\n\n{sources}"
        else:
            section = f"{meta}\n\nOpenAI File Search error: {response}"

        output_sections.append(_format_output(header, section))

    timestamp = datetime.now().strftime("%Y%m%d")
    output_path = Path(args.output) if args.output else PROJECT_ROOT / "output" / f"notebooklm_task_breakdown_{timestamp}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write("# OpenAI File Search Task Breakdowns\n\n")
        f.write("\n".join(output_sections))

    print(f"Wrote breakdowns to {output_path}")


if __name__ == "__main__":
    main()
