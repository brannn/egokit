"""Pluggable detector framework for policy enforcement."""

from .base import DetectorBase, DetectorProtocol
from .loader import DetectorLoader

__all__ = ["DetectorBase", "DetectorProtocol", "DetectorLoader"]