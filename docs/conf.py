import os
import sys

# Add project src to sys.path
sys.path.insert(0, os.path.abspath("../src"))

project = "SomaFractalMemory"
author = "SomaTech"
release = "0.1.0"

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

master_doc = "index"
html_theme = "alabaster"
