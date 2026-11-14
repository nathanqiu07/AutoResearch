"""Stable method IDs from PLAN.md. Unimplemented methods fail explicitly."""


def create_method(method, llm, **kwargs):
    from .m0_none import NoHistory
    from .m1_history import RawHistory
    registry = {"m0": NoHistory, "m1": RawHistory}
    if method not in registry:
        raise ValueError("method %r is not implemented; available: %s" % (method, sorted(registry)))
    return registry[method](llm, **kwargs)
