"""
main.py — Main Entry Point for Aero Suite
Automotive APK & System Studio — Dongfeng Shine Edition
"""
import os
import sys

# Ensure src directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from app_gui import AeroSuiteApp

if __name__ == "__main__":
    app = AeroSuiteApp()
    app.mainloop()
