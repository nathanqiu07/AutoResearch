"""Stable method IDs from PLAN.md. Unimplemented methods fail explicitly."""


def create_method(method, llm, **kwargs):
    from .m0_none import NoHistory
    from .m1_history import RawHistory
    from .m2_synthesizeme import SynthesizeMe
    from .m3_icai import InverseConstitutional
    from .m4_bt import BradleyTerry
    from .m5_hybrid import Hybrid
    from .m6_verified import VerifiedHybrid
    from .m7_confident import ConfidentHybrid
    registry = {"m0": NoHistory, "m1": RawHistory, "m2": SynthesizeMe,
                "m3": InverseConstitutional, "m4": BradleyTerry, "m5": Hybrid,
                "m6": VerifiedHybrid, "m7": ConfidentHybrid}
    if method not in registry:
        raise ValueError("method %r is not implemented; available: %s" % (method, sorted(registry)))
    return registry[method](llm, **kwargs)
