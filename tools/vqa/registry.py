"""Check registry for VQA stages."""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Issue:
    check: str
    where: str
    msg: str
    fix_hint: str
    level: str = "error"  # "error" | "warning"

    def to_dict(self) -> Dict[str, str]:
        return {
            "check": self.check,
            "where": self.where,
            "msg": self.msg,
            "fix_hint": self.fix_hint,
        }


@dataclass
class CheckDef:
    name: str
    stage: str
    func: Callable[[Any], List[Issue]]


_REGISTRY: Dict[str, List[CheckDef]] = {
    "brief": [],
    "shots": [],
    "build": [],
    "render": [],
}


def register_check(stage: str, name: str):
    """Decorator to register a QA check function."""
    if stage not in _REGISTRY:
        raise ValueError(f"Unknown QA stage {stage!r}. Valid: {list(_REGISTRY.keys())}")

    def decorator(fn: Callable[[Any], List[Issue]]):
        _REGISTRY[stage].append(CheckDef(name=name, stage=stage, func=fn))
        return fn

    return decorator


def get_checks(stage: str) -> List[CheckDef]:
    """Retrieve all checks registered for a given stage."""
    _ensure_loaded()
    if stage not in _REGISTRY:
        raise ValueError(f"Unknown QA stage {stage!r}. Valid: {list(_REGISTRY.keys())}")
    return _REGISTRY[stage]


_LOADED = False


def _ensure_loaded():
    """Dynamically import all check modules in tools/vqa/checks/."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    try:
        import tools.vqa.checks as checks_pkg
        for _, stage_name, is_pkg in pkgutil.iter_modules(checks_pkg.__path__):
            if is_pkg:
                stage_mod = importlib.import_module(f"tools.vqa.checks.{stage_name}")
                for _, check_name, _ in pkgutil.iter_modules(stage_mod.__path__):
                    importlib.import_module(f"tools.vqa.checks.{stage_name}.{check_name}")
    except Exception as exc:
        # If running standalone or from tests
        pass
