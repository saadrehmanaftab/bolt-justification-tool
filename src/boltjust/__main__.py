"""Command line: python -m boltjust <fe_export.csv> <out_dir>"""
import sys, json
from .postprocess import run

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python -m boltjust <fe_export.csv> <out_dir>")
    summary, _ = run(sys.argv[1], sys.argv[2])
    print(json.dumps(summary, indent=1))
