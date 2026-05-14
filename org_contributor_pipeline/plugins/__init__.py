"""Pluggable dimension runners."""

from .base import PipelineContext, PipelinePlugin
from .commit_title_signals import run_commit_title_signals_on_events
from .delivery_traceability import DeliveryTraceabilityPlugin
from .identity_footprint import run_identity_footprint_on_events
from .path_taxonomy import run_path_taxonomy_on_events

__all__ = [
    "PipelineContext",
    "PipelinePlugin",
    "DeliveryTraceabilityPlugin",
    "run_commit_title_signals_on_events",
    "run_identity_footprint_on_events",
    "run_path_taxonomy_on_events",
]