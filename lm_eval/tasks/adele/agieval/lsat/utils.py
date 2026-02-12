"""
Local utils module for AGIEval LSAT ADeLe tasks.

This file re-exports helpers from `lm_eval.tasks.adele.utils` so that
YAML files in this directory can use `!function utils.<name>`.
"""

from lm_eval.tasks.adele.utils import (
    process_docs_lsat_ar,
    process_docs_lsat_lr,
    process_docs_lsat_rc,
    doc_to_target_letter,
)
