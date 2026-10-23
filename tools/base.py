"""
NEO AI - Tool Specifications & Result Contracts
Defines standardized contracts for tools, parameter schemas, permissions,
and structured execution results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple


class ToolPermission(str, Enum):
    """Classification of tool action safety levels."""
    READ_ONLY = "read_only"       # Telemetry, search, file listing (no disk/system mutations)
    REVERSIBLE = "reversible"     # Opening apps, navigating web, typing, screenshots
    DESTRUCTIVE = "destructive"   # File deletion, process termination, system reboot/shutdown


@dataclass
class ToolResult:
    """Standardized result returned by any tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    data: Any = None
    permission: ToolPermission = ToolPermission.REVERSIBLE

    def __str__(self) -> str:
        if self.success:
            return self.output
        return self.error or self.output

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "data": self.data,
            "permission": self.permission.value
        }


@dataclass
class ToolSpec:
    """Metadata specification and validator for registered PC automation tools."""
    name: str
    description: str
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    permission: ToolPermission = ToolPermission.REVERSIBLE
    timeout: float = 15.0

    def validate_arguments(self, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates that required parameters are provided and typed appropriately."""
        if not isinstance(arguments, dict):
            return False, f"Expected arguments dictionary, got {type(arguments).__name__}"

        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})

        for req in required:
            if req not in arguments:
                return False, f"Missing required parameter '{req}' for tool '{self.name}'"

        for key, val in arguments.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "string" and not isinstance(val, str):
                    return False, f"Parameter '{key}' must be a string."
                elif expected_type == "integer" and not isinstance(val, int):
                    try:
                        int(val)
                    except (ValueError, TypeError):
                        return False, f"Parameter '{key}' must be an integer."
                elif expected_type == "number" and not isinstance(val, (int, float)):
                    try:
                        float(val)
                    except (ValueError, TypeError):
                        return False, f"Parameter '{key}' must be a number."
                elif expected_type == "boolean" and not isinstance(val, bool):
                    if str(val).lower() not in {"true", "false", "1", "0"}:
                        return False, f"Parameter '{key}' must be a boolean."

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """Executes the wrapped tool function and returns a structured ToolResult."""
        valid, err_msg = self.validate_arguments(kwargs)
        if not valid:
            return ToolResult(
                success=False,
                output="",
                error=err_msg or "Invalid arguments.",
                permission=self.permission
            )

        try:
            raw = self.function(**kwargs)
            if isinstance(raw, ToolResult):
                return raw
            if isinstance(raw, tuple) and len(raw) == 2 and isinstance(raw[0], bool):
                return ToolResult(
                    success=raw[0],
                    output=str(raw[1]) if raw[0] else "",
                    error=str(raw[1]) if not raw[0] else None,
                    permission=self.permission
                )
            # Normal string return
            return ToolResult(
                success=True,
                output=str(raw),
                permission=self.permission
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution error in {self.name}: {exc}",
                permission=self.permission
            )
