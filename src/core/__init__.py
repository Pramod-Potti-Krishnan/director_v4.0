"""
Core Module for Director Agent v4.0

Contains core business logic components for multi-service coordination.

v4.9: Added presentation type analyzer and I-series budget tracker
for audience-aware I-series allocation.
"""

from .content_analyzer import ContentAnalyzer
from .layout_analyzer import LayoutAnalyzer, LayoutAnalysisResult, LayoutSeriesMode
from .presentation_type_analyzer import (
    PresentationType,
    classify_presentation,
    get_target_range,
    get_preferred_image_positions,
    get_iseries_strategy
)
from .iseries_budget_tracker import ISeriesBudgetTracker

__all__ = [
    # Content Analysis
    'ContentAnalyzer',

    # Layout Analysis
    'LayoutAnalyzer',
    'LayoutAnalysisResult',
    'LayoutSeriesMode',

    # v4.9: I-Series Budget Tracking
    'PresentationType',
    'classify_presentation',
    'get_target_range',
    'get_preferred_image_positions',
    'get_iseries_strategy',
    'ISeriesBudgetTracker',
]
