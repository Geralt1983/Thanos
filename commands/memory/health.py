"""
Memory Health Dashboard Command

Displays memory system health metrics including:
- Total memory count
- Heat distribution (hot/warm/cold)
- Average heat score
- Pinned memories count
- Storage utilization
- Last backup timestamp
- Warnings for backup age and retrieval issues

Usage:
    python -m commands.memory.health

Output saved to: History/MemoryHealth/
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

from Tools.memory_v2.config import NEON_DATABASE_URL
from Tools.output_formatter import format_header, format_list, is_mobile


def fetch_memory_stats() -> Dict[str, Any]:
    """
    Fetch memory statistics from the database.

    Returns:
        Dictionary with memory counts, heat distribution, and averages
    """
    try:
        with _get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get overall statistics
                cur.execute("""
                    SELECT
                        COUNT(*) as total_memories,
                        AVG(COALESCE((payload->>'heat')::float, 1.0)) as avg_heat,
                        COUNT(*) FILTER (WHERE COALESCE((payload->>'pinned')::boolean, FALSE) = TRUE) as pinned_count,
                        SUM(
                            CASE
                                WHEN COALESCE((payload->>'heat')::float, 1.0) >= 0.7 THEN 1
                                ELSE 0
                            END
                        ) as hot_count,
                        SUM(
                            CASE
                                WHEN COALESCE((payload->>'heat')::float, 1.0) >= 0.3
                                AND COALESCE((payload->>'heat')::float, 1.0) < 0.7 THEN 1
                                ELSE 0
                            END
                        ) as warm_count,
                        SUM(
                            CASE
                                WHEN COALESCE((payload->>'heat')::float, 1.0) < 0.3 THEN 1
                                ELSE 0
                            END
                        ) as cold_count
                    FROM thanos_memories
                """)

                stats = cur.fetchone()

                if not stats or stats['total_memories'] == 0:
                    return {
                        "total_memories": 0,
                        "avg_heat": 0.0,
                        "pinned_count": 0,
                        "hot_count": 0,
                        "warm_count": 0,
                        "cold_count": 0,
                        "hot_pct": 0.0,
                        "warm_pct": 0.0,
                        "cold_pct": 0.0
                    }

                total = stats['total_memories']

                return {
                    "total_memories": total,
                    "avg_heat": round(float(stats['avg_heat']), 3) if stats['avg_heat'] else 0.0,
                    "pinned_count": stats['pinned_count'] or 0,
                    "hot_count": stats['hot_count'] or 0,
                    "warm_count": stats['warm_count'] or 0,
                    "cold_count": stats['cold_count'] or 0,
                    "hot_pct": round((stats['hot_count'] or 0) / total * 100, 1),
                    "warm_pct": round((stats['warm_count'] or 0) / total * 100, 1),
                    "cold_pct": round((stats['cold_count'] or 0) / total * 100, 1)
                }

    except Exception as e:
        return {"error": f"Failed to fetch memory stats: {str(e)}"}


def fetch_storage_metrics() -> Dict[str, Any]:
    """
    Fetch storage size metrics from the database.

    Returns:
        Dictionary with storage size in MB
    """
    try:
        with _get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get table size
                cur.execute("""
                    SELECT
                        pg_size_pretty(pg_total_relation_size('thanos_memories')) as table_size,
                        pg_total_relation_size('thanos_memories') as table_size_bytes
                """)

                result = cur.fetchone()

                if result:
                    size_mb = round(result['table_size_bytes'] / (1024 * 1024), 2)
                    return {
                        "table_size": result['table_size'],
                        "size_mb": size_mb
                    }

                return {"table_size": "0 bytes", "size_mb": 0.0}

    except Exception as e:
        return {"error": f"Failed to fetch storage metrics: {str(e)}"}


def fetch_backup_status() -> Dict[str, Any]:
    """
    Check for last backup timestamp and generate warnings.

    Returns:
        Dictionary with last backup timestamp, age in days, and warnings
    """
    try:
        project_root = Path(__file__).parent.parent.parent
        backups_dir = project_root / "backups"

        if not backups_dir.exists():
            return {
                "last_backup": None,
                "age_days": None,
                "warning": "No backups directory found",
                "severity": "critical"
            }

        # Find most recent backup file
        backup_files = list(backups_dir.glob("*backup*.tar.gz")) + list(backups_dir.glob("*backup*.sql"))

        if not backup_files:
            return {
                "last_backup": None,
                "age_days": None,
                "warning": "No backup files found",
                "severity": "critical"
            }

        # Get the most recent backup
        most_recent = max(backup_files, key=lambda p: p.stat().st_mtime)
        last_modified = datetime.fromtimestamp(most_recent.stat().st_mtime)
        age_days = (datetime.now() - last_modified).days

        # Generate warning based on backup age
        warning = None
        severity = None

        if age_days > 14:
            warning = f"Backup is {age_days} days old - CRITICAL: run backup immediately"
            severity = "critical"
        elif age_days > 7:
            warning = f"Backup is {age_days} days old - consider running a fresh backup soon"
            severity = "warning"
        elif age_days > 3:
            warning = f"Backup is {age_days} days old - should refresh soon"
            severity = "info"

        return {
            "last_backup": last_modified,
            "age_days": age_days,
            "backup_file": most_recent.name,
            "warning": warning,
            "severity": severity
        }

    except Exception as e:
        return {
            "last_backup": None,
            "age_days": None,
            "warning": f"Error checking backups: {str(e)}",
            "severity": "error"
        }


def check_retrieval_health() -> Dict[str, Any]:
    """
    Test memory retrieval functionality and performance.

    Returns:
        Dictionary with retrieval status, warnings, and performance metrics
    """
    import time

    try:
        with _get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Test 1: Basic query performance
                start_time = time.time()
                cur.execute("SELECT COUNT(*) as count FROM thanos_memories LIMIT 1")
                query_time = time.time() - start_time

                # Test 2: Sample memory retrieval
                start_time = time.time()
                cur.execute("""
                    SELECT id, payload->>'content' as content
                    FROM thanos_memories
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = cur.fetchone()
                retrieval_time = time.time() - start_time

                warnings = []
                severity = None

                # Performance checks
                if query_time > 1.0:
                    warnings.append(f"Slow query performance ({query_time:.2f}s) - database may need optimization")
                    severity = "warning"

                if retrieval_time > 2.0:
                    warnings.append(f"Slow memory retrieval ({retrieval_time:.2f}s) - check database connection")
                    severity = "warning" if severity != "critical" else severity

                # Connection check
                if not result and query_time < 1.0:
                    # Database is responsive but empty (this is OK for new systems)
                    warnings.append("Database is empty - this is normal for new installations")
                    severity = "info"

                return {
                    "query_time": round(query_time, 3),
                    "retrieval_time": round(retrieval_time, 3),
                    "warnings": warnings,
                    "severity": severity,
                    "operational": True
                }

    except psycopg2.OperationalError as e:
        return {
            "query_time": None,
            "retrieval_time": None,
            "warnings": [f"Database connection failed: {str(e)}"],
            "severity": "critical",
            "operational": False
        }
    except Exception as e:
        return {
            "query_time": None,
            "retrieval_time": None,
            "warnings": [f"Retrieval test failed: {str(e)}"],
            "severity": "error",
            "operational": False
        }


