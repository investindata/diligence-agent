#!/usr/bin/env python3
"""
Launch script for Investment Report Viewer

Usage:
    python launch_report_viewer.py
    
Features:
- View completed executive summary reports
- Automatic scanning of output/session_* directories
- Shows latest report for each company
- Clean markdown rendering
"""

import sys
import os

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from diligence_agent.report_viewer import launch_report_viewer

if __name__ == "__main__":
    print("📊 Launching Investment Report Viewer...")
    print("📍 The UI will be available at: http://localhost:7861")
    print("📋 Features:")
    print("   • View completed executive summary reports")
    print("   • Automatic scanning of output directories")
    print("   • Shows latest report for each company")
    print("   • Clean markdown rendering")
    print("🔄 Starting Report Viewer interface...")
    
    launch_report_viewer()