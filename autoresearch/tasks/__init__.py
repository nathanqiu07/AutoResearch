from .base import Task, Result, Invariant, EnvironmentDesignTask
from .eval_awareness import EvalAwarenessTask
from .stretch import AgenticHoneypotTask, UserSimulatorTask

TASKS = {t.name: t for t in (EvalAwarenessTask, AgenticHoneypotTask, UserSimulatorTask)}


def get_task(name: str) -> Task:
    if name not in TASKS:
        raise KeyError(f"unknown task {name!r}; choose from {sorted(TASKS)}")
    return TASKS[name]()
