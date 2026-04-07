#!/usr/bin/env python
"""
Setup script for OllamaOpt Rich CLI
Installs dependencies and configures the environment
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd):
    """Run a shell command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def main():
    print("\n" + "="*60)
    print("  OllamaOpt Rich CLI - Setup")
    print("="*60 + "\n")
    
    # Check Python version
    print("[1/4] Checking Python version...")
    if sys.version_info < (3, 8):
        print(f"✗ Python 3.8+ required, you have {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} found")
    
    # Install dependencies
    print("\n[2/4] Installing dependencies...")
    dependencies = ["rich", "requests", "psutil"]
    
    for dep in dependencies:
        print(f"  Installing {dep}...", end=" ", flush=True)
        success, output = run_command(f"{sys.executable} -m pip install -q {dep}")
        if success:
            print("✓")
        else:
            print(f"✗ (Error: {output})")
    
    # Verify imports
    print("\n[3/4] Verifying imports...")
    try:
        print("  Importing rich...", end=" ", flush=True)
        import rich
        print("✓")
        
        print("  Importing requests...", end=" ", flush=True)
        import requests
        print("✓")
        
        print("  Importing psutil...", end=" ", flush=True)
        import psutil
        print("✓")
        
        print("  Importing cli...", end=" ", flush=True)
        from cli import ollama_cli
        print("✓")
    except ImportError as e:
        print(f"✗ (Error: {e})")
        sys.exit(1)
    
    # Check Ollama
    print("\n[4/4] Checking Ollama server...")
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            print(f"✓ Ollama server running ({len(models)} models available)")
            if models:
                print(f"  First model: {models[0].get('name', 'Unknown')}")
        else:
            print(f"⚠ Ollama server returned status {resp.status_code}")
    except Exception as e:
        print(f"⚠ Ollama server not accessible: {e}")
        print("  Make sure to run: ollama serve")
    
    print("\n" + "="*60)
    print("✓ Setup complete!")
    print("="*60)
    print("\nNext steps:")
    print("  1. Start Ollama: ollama serve")
    print("  2. Run the CLI: python -m cli.ollama_cli")
    print("     OR: run_ollama_cli.bat (Windows)")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
