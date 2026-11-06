"""
bench/__main__.py

CLI entrypoint allowing `python -m bench` or `python -m bench.runner`.
"""

import sys
from bench.runner import main

if __name__ == "__main__":
    sys.exit(main())
