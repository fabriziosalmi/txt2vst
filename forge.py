#!/usr/bin/env python3
"""VST Forge CLI — generates a compilable JUCE VST project from a spec.json.

Usage:
    python forge.py <spec.json> <output_dir>
"""

import sys
from forge import generate

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python forge.py <spec.json> <output_dir>")
        sys.exit(1)
    generate(sys.argv[1], sys.argv[2])
