import os
from typing import Any, Callable

from config import config

_opik_logger = None
_telemetry_available = False


def is_enabled() -> bool:
    return config.telemetry.enable_opik

def is_available() -> bool:
    return is_enabled() and _telemetry_available

def configure_telemetry() -> None:
    """
    Configure Opik only when telemetry is enabled.

    This function is intentionally the only place where Opik SDK
    configuration happens.

    Telemetry initialization must never prevent the application 
    from running.
    """
    global _telemetry_available

    if not is_enabled():
        return

    try:
        import opik

        opik.configure(
            api_key=os.getenv("OPIK_API_KEY"),
            workspace=os.getenv("OPIK_WORKSPACE"),
            force=False,
            automatic_approvals=True,
        )

        _telemetry_available = True

    except Exception as exc:
        _telemetry_available = False

        print(
            f"⚠️ [Telemetry] Opik configuration failed: {exc}. "
            "Continuing without Opik telemetry."
        )


def configure_litellm() -> None:
    """
    Register the Opik LiteLLM callback only when Opik is enabled.
    """
    global _opik_logger

    if not is_available():
        return

    import litellm
    from litellm.integrations.opik.opik import OpikLogger

    if _opik_logger is None:
        _opik_logger = OpikLogger()

    if litellm.callbacks is None:
        litellm.callbacks = []

    if _opik_logger not in litellm.callbacks:
        litellm.callbacks.append(_opik_logger)


def track(*args, **kwargs):
    """
    Backend-neutral tracking decorator.

    When Opik is disabled or unavailable, this becomes a no-op 
    decorator so telemetry failures cannot prevent application startup.
    """

    if not is_enabled():
        def no_op_decorator(func: Callable) -> Callable:
            return func

        return no_op_decorator

    try:
        import opik

        kwargs.setdefault(
            "project_name",
            config.telemetry.project_name,
        )

        return opik.track(*args, **kwargs)
    except Exception as exc:
        print(
            f"⚠️ [Telemetry] Failed to create Opik tracking decorator: "
            f"{exc}. Continuing without this telemetry span."
        )

        def no_op_decorator(func: Callable) -> Callable:
            return func

        return no_op_decorator


def update_current_trace(metadata: dict[str, Any] | None = None) -> None:
    """
    Update the current telemetry trace when telemetry is enabled.
    """
    if not is_available():
        print("⚠️ [Telemetry] update_current_trace skipped: telemetry unavailable.")
        return

    from opik import opik_context

    trace_metadata = {
        "experiment_id": config.experiment.experiment_id,
        "phase": config.telemetry.current_phase,
    }

    if metadata:
        trace_metadata.update(metadata)

    opik_context.update_current_trace(
        metadata=trace_metadata
    )

def update_current_span(metadata: dict[str, Any] | None = None) -> None:
    """
    Update the currently active Opik span when telemetry is available.

    Use this for metadata specific to the currently tracked operation.
    """
    if not is_available():
        print("⚠️ [Telemetry] update_current_span skipped: telemetry unavailable.")
        return

    from opik import opik_context

    span_metadata = {
        "experiment_id": config.experiment.experiment_id,
        "phase": config.telemetry.current_phase,
    }

    if metadata:
        span_metadata.update(metadata)

    opik_context.update_current_span(
        metadata=span_metadata
    ) 

def get_litellm_metadata() -> dict[str, Any]:
    """
    Return metadata required to connect a LiteLLM call to the
    current Opik span.

    Returns an empty dictionary when telemetry is disabled.
    """
    if not is_available():
        return {}

    from opik.opik_context import get_current_span_data

    return {
        "metadata": {
            "opik": {
                "current_span_data": get_current_span_data()
            }
        }
    }