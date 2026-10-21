#!/usr/bin/env python
"""Production runner: execute main.ipynb from a clean kernel, save executed notebook."""
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent
nb = nbformat.read(ROOT / "main.ipynb", as_version=4)
client = NotebookClient(nb, timeout=600, kernel_name="python3",
                        resources={"metadata": {"path": str(ROOT)}})
t0 = time.time()
client.execute()
nbformat.write(nb, ROOT / "main.ipynb")
print(f"EXECUTION OK in {time.time() - t0:.1f}s")
