#!/usr/bin/env python3
"""
Unified Memory Capture Router.

Routes extracted learnings to:
- Memory V2 (vector store) via unified_capture (Memory V2 + Graphiti)
- ByteRover (project/technical knowledge) via brv CLI

Designed to be used by hooks and OpenClaw plugins with minimal manual steps.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT_DIR / "State"
LOG_DIR = ROOT_DIR / "logs"
STATE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

DEDUPE_PATH = STATE_DIR / "memory_capture_dedupe.json"
DEDUPE_TTL_DAYS = 7
BACKLOG_PATH = STATE_DIR / "memory_capture_backlog.jsonl"
BRV_BACKLOG_PATH = STATE_DIR / "byterover_backlog.jsonl"
BACKLOG_MAX_ITEMS = 500
BACKLOG_TTL_DAYS = 30
BACKLOG_FLUSH_INTERVAL_SECONDS = 600

_last_backlog_flush = 0.0


# ----------------------------
# Extraction Patterns
# ----------------------------

DECISION_PATTERNS = [
    r"(?:decided to|chose to|going with|will use|opted for|selected)\s+(.{20,200})",
    r"(?:the approach is|solution is|best option is|implemented)\s+(.{20,200})",
    r"(?:architecture|design):?\s*(.{20,200})",
]

BUG_FIX_PATTERNS = [
    r"(?:fixed|resolved|solved|patched)\s+(?:the\s+)?(?:bug|issue|problem|error)\s*(?:by|with|:)?\s*(.{20,200})",
    r"(?:the issue was|problem was|root cause was|caused by)\s+(.{20,200})",
    r"(?:bug|error|issue):\s*(.{20,200})",
]

PATTERN_PATTERNS = [
    r"(?:pattern|approach|technique|method):\s*(.{20,200})",
    r"(?:always|never|should)\s+(.{20,200})",
    r"(?:lesson learned|takeaway|insight):\s*(.{20,200})",
    r"(?:this works because|key insight is|remember that)\s+(.{20,200})",
]

PLAN_PATTERNS = [
    r"(?:this weekend|tomorrow|tonight|saturday|sunday)(?:'s plan|,)?\s*(?:we'll|I'll|let's|going to|plan to|will)\s+(.{20,300})",
    r"(?:plan for|scheduled for|agenda for)\s+(?:this weekend|tomorrow|tonight|saturday|sunday)\s*[:\-]?\s*(.{20,300})",
    r"(?:weekend tasks?|tomorrow's tasks?|chill tasks?)[:\-]?\s*(.{20,500})",
    r"(?:let's do|we should do|I should do|need to do)\s+(?:this weekend|tomorrow)?\s*[:\-]?\s*(.{20,300})",
]

COMMITMENT_PATTERNS = [
    r"(?:I'll|we'll|I will|we will|going to|plan to|committed to)\s+(.{20,200})",
    r"(?:need to|have to|must|should)\s+(?:finish|complete|do|handle|take care of)\s+(.{20,200})",
    r"(?:don't forget|remember to|make sure to)\s+(.{20,200})",
]

COMPLETED_PATTERNS = [
    r"(?:already done|already finished|completed|done with|finished)\s+(.{20,200})",
    r"(?:passport forms?|forms?)\s+(?:are|were|is)\s+(?:done|completed|finished|submitted)",
    r"(?:checked off|crossed off|marked as done)\s+(.{20,200})",
]

TECH_KEYWORDS = [
    "api", "bug", "error", "issue", "fix", "fixed", "resolved", "root cause",
    "refactor", "architecture", "design", "system", "pipeline", "mcp",
    "openclaw", "vector", "embedding", "database", "schema", "migration",
    "typescript", "python", "node", "workers", "cloudflare", "deploy",
    "integration", "cli", "runtime", "performance", "latency", "cache",
]


# ----------------------------
# Models
# ----------------------------

@dataclass
class LearningItem:
    type: str
    content: str
    confidence: float
    source: str


# ----------------------------
# Dedupe Cache
# ----------------------------

class DedupeCache:
    def __init__(self, path: Path = DEDUPE_PATH, ttl_days: int = DEDUPE_TTL_DAYS):
        self.path = path
        self.ttl_seconds = ttl_days * 86400

    def _now(self) -> float:
        return time.time()

    def _load(self) -> Dict[str, float]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text())
            if isinstance(data, dict):
                return {k: float(v) for k, v in data.items()}
        except Exception:
            pass
        return {}

    def _save(self, data: Dict[str, float]) -> None:
        try:
            self.path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save dedupe cache: {e}")

    def _prune(self, data: Dict[str, float]) -> Dict[str, float]:
        cutoff = self._now() - self.ttl_seconds
        return {k: v for k, v in data.items() if v >= cutoff}

    def seen(self, key: str) -> bool:
        data = self._prune(self._load())
        if key in data:
            return True
        data[key] = self._now()
        self._save(data)
        return False


def _hash_key(text: str, item_type: str) -> str:
    norm = f"{item_type}:{text.strip().lower()}"
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


# ----------------------------
# Extraction Helpers
# ----------------------------

def _clean_text(text: str) -> str:
    text = re.sub(r'[.,:;]+$', '', text.strip())
    text = ' '.join(text.split())
    if text:
        text = text[0].upper() + text[1:]
    return text


def _extract_with_patterns(content: str) -> List[LearningItem]:
    items: List[LearningItem] = []
    seen = set()

    def add_items(patterns: Iterable[str], item_type: str, confidence: float):
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                raw = match.group(1).strip() if match.lastindex else match.group(0).strip()
                if not raw or len(raw) < 20:
                    continue
                cleaned = _clean_text(raw)
                if cleaned in seen:
                    continue
                seen.add(cleaned)
                items.append(LearningItem(item_type, cleaned, confidence, source="regex"))

    add_items(DECISION_PATTERNS, "decision", 0.7)
    add_items(BUG_FIX_PATTERNS, "bug_fix", 0.8)
    add_items(PATTERN_PATTERNS, "pattern", 0.6)
    add_items(PLAN_PATTERNS, "plan", 0.9)
    add_items(COMMITMENT_PATTERNS, "commitment", 0.85)
    add_items(COMPLETED_PATTERNS, "completed", 0.95)

    return items


def _classify_point(point: str) -> str:
    text = point.lower()
    if any(k in text for k in ["decided", "chose", "going with", "will use", "selected"]):
        return "decision"
    if any(k in text for k in ["fixed", "resolved", "bug", "issue", "error", "root cause"]):
        return "bug_fix"
    if any(k in text for k in ["pattern", "always", "never", "best practice", "insight"]):
        return "pattern"
    if any(k in text for k in ["tomorrow", "tonight", "weekend", "plan"]):
        return "plan"
    if any(k in text for k in ["remember to", "need to", "must", "committed"]):
        return "commitment"
    if any(k in text for k in ["done", "completed", "finished"]):
        return "completed"
    return "learning"


def _extract_llm_points(messages: List[Dict[str, str]], max_points: int = 10) -> List[LearningItem]:
    try:
        from Tools.conversation_summarizer import ConversationSummarizer
        summarizer = ConversationSummarizer(model="anthropic/claude-sonnet-4-5", max_tokens=1200)
        points = summarizer.extract_key_points(messages, max_points=max_points)
        items = []
        for p in points:
            cleaned = _clean_text(p)
            if cleaned:
                items.append(LearningItem(_classify_point(cleaned), cleaned, 0.6, source="llm"))
        return items
    except Exception as e:
        logger.warning(f"LLM extraction unavailable: {e}")
        return []


def extract_learnings_from_text(content: str, allow_llm: bool = False,
                                messages: Optional[List[Dict[str, str]]] = None) -> List[LearningItem]:
    items = _extract_with_patterns(content)

    if allow_llm and messages:
        items.extend(_extract_llm_points(messages))

    # Dedupe by content, keep highest confidence
    merged: Dict[str, LearningItem] = {}
    for item in items:
        key = item.content.lower()
        if key not in merged or item.confidence > merged[key].confidence:
            merged[key] = item

    merged_items = list(merged.values())
    merged_items.sort(key=lambda x: x.confidence, reverse=True)
    return merged_items[:20]


# ----------------------------
# Transcript Helpers
# ----------------------------

def read_transcript(transcript_path: str) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = []
    try:
        path = Path(transcript_path).expanduser()
        if not path.exists():
            return messages
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"Error reading transcript: {e}")
    return messages


def extract_text_content(messages: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for msg in messages:
        if isinstance(msg, dict):
            if "content" in msg:
                content = msg["content"]
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            parts.append(item["text"])
                        elif isinstance(item, str):
                            parts.append(item)
            if "message" in msg:
                inner = msg["message"]
                if isinstance(inner, dict) and "content" in inner:
                    if isinstance(inner["content"], str):
                        parts.append(inner["content"])
    return "\n\n".join(parts)


# ----------------------------
# ByteRover Integration
# ----------------------------

def _brv_available() -> bool:
    try:
        env = os.environ.copy()
        env["BRV_FORCE_FILE_TOKEN_STORE"] = "1"
        result = subprocess.run(
            ["brv", "status", "--headless"],
            capture_output=True,
            text=True,
            timeout=3,
            env=env
        )
        return "Status: Logged in" in (result.stdout or "") or "Status: Logged in" in (result.stderr or "")
    except Exception:
        return False


def _ensure_brv_running() -> bool:
    if _brv_available():
        return True
    script_path = ROOT_DIR / "scripts" / "start-brv.sh"
    if not script_path.exists():
        return False
    try:
        subprocess.run(["bash", str(script_path)], capture_output=True, text=True, timeout=8, cwd=str(ROOT_DIR))
    except Exception:
        pass
    return _brv_available()


def _is_technical(item: LearningItem, context: Dict[str, Any]) -> bool:
    text = item.content.lower()
    if any(k in text for k in TECH_KEYWORDS):
        return True
    project = (context.get("project") or "").lower()
    if project in ("thanos", "openclaw"):
        return True
    if re.search(r"\.[a-z]{2,4}\b", text):
        return True
    return False


def _extract_reason(text: str) -> str:
    for marker in ["because", "due to", "caused by", "so that"]:
        if marker in text.lower():
            parts = text.split(marker, 1)
            if len(parts) == 2:
                return _clean_text(parts[1])
    return "Captured from session transcript"


def _format_brv_entry(item: LearningItem, context: Dict[str, Any], session_id: str) -> str:
    category = item.type.replace("_", " ").title()
    reason = _extract_reason(item.content)
    project = context.get("project") or "unknown"
    client = context.get("client")
    ctx = f"project={project}"
    if client:
        ctx += f", client={client}"
    ctx += f", session={session_id}"
    return f"Category: {category} - {item.content}. Reason: {reason}. Context: {ctx}."


def _curate_brv(items: List[LearningItem], context: Dict[str, Any], session_id: str) -> int:
    if not items:
        return 0
    if not _ensure_brv_running():
        for item in items:
            if item.type in ("decision", "bug_fix", "pattern", "learning") and _is_technical(item, context):
                _enqueue_brv_backlog(item, context, session_id)
        return 0
    curated = 0
    for item in items:
        if item.type not in ("decision", "bug_fix", "pattern", "learning"):
            continue
        if not _is_technical(item, context):
            continue
        try:
            payload = _format_brv_entry(item, context, session_id)
            env = os.environ.copy()
            env["BRV_FORCE_FILE_TOKEN_STORE"] = "1"
            result = subprocess.run(
                ["brv", "curate", "--headless", payload],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            if result.returncode == 0:
                curated += 1
            else:
                _enqueue_brv_backlog(item, context, session_id)
        except Exception:
            _enqueue_brv_backlog(item, context, session_id)
            continue
    return curated


# ----------------------------
# Memory V2 + Graphiti Capture
# ----------------------------

def _capture_memory(items: List[LearningItem], context: Dict[str, Any], session_id: str,
                    source: str, dedupe: DedupeCache) -> int:
    if os.environ.get("MEMORY_CAPTURE_BACKLOG_ONLY", "").lower() in ("1", "true", "yes"):
        for item in items:
            _enqueue_backlog(item, context, session_id, source)
        return 0
    try:
        from Tools.memory_v2.unified_capture import capture, CaptureType
    except Exception as e:
        logger.warning(f"Unified capture unavailable: {e}")
        for item in items:
            _enqueue_backlog(item, context, session_id, source)
        return 0

    stored = 0
    for item in items:
        key = _hash_key(item.content, item.type)
        if dedupe.seen(key):
            continue

        capture_type = {
            "decision": CaptureType.DECISION,
            "bug_fix": CaptureType.LEARNING,
            "pattern": CaptureType.PATTERN,
            "plan": CaptureType.NOTE,
            "commitment": CaptureType.NOTE,
            "completed": CaptureType.FACT,
        }.get(item.type, CaptureType.LEARNING)

        importance = 1.0
        if item.type in ("plan", "commitment"):
            importance = 1.5
        elif item.type == "completed":
            importance = 1.2

        metadata = {
            "type": item.type,
            "extraction_type": item.type,
            "extraction_source": item.source,
            "confidence": item.confidence,
            "importance": importance,
            "session_id": session_id,
            "extracted_at": datetime.now().isoformat(),
        }
        if context.get("client"):
            metadata["client"] = context["client"]
        if context.get("project"):
            metadata["project"] = context["project"]

        try:
            capture(item.content, capture_type=capture_type, metadata=metadata, source=source)
            stored += 1
        except Exception as e:
            logger.warning(f"Memory capture failed: {e}")
            _enqueue_backlog(item, context, session_id, source, capture_type=capture_type, metadata=metadata)

    return stored


# ----------------------------
# Public Entry Points
# ----------------------------

def capture_from_text(
    content: str,
    context: Dict[str, Any],
    session_id: str,
    source: str = "openclaw",
    allow_llm: bool = False,
    messages: Optional[List[Dict[str, str]]] = None
) -> Dict[str, int]:
    _maybe_process_backlogs()
    dedupe = DedupeCache()
    items = extract_learnings_from_text(content, allow_llm=allow_llm, messages=messages)

    stored = _capture_memory(items, context, session_id, source, dedupe)
    curated = _curate_brv(items, context, session_id)

    return {"memory_v2": stored, "byterover": curated}


def capture_from_transcript(
    transcript_path: str,
    context: Dict[str, Any],
    session_id: str,
    source: str = "openclaw",
    allow_llm: bool = True
) -> Dict[str, int]:
    _maybe_process_backlogs()
    messages_raw = read_transcript(transcript_path)
    content = extract_text_content(messages_raw)
    messages = []
    for msg in messages_raw:
        if isinstance(msg, dict) and msg.get("role") and msg.get("content"):
            text = msg.get("content")
            if isinstance(text, str):
                messages.append({"role": msg["role"], "content": text})
    return capture_from_text(content, context, session_id, source, allow_llm=allow_llm, messages=messages)


def capture_exchange(
    messages: List[Dict[str, str]],
    context: Dict[str, Any],
    session_id: str,
    source: str = "openclaw",
    allow_llm: bool = False
) -> Dict[str, int]:
    _maybe_process_backlogs()
    text_parts = [m.get("content", "") for m in messages if m.get("content")]
    content = "\n\n".join(text_parts)
    if not _should_capture(content):
        return {"memory_v2": 0, "byterover": 0}
    return capture_from_text(content, context, session_id, source, allow_llm=allow_llm, messages=messages)


def _should_capture(content: str) -> bool:
    if not content or len(content) < 40:
        return False
    lower = content.lower()
    keywords = [
        "decided", "decision", "chose", "will use", "fixed", "resolved",
        "pattern", "lesson", "insight", "root cause", "bug", "issue", "plan",
        "commit", "remember to", "need to", "must", "should"
    ]
    return any(k in lower for k in keywords)


def capture_checkpoint_extraction(extraction: Dict[str, Any], source: str = "session_end_hook") -> bool:
    try:
        from Tools.memory_v2.service import MemoryService
        service = MemoryService()
        session_id = extraction.get("session_id", "unknown")
        duration = extraction.get("duration_minutes", 0)
        prompt_count = extraction.get("prompt_count", 0)
        project = extraction.get("project", "unknown")
        client = extraction.get("client")
        summary = extraction.get("cumulative_summary", "")
        facts = extraction.get("all_facts", [])
        files = extraction.get("all_files_modified", [])
        content_parts = [
            f"Session {session_id}: {duration}min, {prompt_count} prompts",
            f"Project: {project}" + (f" (Client: {client})" if client else ""),
        ]
        if summary:
            content_parts.append(f"\nSummary:\n{summary}")
        if facts:
            content_parts.append(f"\nKey facts:\n- " + "\n- ".join(facts[:10]))
        if files:
            content_parts.append(f"\nFiles:\n- " + "\n- ".join(files[:10]))
        content = "\n".join(content_parts)
        service.add(
            content=content,
            metadata={
                "type": "session_summary",
                "session_id": session_id,
                "project": project,
                "client": client,
                "duration_minutes": duration,
                "prompt_count": prompt_count,
                "source": source,
                "extracted_at": datetime.now().isoformat()
            }
        )
        return True
    except Exception as e:
        logger.warning(f"Checkpoint memory capture failed: {e}")
        _enqueue_checkpoint_backlog(extraction, source=source)
        return False


# ----------------------------
# Backlog Handling
# ----------------------------

def _maybe_process_backlogs() -> None:
    if os.environ.get("MEMORY_CAPTURE_BACKLOG_ONLY", "").lower() in ("1", "true", "yes"):
        return
    global _last_backlog_flush
    now = time.time()
    if now - _last_backlog_flush < BACKLOG_FLUSH_INTERVAL_SECONDS:
        return
    _last_backlog_flush = now
    try:
        process_memory_backlog()
        process_brv_backlog()
    except Exception:
        # Never block capture
        pass


def _enqueue_backlog(
    item: LearningItem,
    context: Dict[str, Any],
    session_id: str,
    source: str,
    capture_type: Any = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    record = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "source": source,
        "content": item.content,
        "item_type": item.type,
        "confidence": item.confidence,
        "context": context,
        "capture_type": getattr(capture_type, "value", None),
        "metadata": metadata or {},
        "attempts": 0,
        "last_error": ""
    }
    _append_backlog(BACKLOG_PATH, record)


def _enqueue_checkpoint_backlog(extraction: Dict[str, Any], source: str) -> None:
    record = {
        "timestamp": datetime.now().isoformat(),
        "type": "checkpoint",
        "source": source,
        "extraction": extraction,
        "attempts": 0,
        "last_error": ""
    }
    _append_backlog(BACKLOG_PATH, record)


def _enqueue_brv_backlog(item: LearningItem, context: Dict[str, Any], session_id: str) -> None:
    record = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "content": item.content,
        "item_type": item.type,
        "context": context,
        "attempts": 0,
        "last_error": ""
    }
    _append_backlog(BRV_BACKLOG_PATH, record)


def _append_backlog(path: Path, record: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        _trim_backlog(path)
    except Exception as e:
        logger.warning(f"Failed to append backlog: {e}")


def _trim_backlog(path: Path) -> None:
    try:
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= BACKLOG_MAX_ITEMS:
            return
        trimmed = lines[-BACKLOG_MAX_ITEMS:]
        path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
    except Exception:
        pass


def _load_backlog(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    try:
        cutoff = datetime.now() - timedelta(days=BACKLOG_TTL_DAYS)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts = rec.get("timestamp")
                    if ts:
                        try:
                            if datetime.fromisoformat(ts) < cutoff:
                                continue
                        except Exception:
                            pass
                    records.append(rec)
                except Exception:
                    continue
    except Exception:
        return []
    return records


def _write_backlog(path: Path, records: List[Dict[str, Any]]) -> None:
    try:
        if not records:
            if path.exists():
                path.unlink()
            return
        with open(path, "w", encoding="utf-8") as f:
            for rec in records[-BACKLOG_MAX_ITEMS:]:
                f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def process_memory_backlog(max_items: int = 50) -> int:
    try:
        from Tools.memory_v2.unified_capture import capture, CaptureType
    except Exception:
        return 0

    records = _load_backlog(BACKLOG_PATH)
    if not records:
        return 0

    remaining: List[Dict[str, Any]] = []
    processed = 0
    for rec in records[:max_items]:
        if rec.get("type") == "checkpoint":
            try:
                from Tools.memory_v2.service import MemoryService
                service = MemoryService()
                extraction = rec.get("extraction", {})
                session_id = extraction.get("session_id", "unknown")
                duration = extraction.get("duration_minutes", 0)
                prompt_count = extraction.get("prompt_count", 0)
                project = extraction.get("project", "unknown")
                client = extraction.get("client")
                summary = extraction.get("cumulative_summary", "")
                facts = extraction.get("all_facts", [])
                files = extraction.get("all_files_modified", [])
                content_parts = [
                    f"Session {session_id}: {duration}min, {prompt_count} prompts",
                    f"Project: {project}" + (f" (Client: {client})" if client else ""),
                ]
                if summary:
                    content_parts.append(f"\nSummary:\n{summary}")
                if facts:
                    content_parts.append(f"\nKey facts:\n- " + "\n- ".join(facts[:10]))
                if files:
                    content_parts.append(f"\nFiles:\n- " + "\n- ".join(files[:10]))
                content = "\n".join(content_parts)
                service.add(
                    content=content,
                    metadata={
                        "type": "session_summary",
                        "session_id": session_id,
                        "project": project,
                        "client": client,
                        "duration_minutes": duration,
                        "prompt_count": prompt_count,
                        "source": rec.get("source", "session_end_hook"),
                        "extracted_at": datetime.now().isoformat()
                    }
                )
                processed += 1
            except Exception as e:
                rec["attempts"] = rec.get("attempts", 0) + 1
                rec["last_error"] = str(e)
                remaining.append(rec)
            continue

        try:
            capture_type_val = rec.get("capture_type")
            capture_type = CaptureType[capture_type_val.upper()] if capture_type_val else CaptureType.LEARNING
            metadata = rec.get("metadata", {})
            source = rec.get("source", "openclaw")
            capture(rec.get("content", ""), capture_type=capture_type, metadata=metadata, source=source)
            processed += 1
        except Exception as e:
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["last_error"] = str(e)
            remaining.append(rec)

    remaining.extend(records[max_items:])
    _write_backlog(BACKLOG_PATH, remaining)
    return processed


def process_brv_backlog(max_items: int = 50) -> int:
    if not _ensure_brv_running():
        return 0
    records = _load_backlog(BRV_BACKLOG_PATH)
    if not records:
        return 0

    remaining: List[Dict[str, Any]] = []
    processed = 0
    for rec in records[:max_items]:
        try:
            content = rec.get("content", "")
            item_type = rec.get("item_type", "learning")
            context = rec.get("context", {}) or {}
            session_id = rec.get("session_id", "unknown")
            item = LearningItem(item_type, content, 0.6, source="backlog")
            payload = _format_brv_entry(item, context, session_id)
            result = subprocess.run(["brv", "curate", "--headless", payload], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                processed += 1
            else:
                rec["attempts"] = rec.get("attempts", 0) + 1
                rec["last_error"] = (result.stderr or result.stdout or "")[:200]
                remaining.append(rec)
        except Exception as e:
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["last_error"] = str(e)
            remaining.append(rec)

    remaining.extend(records[max_items:])
    _write_backlog(BRV_BACKLOG_PATH, remaining)
    return processed