def format_memory_health_summary(
    stats: Dict[str, Any],
    storage: Dict[str, Any],
    backup: Dict[str, Any],
    retrieval: Dict[str, Any]
) -> str:
    """
    Format memory health data into a readable summary.

    Args:
        stats: Memory statistics
        storage: Storage metrics
        backup: Backup status
        retrieval: Retrieval health check results

    Returns:
        Formatted summary string
    """
    mobile = is_mobile()
    output = []

    # Header
    today = datetime.now().strftime("%A, %B %d, %Y")
    if mobile:
        output.append("━━━ MEMORY HEALTH ━━━")
        output.append(today)
        output.append("━" * 20)
    else:
        output.append("# Memory System Health Dashboard")
        output.append(f"*{today}*")
        output.append("")

    # Check for errors
    if "error" in stats:
        output.append(f"\n⚠️ Error: {stats['error']}")
        return "\n".join(output)

    # Overview Section
    output.append(format_header("Overview"))

    total = stats['total_memories']
    avg_heat = stats['avg_heat']
    pinned = stats['pinned_count']

    if mobile:
        output.append(f"Total Memories: {total:,}")
        output.append(f"Average Heat: {avg_heat:.3f}")
        output.append(f"Pinned: {pinned}")
    else:
        overview_items = [
            f"**Total Memories:** {total:,}",
            f"**Average Heat Score:** {avg_heat:.3f}",
            f"**Pinned Memories:** {pinned} (never decay)"
        ]
        output.append(format_list(overview_items))

    # Heat Distribution Section
    output.append("\n" + format_header("Heat Distribution"))

    hot_count = stats['hot_count']
    warm_count = stats['warm_count']
    cold_count = stats['cold_count']
    hot_pct = stats['hot_pct']
    warm_pct = stats['warm_pct']
    cold_pct = stats['cold_pct']

    if mobile:
        output.append(f"🔥 Hot (≥0.7): {hot_count} ({hot_pct}%)")
        output.append(f"🌡️  Warm (0.3-0.7): {warm_count} ({warm_pct}%)")
        output.append(f"❄️  Cold (<0.3): {cold_count} ({cold_pct}%)")
    else:
        heat_items = [
            f"🔥 **Hot** (heat ≥ 0.7): {hot_count:,} memories ({hot_pct}%)",
            f"🌡️  **Warm** (heat 0.3-0.7): {warm_count:,} memories ({warm_pct}%)",
            f"❄️  **Cold** (heat < 0.3): {cold_count:,} memories ({cold_pct}%)"
        ]
        output.append(format_list(heat_items))

    # Heat distribution health check
    if cold_pct > 50:
        output.append("\n⚠️ High percentage of cold memories - consider reviewing neglected items")
    elif hot_pct > 60:
        output.append("\n✅ Strong memory engagement - lots of active recall")

    # Storage Section
    output.append("\n" + format_header("Storage"))

    if "error" in storage:
        output.append(f"⚠️ {storage['error']}")
    else:
        size_mb = storage['size_mb']
        table_size = storage['table_size']

        if mobile:
            output.append(f"Size: {table_size}")
            output.append(f"({size_mb} MB)")
        else:
            storage_items = [
                f"**Database Size:** {table_size}",
                f"**Approximate Size:** {size_mb} MB"
            ]
            output.append(format_list(storage_items))

        # Storage health check
        if size_mb > 1000:
            output.append("\n⚠️ Database size exceeding 1GB - consider archiving old memories")
        else:
            output.append("\n✅ Storage utilization healthy")

    # Backup Status Section
    output.append("\n" + format_header("Backup Status"))

    backup_severity = backup.get("severity")
    backup_warning = backup.get("warning")

    if backup.get("last_backup"):
        last_backup = backup['last_backup']
        age_days = backup['age_days']
        backup_file = backup.get('backup_file', 'unknown')

        if mobile:
            output.append(f"Last: {last_backup.strftime('%Y-%m-%d %H:%M')}")
            output.append(f"Age: {age_days} days")
        else:
            backup_items = [
                f"**Last Backup:** {last_backup.strftime('%B %d, %Y at %I:%M %p')}",
                f"**Backup Age:** {age_days} days ago",
                f"**File:** {backup_file}"
            ]
            output.append(format_list(backup_items))

        # Display warning with appropriate emoji based on severity
        if backup_warning:
            if backup_severity == "critical":
                output.append(f"\n🔴 CRITICAL: {backup_warning}")
            elif backup_severity == "warning":
                output.append(f"\n⚠️ Warning: {backup_warning}")
            elif backup_severity == "info":
                output.append(f"\n💡 Note: {backup_warning}")
        else:
            output.append("\n✅ Backup is recent and healthy")
    else:
        # No backup found
        if backup_warning:
            if backup_severity == "critical":
                output.append(f"🔴 CRITICAL: {backup_warning}")
            else:
                output.append(f"⚠️ {backup_warning}")
        else:
            output.append("⚠️ No recent backups found")

    # Retrieval Health Section
    output.append("\n" + format_header("Retrieval Health"))

    retrieval_operational = retrieval.get("operational", False)
    retrieval_warnings = retrieval.get("warnings", [])
    retrieval_severity = retrieval.get("severity")
    query_time = retrieval.get("query_time")
    retrieval_time = retrieval.get("retrieval_time")

    if retrieval_operational:
        if mobile:
            if query_time is not None:
                output.append(f"Query time: {query_time:.3f}s")
            if retrieval_time is not None:
                output.append(f"Retrieval time: {retrieval_time:.3f}s")
        else:
            perf_items = []
            if query_time is not None:
                perf_items.append(f"**Query Performance:** {query_time:.3f}s")
            if retrieval_time is not None:
                perf_items.append(f"**Retrieval Performance:** {retrieval_time:.3f}s")
            if perf_items:
                output.append(format_list(perf_items))

        # Display retrieval warnings
        if retrieval_warnings:
            output.append("")
            for warning in retrieval_warnings:
                if retrieval_severity == "critical":
                    output.append(f"🔴 CRITICAL: {warning}")
                elif retrieval_severity == "warning":
                    output.append(f"⚠️ {warning}")
                elif retrieval_severity == "info":
                    output.append(f"💡 {warning}")
        else:
            output.append("\n✅ Retrieval performance is healthy")
    else:
        # Retrieval failed
        output.append("🔴 CRITICAL: Memory retrieval system is not operational")
        if retrieval_warnings:
            for warning in retrieval_warnings:
                output.append(f"  - {warning}")

    # System Health Section
    output.append("\n" + format_header("System Health"))

    health_checks = []

    # Overall health indicator
    if total > 0:
        health_checks.append("✅ Memory system is operational")
    else:
        health_checks.append("⚠️ No memories stored yet")

    # Heat system health
    if avg_heat > 0:
        health_checks.append(f"✅ Heat decay system active (avg: {avg_heat:.3f})")
    else:
        health_checks.append("⚠️ Heat system may need initialization")

    # Pinned memories
    if pinned > 0:
        health_checks.append(f"✅ {pinned} critical memories pinned")

    # Database connectivity (from retrieval check)
    if retrieval_operational:
        health_checks.append("✅ Database connection healthy")
    else:
        health_checks.append("🔴 Database connection issues detected")

    output.append(format_list(health_checks))

    # Footer
    if mobile:
        output.append("\n━" * 20)
    else:
        output.append("")

    return "\n".join(output)


