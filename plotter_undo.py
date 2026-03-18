"""plotter_undo.py — Command-pattern undo/redo system for Claude Plotter."""

import time
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Command:
    description: str
    var_key: str
    old_value: Any
    new_value: Any
    timestamp: float = field(default_factory=time.time)

    def apply(self, app_vars: dict) -> None:
        """Apply command (set new_value)."""
        var = app_vars.get(self.var_key)
        if var is not None and hasattr(var, "set"):
            var.set(self.new_value)

    def reverse(self, app_vars: dict) -> None:
        """Reverse command (restore old_value)."""
        var = app_vars.get(self.var_key)
        if var is not None and hasattr(var, "set"):
            var.set(self.old_value)


@dataclass
class CompoundCommand:
    description: str
    commands: List[Command] = field(default_factory=list)

    def apply(self, app_vars: dict) -> None:
        """Apply all sub-commands in order."""
        for cmd in self.commands:
            cmd.apply(app_vars)

    def reverse(self, app_vars: dict) -> None:
        """Reverse all sub-commands in reverse order."""
        for cmd in reversed(self.commands):
            cmd.reverse(app_vars)


class UndoStack:
    """Undo/redo stack with configurable max depth."""

    def __init__(self, max_depth: int = 50):
        self._max_depth = max_depth
        self._undo: List = []
        self._redo: List = []
        self._suppressed: bool = False
        self._recording: bool = False
        self._compound_desc: str = ""
        self._compound_acc: List[Command] = []

    def record(self, cmd) -> None:
        """Add command to undo stack. Ignored when suppressed or in compound mode."""
        if self._suppressed:
            return
        if self._recording:
            if isinstance(cmd, Command):
                self._compound_acc.append(cmd)
            return
        self._undo.append(cmd)
        if len(self._undo) > self._max_depth:
            self._undo.pop(0)
        self._redo.clear()

    def begin_compound(self, description: str) -> None:
        """Start accumulating commands into a single compound command."""
        self._recording = True
        self._compound_desc = description
        self._compound_acc = []

    def end_compound(self) -> None:
        """Push accumulated commands as one CompoundCommand."""
        self._recording = False
        if self._compound_acc:
            compound = CompoundCommand(
                description=self._compound_desc,
                commands=list(self._compound_acc),
            )
            self._undo.append(compound)
            if len(self._undo) > self._max_depth:
                self._undo.pop(0)
            self._redo.clear()
        self._compound_acc = []
        self._compound_desc = ""

    def undo(self, app_vars: dict) -> Optional[str]:
        """Pop from undo, reverse, push to redo. Returns description or None."""
        if not self._undo:
            return None
        cmd = self._undo.pop()
        self._suppressed = True
        try:
            cmd.reverse(app_vars)
        finally:
            self._suppressed = False
        self._redo.append(cmd)
        return cmd.description

    def redo(self, app_vars: dict) -> Optional[str]:
        """Pop from redo, apply, push to undo. Returns description or None."""
        if not self._redo:
            return None
        cmd = self._redo.pop()
        self._suppressed = True
        try:
            cmd.apply(app_vars)
        finally:
            self._suppressed = False
        self._undo.append(cmd)
        return cmd.description

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_description(self) -> Optional[str]:
        return self._undo[-1].description if self._undo else None

    @property
    def redo_description(self) -> Optional[str]:
        return self._redo[-1].description if self._redo else None
