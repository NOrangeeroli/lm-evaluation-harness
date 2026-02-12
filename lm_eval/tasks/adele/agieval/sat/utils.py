"""
Local utils module for AGIEval SAT ADeLe tasks.

This file re-exports helpers from `lm_eval.tasks.adele.utils` so that
YAML files in this directory can use `!function utils.<name>`.
"""

from lm_eval.tasks.adele.utils import (
    process_docs_sat_en,
    process_docs_sat_math,
    doc_to_target_letter,
)
