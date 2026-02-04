#!/usr/bin/env python3
"""
OpenAI RAG cross-reference helper for Epic self-learning.

Queries mapped OpenAI File Search vector stores to surface existing knowledge
before asking Jeremy for clarifications.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / "config" / "notebooklm.json").exists():
            return parent
    return start


def _load_config() -> Dict[str, Any]:
    root = _find_project_root(Path(__file__).resolve())
    config_path = root / "config" / "notebooklm.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r") as f:
        return json.load(f)


def _normalize_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _truncate(text: str, max_chars: int = 800) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


class OpenAIRagCrossRef:
    """Wrapper for OpenAI File Search cross-references."""

    def __init__(self) -> None:
        self.config = _load_config()
        self._ensure_tools_on_path()

    def _ensure_tools_on_path(self) -> None:
        root = _find_project_root(Path(__file__).resolve())
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

    def resolve_notebook_for_domain(self, domain: Optional[str]) -> Optional[Dict[str, Any]]:
        if not domain:
            return None
        key = self.config.get("domain_notebooks", {}).get(domain)
        if not key:
            return None
        return self.config.get("notebooks", {}).get(key)

    def resolve_notebook_for_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        combined = " ".join(
            part
            for part in [
                _normalize_text(task.get("title")),
                _normalize_text(task.get("description")),
                _normalize_text(task.get("client_name") or task.get("client")),
            ]
            if part
        )
        for key, keywords in self.config.get("matching", {}).items():
            for keyword in keywords:
                if keyword.lower() in combined:
                    return self.config.get("notebooks", {}).get(key)
        return None

    def _build_prompt(self, question: str, hints: Optional[list[str]]) -> str:
        base = (
            "Answer ONLY using the retrieved documents. "
            "If the answer is not explicitly present, respond: 'Not found in documents.'\n\n"
            f"Question: {question}"
        )
        if hints:
            hint_text = ", ".join(hints)
            return f"{base}\n\nSearch focus terms: {hint_text}"
        return base

    def _query_vector_store(
        self,
        vector_store_id: str,
        question: str,
        notebook: Dict[str, Any],
        timeout: int,
    ) -> Tuple[bool, str]:
        try:
            from Tools.openai_file_search import OpenAIFileSearchClient
        except Exception as exc:
            return False, f"OpenAI File Search unavailable: {exc}"

        defaults = self.config.get("file_search_defaults", {})
        max_results = defaults.get("max_results", 20)
        include_results = defaults.get("include_results", False)
        strict = defaults.get("strict", True)
        score_threshold = defaults.get("score_threshold")
        context_results = defaults.get("context_results") or 3
        context_chars = defaults.get("context_chars") or 4000
        ranking_options = defaults.get("ranking_options")

        client = OpenAIFileSearchClient(timeout=timeout)
        prompt = self._build_prompt(question, notebook.get("query_hints"))
        ok, response, _ = client.query(
            prompt=prompt,
            vector_store_id=vector_store_id,
            max_results=max_results,
            include_results=include_results,
            ranking_options=ranking_options,
            strict=strict,
            score_threshold=score_threshold,
            context_results=context_results,
            context_chars=context_chars,
        )
        return ok, response

    def summarize_for_question(self, domain: Optional[str], question: str, timeout: int = 120) -> Optional[str]:
        notebook = self.resolve_notebook_for_domain(domain)
        if not notebook:
            return None
        vector_store_id = notebook.get("vector_store_id")
        if not vector_store_id:
            return None

        ok, response = self._query_vector_store(vector_store_id, question, notebook, timeout)
        if not ok:
            return None
        cleaned = _truncate(str(response).strip())
        return f"OpenAI RAG ({notebook.get('title', 'Vector Store')}) says:\n{cleaned}"

    def summarize_for_task(self, task: Dict[str, Any], domain: Optional[str], timeout: int = 120) -> Optional[str]:
        notebook = self.resolve_notebook_for_domain(domain) or self.resolve_notebook_for_task(task)
        if not notebook:
            return None
        vector_store_id = notebook.get("vector_store_id")
        if not vector_store_id:
            return None

        title = task.get("title") or ""
        question = (
            "Based on the documents, summarize the standard approach for this task "
            "in 2-4 bullets, <=80 words."
        )
        prompt = f"{question}\n\nTask: {title}"
        ok, response = self._query_vector_store(vector_store_id, prompt, notebook, timeout)
        if not ok:
            return None
        cleaned = _truncate(str(response).strip())
        return f"OpenAI RAG ({notebook.get('title', 'Vector Store')}) says:\n{cleaned}"
