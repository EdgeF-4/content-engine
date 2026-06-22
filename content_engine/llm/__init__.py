"""Provider agnostic LLM access for the planner and QC stages."""
from .router import completer_for_role, extract_json

__all__ = ["completer_for_role", "extract_json"]
