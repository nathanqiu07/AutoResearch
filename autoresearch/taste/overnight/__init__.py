"""Neutral, version-pinned researcher profiles; existing UserModel stays unchanged."""

from .contracts import ProfileArtifact, build_profile
from .consumer import ProfileFailure, predict_profile

__all__ = ["ProfileArtifact", "ProfileFailure", "build_profile", "predict_profile"]
