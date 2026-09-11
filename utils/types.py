"""Standard response and data schemas for financial analyst agent and tools."""

from typing import Optional, Any
from pydantic import BaseModel, Field


class ToolResponse(BaseModel):
    """Standard response model for MCP tools."""
    success: bool = Field(..., description="Whether the operation succeeded.")
    message: str = Field(..., description="Human-readable summary or status message.")
    data: Optional[Any] = Field(None, description="Payload data (e.g. file paths, analysis summary).")
    error: Optional[str] = Field(None, description="Detailed error message if unsuccessful.")

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)


class ExecutionResult(BaseModel):
    """Result of executing an analysis Python script in a sandboxed subprocess."""
    success: bool = Field(..., description="Whether the script exited with return code 0.")
    script_path: str = Field(..., description="Path to the executed script.")
    chart_path: Optional[str] = Field(None, description="Path to the generated chart image, if any.")
    stdout: str = Field(default="", description="Captured standard output.")
    stderr: str = Field(default="", description="Captured standard error.")
    returncode: int = Field(default=0, description="Process exit code.")
    execution_time_seconds: float = Field(default=0.0, description="Runtime duration in seconds.")
    error: Optional[str] = Field(None, description="Execution error message (e.g. timeout, syntax, runtime).")

