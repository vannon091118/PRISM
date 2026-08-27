"""
parse_user_inputs.modes
========================
CLI-Modi als separate Module:
  - thread_mode: --threads / --scan-all (Thread-Dashboard)
  - scan_mode: --scan-all ohne --threads (Input-Dashboard)
  - project_mode: Einzelnes Projekt scannen
"""

from parse_user_inputs.modes.thread_mode import run_threads_mode
from parse_user_inputs.modes.scan_mode import run_scan_mode
from parse_user_inputs.modes.project_mode import run_project_mode

__all__ = ["run_threads_mode", "run_scan_mode", "run_project_mode"]
