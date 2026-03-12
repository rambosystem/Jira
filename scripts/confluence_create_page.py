#!/usr/bin/env python3
"""Compatibility entrypoint for scripts/confluence/confluence_create_page.py."""
from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parent / "confluence" / "confluence_create_page.py"
runpy.run_path(str(TARGET), run_name="__main__")
