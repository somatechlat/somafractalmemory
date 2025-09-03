import os
import sys

# Ensure the src/ layout is first on sys.path for tests
SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
