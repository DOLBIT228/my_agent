"""Safe-ish Python execution tool for quick calculations."""
from __future__ import annotations

from io import StringIO
import contextlib


class PythonExecTool:
    def run(self, code: str) -> str:
        safe_globals = {"__builtins__": {"print": print, "len": len, "sum": sum, "min": min, "max": max, "range": range}}
        output = StringIO()
        with contextlib.redirect_stdout(output):
            exec(code, safe_globals, {})  # noqa: S102
        return output.getvalue().strip() or "Executed successfully."
