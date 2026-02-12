"""
Local utils module for AGIEval GRE & GMAT ADeLe tasks.

This file re-exports helpers from `lm_eval.tasks.adele.utils` so that
YAML files in this directory can use `!function utils.<name>`.
"""

from lm_eval.tasks.adele.utils import (
    process_docs_aqua_rat,
    doc_to_target_letter,
)
