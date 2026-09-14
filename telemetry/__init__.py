"""
/telemetry/__init__.py

This becomes the application's telemetry interface.
"""

from telemetry.opik_adapter import (
    configure_telemetry,
    is_enabled,
    is_available,
    track,
    update_current_trace,
    update_current_span,
    get_litellm_metadata,
    configure_litellm,
)