# Lets pytest import core/, plugins/ and qecon/ from the repo root.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The submission notebook writes a copy of the project here. Its tests are not separate tests.
collect_ignore = ["qecon_src"]
