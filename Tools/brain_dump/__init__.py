#!/usr/bin/env python3
"""
Brain Dump Processing Module for Thanos.

Provides classification, routing, and storage of brain dump entries.
Supports categorizing thoughts into tasks, ideas, notes, commitments,
or reflective entries (thinking, venting, observations).

Usage:
    from Tools.brain_dump import BrainDumpClassifier, ClassifiedBrainDump

    classifier = BrainDumpClassifier()
    result = await classifier.classify("Need to call the dentist")
"""

# Import classifier (always available)
from .classifier import (
    BrainDumpClassifier,
    ClassifiedBrainDump,
    classify_brain_dump,
    classify_brain_dump_sync,
)

__all__ = [
    # Classifier
    "BrainDumpClassifier",
    "ClassifiedBrainDump",
    "classify_brain_dump",
    "classify_brain_dump_sync",
]

# Import router
from .router import (
    BrainDumpRouter,
    RoutingResult,
    ClassifiedSegment,
    Classification,
    route_brain_dump,
)

__all__.extend([
    # Router
    "BrainDumpRouter",
    "RoutingResult",
    "ClassifiedSegment",
    "Classification",
    "route_brain_dump",
])
