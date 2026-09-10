#!/usr/bin/env python3
"""
Alias / forwarder to main.py for backward compatibility.
Allows execution via `python run.py https://example.com/`
"""

import sys
from main import main

if __name__ == '__main__':
    main()
