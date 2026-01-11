#!/bin/bash
# Smart Swarm Configuration Hook
# Analyzes task context and outputs swarm configuration for MCP tools
# Fast execution - no external CLI calls

set -euo pipefail

# Detect project root - handle being inside a worktree
if [[ "$PWD" == *".auto-claude/worktrees/tasks/"* ]]; then
    PROJECT_ROOT="${PWD%%/.auto-claude/*}"
else
    PROJECT_ROOT="${PWD:-/Users/jeremy/Projects/Thanos}"
fi
AUTO_CLAUDE_DIR="${PROJECT_ROOT}/.auto-claude"
SWARM_STATE_FILE="${HOME}/.claude-flow-swarm-state.json"

# Analyze task complexity from AutoClaude metadata
analyze_task() {
    local complexity="simple"
    local priority="medium"
    local category=""

    # Check for active AutoClaude worktrees
    if [ -d "$AUTO_CLAUDE_DIR/worktrees/tasks" ]; then
        local worktree_count=$(find "$AUTO_CLAUDE_DIR/worktrees/tasks" -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
        if [ "$worktree_count" -gt 3 ]; then
            complexity="enterprise"
        fi
    fi

    # Check current task spec if in a worktree
    if [[ "$PWD" == *".auto-claude/worktrees/tasks/"* ]]; then
        local task_name=$(echo "$PWD" | sed 's|.*\.auto-claude/worktrees/tasks/\([^/]*\).*|\1|')
        local task_metadata="${PROJECT_ROOT}/.auto-claude/specs/${task_name}/task_metadata.json"
        if [ -f "$task_metadata" ]; then
            priority=$(jq -r '.priority // "medium"' "$task_metadata" 2>/dev/null || echo "medium")
            category=$(jq -r '.category // ""' "$task_metadata" 2>/dev/null || echo "")

            case "$category" in
                "refactoring"|"code_quality"|"architecture") complexity="complex" ;;
                "security"|"performance") complexity="critical" ;;
                "documentation"|"testing") complexity="moderate" ;;
            esac
        fi
    fi

    echo "$complexity|$priority|$category"
}

# Select optimal swarm configuration
select_config() {
    local analysis="$1"
    local complexity=$(echo "$analysis" | cut -d'|' -f1)
    local priority=$(echo "$analysis" | cut -d'|' -f2)
    local category=$(echo "$analysis" | cut -d'|' -f3)

    local topology="hierarchical"
    local max_agents=4
    local strategy="balanced"
    local use_hive_mind="false"
    local queen_type=""

    case "$complexity" in
        "simple") topology="star"; max_agents=3 ;;
        "moderate") topology="hierarchical"; max_agents=5 ;;
        "complex") topology="mesh"; max_agents=8; strategy="specialized" ;;
        "critical") use_hive_mind="true"; queen_type="tactical"; max_agents=10; strategy="adaptive" ;;
        "enterprise") use_hive_mind="true"; queen_type="strategic"; max_agents=12; strategy="adaptive" ;;
    esac

    # Adjust for high priority
    if [ "$priority" = "high" ] || [ "$priority" = "critical" ]; then
        max_agents=$((max_agents + 2))
        [ "$use_hive_mind" = "false" ] && [ "$complexity" != "simple" ] && topology="mesh" && strategy="adaptive"
    fi

    # Category-specific adjustments
    case "$category" in
        "security") use_hive_mind="true"; queen_type="adaptive" ;;
        "testing") topology="ring" ;;
    esac

    echo "$use_hive_mind|$topology|$max_agents|$strategy|$queen_type|$category"
}

# Main
main() {
    ANALYSIS=$(analyze_task)
    CONFIG=$(select_config "$ANALYSIS")

    USE_HIVE_MIND=$(echo "$CONFIG" | cut -d'|' -f1)
    TOPOLOGY=$(echo "$CONFIG" | cut -d'|' -f2)
    MAX_AGENTS=$(echo "$CONFIG" | cut -d'|' -f3)
    STRATEGY=$(echo "$CONFIG" | cut -d'|' -f4)
    QUEEN_TYPE=$(echo "$CONFIG" | cut -d'|' -f5)
    CATEGORY=$(echo "$CONFIG" | cut -d'|' -f6)

    # Write initial state (not yet initialized)
    cat > "$SWARM_STATE_FILE" << EOF
{
    "useHiveMind": $USE_HIVE_MIND,
    "topology": "$TOPOLOGY",
    "maxAgents": $MAX_AGENTS,
    "strategy": "$STRATEGY",
    "queenType": "$QUEEN_TYPE",
    "category": "$CATEGORY",
    "analysis": "$ANALYSIS",
    "startedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "workingDir": "$PWD",
    "initialized": false,
    "autoInitPending": true
}
EOF

    # Output swarm configuration for Claude to auto-initialize via MCP
    echo ""
    echo "SessionStart:smart-swarm hook success: Success"
    echo ""
    echo "🚀 SWARM AUTO-INIT REQUIRED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Configuration detected:"
    echo "  Topology: $TOPOLOGY"
    echo "  Max Agents: $MAX_AGENTS"
    echo "  Strategy: $STRATEGY"
    if [ "$USE_HIVE_MIND" = "true" ]; then
        echo "  Mode: HIVE-MIND (Queen: $QUEEN_TYPE)"
    fi
    [ -n "$CATEGORY" ] && echo "  Category: $CATEGORY"
    echo ""
    echo "INSTRUCTION: Initialize swarm NOW using MCP tool:"
    echo "  mcp__claude-flow__swarm_init(topology: \"$TOPOLOGY\", maxAgents: $MAX_AGENTS, strategy: \"$STRATEGY\")"
    echo ""
    echo "After init, spawn coordinator:"
    echo "  mcp__claude-flow__agent_spawn(type: \"coordinator\", name: \"task-router\")"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

main
