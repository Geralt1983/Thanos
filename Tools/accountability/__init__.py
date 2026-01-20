#!/usr/bin/env python3
"""
Accountability Architecture for Thanos.

This module provides brain dump processing, impact scoring,
work prioritization, and daily planning enforcement.

Components:
- processor: Brain dump classification and routing
- impact_scorer: Personal task impact scoring
- work_prioritizer: Work task prioritization
- planning_enforcer: Daily planning with consequences
- models: Data models and enums
"""

from .models import (
    BrainDumpCategory,
    TaskDomain,
    ImpactDimension,
    ImpactScore,
    WorkPriorityMode,
    PlanningStatus,
    ClassifiedBrainDump,
    ClientWorkload,
    PlanningRecord,
    AccountabilityMetrics,
)

from .processor import (
    BrainDumpProcessor,
    BrainDumpRouter,
    process_brain_dump,
)

from .impact_scorer import (
    ImpactScorer,
    score_task,
)

from .work_prioritizer import (
    WorkPrioritizer,
    get_prioritized_clients,
)

from .planning_enforcer import (
    PlanningEnforcer,
    PlanningAlertChecker,
)

__all__ = [
    # Models
    'BrainDumpCategory',
    'TaskDomain',
    'ImpactDimension',
    'ImpactScore',
    'WorkPriorityMode',
    'PlanningStatus',
    'ClassifiedBrainDump',
    'ClientWorkload',
    'PlanningRecord',
    'AccountabilityMetrics',

    # Processor
    'BrainDumpProcessor',
    'BrainDumpRouter',
    'process_brain_dump',

    # Impact Scorer
    'ImpactScorer',
    'score_task',

    # Work Prioritizer
    'WorkPrioritizer',
    'get_prioritized_clients',

    # Planning Enforcer
    'PlanningEnforcer',
    'PlanningAlertChecker',
]
