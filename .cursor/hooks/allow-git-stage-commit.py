#!/usr/bin/env python3
"""Auto-allow git add and git commit in this repo (beforeShellExecution hook).

The hooks.json matcher already limits this to commands containing
'git add' or 'git commit'. This script only returns allow.
"""
import json
import sys

def main() -> None:
    sys.stdin.read()  # consume hook input JSON
    print(json.dumps({"permission": "allow"}))


if __name__ == "__main__":
    main()
