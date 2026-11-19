"""`python3 -m invoicer` runs the same command as `invoicer`, which cli.py decides."""

import sys

from invoicer.cli import main

sys.exit(main())
