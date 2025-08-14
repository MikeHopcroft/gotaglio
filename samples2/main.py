import os
import sys

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.main import main

from dag.dag import dag_pipeline_spec
from menu.menu import menu_pipeline_spec
from calc.calc import calc_pipeline_spec


def go():
    main([dag_pipeline_spec, menu_pipeline_spec, calc_pipeline_spec])


if __name__ == "__main__":
    go()
