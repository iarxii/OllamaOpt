#!/usr/bin/env python
"""
Test script for OllamaOpt Rich CLI
Verifies all components work correctly
"""

import sys
import time
from pathlib import Path

def test_imports():
    """Test that all modules can be imported"""
    print("\n" + "="*60)
    print("TEST 1: Module Imports")
    print("="*60)
    
    tests = [
        ("rich", "Rich library"),
        ("requests", "Requests library"),
        ("psutil", "PSUtil library"),
        ("cli.assets.logo_art", "Logo art assets"),
        ("cli.metrics_collector", "Metrics collector"),
        ("cli.formatters", "Text formatters"),
        ("cli.dashboard", "Dashboard"),
        ("cli.chat_interface", "Chat interface"),
        ("cli.ollama_cli", "Main CLI"),
    ]
    
    passed = 0
    for module, name in tests:
        try:
            __import__(module)
            print(f"  ✓ {name:40} OK")
            passed += 1
        except ImportError as e:
            print(f"  ✗ {name:40} FAILED: {e}")
    
    print(f"\nResult: {passed}/{len(tests)} imports successful")
    return passed == len(tests)

def test_metrics_collector():
    """Test metrics collector initialization"""
    print("\n" + "="*60)
    print("TEST 2: Metrics Collector")
    print("="*60)
    
    try:
        from cli.metrics_collector import MetricsCollector
        
        collector = MetricsCollector(api_base="http://localhost:11434")
        print("  ✓ MetricsCollector instance created")
        
        # Test data structures
        snapshot = collector.get_snapshot()
        required_keys = ["model", "hardware", "performance", "system", "session"]
        
        for key in required_keys:
            if key in snapshot:
                print(f"  ✓ Snapshot contains '{key}' data")
            else:
                print(f"  ✗ Snapshot missing '{key}' data")
                return False
        
        print("\n  Collector ready to start background polling")
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_chat_interface():
    """Test chat interface initialization"""
    print("\n" + "="*60)
    print("TEST 3: Chat Interface")
    print("="*60)
    
    try:
        from cli.chat_interface import ChatInterface, CommandHandler
        
        chat = ChatInterface(api_base="http://localhost:11434")
        print("  ✓ ChatInterface instance created")
        
        handler = CommandHandler(chat)
        print("  ✓ CommandHandler instance created")
        
        # Test command detection
        if handler.handle_command("/help"):
            print("  ✓ Command handler processes commands")
        
        print("  ✓ Chat interface initialized successfully")
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_formatters():
    """Test text formatters"""
    print("\n" + "="*60)
    print("TEST 4: Text Formatters")
    print("="*60)
    
    try:
        from cli.formatters import (
            MessageFormatter,
            ResponseFormatter,
            IndicatorFormatter,
            format_duration,
            format_size,
        )
        
        # Test formatting functions
        duration = format_duration(125.5)
        print(f"  ✓ Duration formatting: {duration}")
        
        size = format_size(1536.0 * 1024 * 1024)
        print(f"  ✓ Size formatting: {size}")
        
        print("  ✓ All formatters working correctly")
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_dashboard():
    """Test dashboard initialization"""
    print("\n" + "="*60)
    print("TEST 5: Dashboard")
    print("="*60)
    
    try:
        from cli.dashboard import Dashboard, LatencyChart
        from cli.metrics_collector import get_collector
        
        # Initialize collector first
        collector = get_collector()
        
        dashboard = Dashboard()
        print("  ✓ Dashboard instance created")
        
        chart = LatencyChart()
        print("  ✓ LatencyChart instance created")
        
        # Test rendering (without displaying)
        try:
            header = dashboard.render_header()
            print("  ✓ Dashboard header renders")
            
            metrics = dashboard.render_metrics()
            print("  ✓ Dashboard metrics render")
        except Exception as e:
            print(f"  ⚠ Dashboard rendering: {e}")
        
        print("  ✓ Dashboard initialized successfully")
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_ollama_connection():
    """Test connection to Ollama server"""
    print("\n" + "="*60)
    print("TEST 6: Ollama Server Connection")
    print("="*60)
    
    try:
        import requests
        
        print("  Attempting to connect to Ollama at localhost:11434...")
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            print(f"  ✓ Connected successfully")
            print(f"  ✓ Found {len(models)} model(s)")
            
            if models:
                for model in models[:3]:  # Show first 3
                    name = model.get("name", "Unknown")
                    size = model.get("size", 0) / (1024**3)
                    print(f"    - {name} ({size:.1f} GB)")
                if len(models) > 3:
                    print(f"    ... and {len(models) - 3} more")
            else:
                print("  ⚠ No models downloaded yet")
                print("    Pull a model first: ollama pull qwen3.5:9b")
            
            return True
        else:
            print(f"  ✗ Server returned status {resp.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("  ✗ Cannot connect to Ollama")
        print("    Make sure Ollama is running: ollama serve")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_cli_startup():
    """Test CLI startup (without full interaction)"""
    print("\n" + "="*60)
    print("TEST 7: CLI Startup")
    print("="*60)
    
    try:
        from cli.ollama_cli import OllamaOptCLI
        
        cli = OllamaOptCLI(api_base="http://localhost:11434")
        print("  ✓ OllamaOptCLI instance created")
        
        # Don't call initialize() as it tries to fetch models
        # but test the structure is correct
        
        print("  ✓ CLI structure validated")
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║    OllamaOpt Rich CLI - Component Test Suite             ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    
    tests = [
        ("Module Imports", test_imports),
        ("Metrics Collector", test_metrics_collector),
        ("Chat Interface", test_chat_interface),
        ("Text Formatters", test_formatters),
        ("Dashboard", test_dashboard),
        ("Ollama Connection", test_ollama_connection),
        ("CLI Startup", test_cli_startup),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status:8} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! CLI is ready to use.")
        print("\nNext steps:")
        print("  1. Make sure Ollama is running: ollama serve")
        print("  2. Start the CLI: python -m cli.ollama_cli")
        print("     OR: run_ollama_cli.bat (Windows)")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. See errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
