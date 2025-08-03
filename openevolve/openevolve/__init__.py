"""
OpenEvolve: An open-source implementation of AlphaEvolve
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from openevolve._version import __version__
from openevolve.controller import OpenEvolve

__all__ = ["OpenEvolve", "__version__"]
