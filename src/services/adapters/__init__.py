"""
Service Adapters for Unified Variant Registry

Provides adapter pattern implementation for service-specific request building
and response handling. Each service (Text, Illustrator, Analytics) has a
dedicated adapter that implements the common interface defined in BaseServiceAdapter.

Version: 2.0.0
Created: 2025-11-29
"""

from .base_adapter import BaseServiceAdapter
from .text_service_adapter import TextServiceAdapter
from .illustrator_service_adapter import IllustratorServiceAdapter
from .analytics_service_adapter import AnalyticsServiceAdapter

__all__ = [
    "BaseServiceAdapter",
    "TextServiceAdapter",
    "IllustratorServiceAdapter",
    "AnalyticsServiceAdapter",
]
