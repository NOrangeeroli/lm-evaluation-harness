"""
Local utils module for ChemLLMBench ADeLe tasks.

This file re-exports helpers from `lm_eval.tasks.adele.utils` so that
YAML files in this directory can use `!function utils.<name>`.
"""

from lm_eval.tasks.adele.utils import (
    process_docs_molecule_captioning,
    process_docs_molecule_design,
    process_docs_name_prediction,
    process_docs_reaction_prediction,
    process_docs_retrosynthesis,
    process_results_gen,
    doc_to_target,
)