def save_to_history(summary: str):
    """Save the memory health summary to History."""
    project_root = Path(__file__).parent.parent.parent
    history_dir = project_root / "History" / "MemoryHealth"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"memory_health_{timestamp.strftime('%Y-%m-%d_%H%M%S')}.md"

    with open(history_dir / filename, "w") as f:
        f.write(f"# Memory Health Dashboard\n\n")
        f.write(f"*Generated at {timestamp.strftime('%B %d, %Y - %I:%M %p')}*\n\n")
        f.write(summary)


@contextmanager
def _get_connection():
    """Get database connection with context manager."""
    if not NEON_DATABASE_URL:
        raise ValueError("THANOS_MEMORY_DATABASE_URL not configured")

    conn = psycopg2.connect(NEON_DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute() -> str:
    """
    Generate memory health dashboard.

    Returns:
        The generated health summary
    """
    today = datetime.now().strftime("%A, %B %d, %Y")
    print(f"🧠 Generating memory health dashboard for {today}...\n")

    # Fetch all metrics
    print("📊 Fetching memory statistics...")
    stats = fetch_memory_stats()

    print("💾 Checking storage utilization...")
    storage = fetch_storage_metrics()

    print("📦 Checking backup status...")
    backup = fetch_backup_status()

    print("🔍 Testing memory retrieval...")
    retrieval = check_retrieval_health()

    # Format the summary
    summary = format_memory_health_summary(stats, storage, backup, retrieval)

    print("-" * 50)
    print(summary)
    print("-" * 50)

    # Save to history
    save_to_history(summary)
    print("\n✅ Saved to History/MemoryHealth/")

    return summary


def main():
    """CLI entry point."""
    try:
        execute()
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
