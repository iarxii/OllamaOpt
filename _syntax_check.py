"""Temporary syntax and import check for cli/rag modules."""
import ast
import sys
from pathlib import Path

rag_dir = Path(__file__).parent / "cli" / "rag"
files = sorted(rag_dir.glob("*.py"))

if not files:
    print("ERROR: No .py files found in cli/rag/")
    sys.exit(1)

all_ok = True
for f in files:
    try:
        source = f.read_text(encoding="utf-8")
        ast.parse(source)
        print(f"  SYNTAX OK  {f.name}")
    except SyntaxError as exc:
        print(f"  SYNTAX ERR {f.name}  ->  {exc}")
        all_ok = False
    except Exception as exc:
        print(f"  READ ERR   {f.name}  ->  {exc}")
        all_ok = False

print()
if all_ok:
    print("All files parsed without syntax errors.")
else:
    print("One or more files have syntax errors.")
    sys.exit(1)
