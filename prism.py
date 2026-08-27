#!/usr/bin/env python3
"""
PRISM — Platform Recognition & Input Session Miner
====================================================
Dies ist ein Deprecated-Wrapper. Verwende stattdessen:

    python -m parse_user_inputs --help

Oder importiere direkt:

    from parse_user_inputs.config import Config
    from parse_user_inputs.sources import scan_all_threads
"""

import sys
import warnings

warnings.warn(
    "prism.py ist veraltet. Verwende: python -m parse_user_inputs",
    DeprecationWarning,
    stacklevel=1,
)

from parse_user_inputs.cli import main

if __name__ == "__main__":
    main()
