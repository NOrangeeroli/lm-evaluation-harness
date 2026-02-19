import ast
import datasets
from functools import partial
import numpy as np
import re

try:
    import evaluate

    bleu = evaluate.load("bleu")
    # rouge = evaluate.load("rouge")
    # bertscore = evaluate.load("bertscore")
    # bleurt = evaluate.load("bleurt", "bleurt-base-512", module_type="metric")

except (ModuleNotFoundError, ImportError):
    raise ModuleNotFoundError(
        "Please install evaluation metrics via pip install evaluate bert-score "
        "rouge_score>=0.1.2 nltk absl-py "
        "git+https://github.com/google-research/bleurt.git"
    )
except Exception as e:
    raise RuntimeError(
        f"Error loading evaluation metrics: {str(e)}. Please check your installation."
    )




def process_results_gen(doc, results):
    pred, refs = [results[0]], [doc_to_target(doc)]

    if len(refs[0]) < 1 or len(pred[0]) < 1:
        return {
            "bleu": np.NAN,
           
        }

    
    try:
        
        bleu_results = bleu.compute(predictions=pred, references=refs)
    except Exception as e:
        print(f"Bleu error: {e}")
        bleu_results = {"bleu": np.NAN}

    

    if bleu_results["bleu"] == 0:
        # Sometimes bleu is 0.0 and this breaks the stderr computation.
        bleu_results["bleu"] += 1e-5

    return {
        "bleu": bleu_results["bleu"],
    }


def process_results_molecule_captioning(doc, results):
    """
    Custom metric for molecule_captioning tasks.
    
    Computes BLEU score but reports it as 'exact_match' to keep the metric name consistent.
    """
    pred, refs = [results[0]], [doc_to_target(doc)]

    if len(refs[0]) < 1 or len(pred[0]) < 1:
        return {
            "exact_match": np.NAN,
        }

    try:
        bleu_results = bleu.compute(predictions=pred, references=refs)
    except Exception as e:
        print(f"BLEU error for molecule_captioning: {e}")
        bleu_results = {"bleu": np.NAN}

    if bleu_results["bleu"] == 0:
        # Sometimes bleu is 0.0 and this breaks the stderr computation.
        bleu_results["bleu"] += 1e-5

    # Return BLEU score under the 'exact_match' key
    return {
        "exact_match": bleu_results["bleu"],
    }


def _extract_first_float(text: str) -> float | None:
    """
    Extract the first floating-point number from a string.
    Returns None if no number is found.
    """
    if not isinstance(text, str):
        text = str(text)
    # Remove thousands separators if present
    cleaned = text.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def process_results_medcalcbench(doc, results):
    """
    Custom metric for MedCalcBench tasks.

    Groundtruth sometimes contains a tolerance range, e.g.:
        "The groundtruth is 46.667 but anything between 44.33365 and 49.00035
         can be counted as correct to have an error tolerance of 5%"

    In that case we:
      - extract the numeric prediction from the model output,
      - extract the lower/upper bounds from the groundtruth,
      - return exact_match = 1.0 if prediction is within [lower, upper], else 0.0.

    If the groundtruth does not match this template, we fall back to a
    string-based exact match (loosely normalized).
    """
    if not results:
        return {"exact_match": 0.0}

    pred_text = str(results[0])
    gt_text = str(doc.get("groundtruth", ""))

    # Try to parse a numeric prediction
    pred_val = _extract_first_float(pred_text)

    # Try to find "between <lower> and <upper>" pattern in groundtruth
    range_match = re.search(
        r"between\s+(-?\d+(?:\.\d+)?)\s+and\s+(-?\d+(?:\.\d+)?)", gt_text.replace(",", "")
    )

    if range_match and pred_val is not None:
        try:
            lower = float(range_match.group(1))
            upper = float(range_match.group(2))
            in_range = lower <= pred_val <= upper
            return {"exact_match": 1.0 if in_range else 0.0}
        except ValueError:
            # If parsing fails for some reason, fall back to string match
            pass

    # Fallback: approximate string-based exact match, mirroring template behavior
    def _normalize(s: str) -> str:
        s = s.strip().lower()
        # Remove trailing period and common punctuation / escapes used in regexes_to_ignore
        s = re.sub(r"[\\.,\"\\n]", "", s)
        return s

    return {
        "exact_match": 1.0 if _normalize(pred_text) == _normalize(gt_text) else 0.0
    }


def process_results_smile(doc, results):
    """
    Custom metric for SMILES-based tasks (molecule_design, retrosynthesis) using InChI comparison.

    Converts both prediction and groundtruth SMILES to InChI format using RDKit,
    then compares the InChI strings. This is more robust than string matching
    because different SMILES representations of the same molecule will have
    the same InChI.

    Based on the evaluation method from the Molecule_Design.ipynb notebook.
    """
    if not results:
        return {"exact_match": 0.0}

    pred_text = str(results[0]).strip()
    gt_text = str(doc.get("groundtruth", "")).strip()

    try:
        from rdkit import Chem  # type: ignore[import]
    except ImportError as e:
        raise ModuleNotFoundError(
            "rdkit is required for SMILES-based tasks (molecule_design, retrosynthesis). "
            "Please install via `pip install rdkit`."
        ) from e

    try:
        # Convert prediction SMILES to molecule and then to InChI
        pred_mol = Chem.MolFromSmiles(pred_text)
        if pred_mol is None:
            # Invalid SMILES - treat as incorrect
            return {"exact_match": 0.0}
        pred_inchi = Chem.MolToInchi(pred_mol)

        # Convert groundtruth SMILES to molecule and then to InChI
        gt_mol = Chem.MolFromSmiles(gt_text)
        if gt_mol is None:
            # Invalid groundtruth - this shouldn't happen, but treat as incorrect
            return {"exact_match": 0.0}
        gt_inchi = Chem.MolToInchi(gt_mol)

        # Compare InChI strings
        ok = pred_inchi == gt_inchi
    except Exception as e:
        # If conversion fails for any reason, treat as incorrect but log the error
        print(f"InChI conversion error for SMILES task: {e}")
        ok = False

    # Expose this check as 'exact_match' so SMILES-based tasks keep the standard metric name.
    return {
        "exact_match": 1.0 if ok else 0.0,
    }


def process_results_math(doc, results):
    """
    Custom metric for OmniMath tasks using math_verify.

    We interpret both the model prediction and the groundtruth as math
    expressions / solutions, and delegate equivalence checking to
    math_verify.parse + math_verify.verify.
    """
    if not results:
        return {"exact_match": 0.0}

    pred_text = str(results[0])
    gt_text = str(doc.get("groundtruth", ""))

    # Wrap with $$ for LaTeX math mode
    pred_text = f"${pred_text}$"
    gt_text = f"${gt_text}$"

    try:
        from math_verify import parse, verify  # type: ignore[import]
    except ImportError as e:
        raise ModuleNotFoundError(
            "math_verify is required for OmniMath tasks. "
            "Please install via `pip install lm-eval[math]` or `pip install -e .[math]`."
        ) from e

    try:
        ok = verify(gold=parse(gt_text), target=parse(pred_text))
        ok = ok or pred_text == gt_text
    except Exception as e:
        # If parsing or verification fails, treat as incorrect but log the error.
        print(f"math_verify error for OmniMath: {e}")
        ok = False

    # Expose this check as 'exact_match' so OmniMath tasks keep the standard metric name.
    return {
        "exact_match": 1.0 if ok else 0.0,
    }


def process_docs(
    dataset: datasets.Dataset,
    task_name: str | None = None,
    benchmark_name: str | None = None,
) -> datasets.Dataset:
    """
    Filter the ADeLe dataset by the 'task' (and optionally 'benchmark')
    columns to get only the rows corresponding to the specific ADeLe task.
    
    Args:
        dataset: The full ADeLe dataset from HuggingFace
        task_name: The task name to filter by (e.g., "molecule_captioning", "biology")
        benchmark_name: Optional benchmark name to filter by (e.g., "ChemLLMBench",
            "MMLU-Pro"). When provided, both benchmark and task must match.
    
    Returns:
        Filtered dataset containing only examples for the specified task
    """
    if task_name is None and benchmark_name is None:
        # If no filter is provided, return the whole dataset
        return dataset
        
    def _predicate(example: dict) -> bool:
        ok = True
        if task_name is not None:
            ok = ok and example.get("task") == task_name
        if benchmark_name is not None:
            ok = ok and example.get("benchmark") == benchmark_name
        return ok

    # Filter the dataset by the specified columns
    return dataset.filter(_predicate)


def doc_to_target(doc: dict) -> str:
    """
    Extract the letter from groundtruth for MC tasks.
    Groundtruth format is like "G. The answer text..."
    Returns just the letter (e.g., "G").
    """
    groundtruth = str(doc.get("groundtruth", ""))
    return groundtruth


def doc_to_target_letter(doc: dict) -> str:
    """
    Extract just the letter from groundtruth for MC tasks.
    Groundtruth format is like "G. The answer text..." or just "G"
    Returns just the letter (e.g., "G").
    """
    groundtruth = str(doc.get("groundtruth", "")).strip()
    if not groundtruth:
        return ""
    # If it's just a single letter, return it
    if len(groundtruth) == 1 and groundtruth.isalpha():
        return groundtruth.upper()
    # If it starts with a letter followed by a period or space, extract the letter
    match = re.match(r"^([A-Z])[.\s]", groundtruth)
    if match:
        return match.group(1)
    # Otherwise, try to extract the first letter
    if groundtruth[0].isalpha():
        return groundtruth[0].upper()
    return groundtruth


def _parse_truthquest_groundtruth(groundtruth_str: str) -> dict:
    """
    Parse TruthQuest groundtruth into a dict mapping option letters to bool.

    Groundtruth format is like:
        [{'A': False, 'B': False, 'C': False, 'D': True, 'E': True, 'F': True}]
    or a single dict. Returns dict like {'A': False, 'B': False, 'C': False, 'D': True, ...}.
    """
    s = (groundtruth_str or "").strip()
    if not s:
        return {}
    try:
        parsed = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return {}
    if isinstance(parsed, list) and len(parsed) > 0:
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        return {}
    return {str(k).strip().upper(): bool(v) for k, v in parsed.items()}


def _parse_truthquest_prediction(pred_str: str) -> dict:
    """
    Parse TruthQuest model output into a dict mapping option letters to bool.

    Model output format is like:
        "A is a knight, B is a knave, and C is a knave."
    Returns dict like {'A': True, 'B': False, 'C': False} where True=knight, False=knave.
    """
    s = (pred_str or "").strip()
    if not s:
        return {}
    result = {}
    # Pattern to match "X is a knight" or "X is a knave" (case-insensitive)
    # Also handle variations like "X is knight", "X is knave", "X is the knight", etc.
    pattern = r"([A-Z])(?:(?![A-Z]|knight|knave).)*(knight|knave)"

    matches = re.finditer(pattern, s, re.IGNORECASE)
    for match in matches:
        letter = match.group(1).upper()
        role = match.group(2).lower()
        # knight -> True, knave -> False
        result[letter] = role == "knight"
    return result


def process_results_truthquest(doc, results):
    """
    Evaluate TruthQuest tasks: groundtruth is a dict mapping letters to bool (True=knight, False=knave).
    Model output is parsed to extract statements like "A is a knight, B is a knave" and build
    a dict mapping letters to bool. The two dicts are compared for exact match.
    """
    if not results:
        return {"exact_match": 0.0}
    gt_str = str(doc.get("groundtruth", "")).strip()
    gt_dict = _parse_truthquest_groundtruth(gt_str)
    pred_str = (results[0] or "").strip() if results else ""
    pred_dict = _parse_truthquest_prediction(pred_str)
    # Compare dicts: exact match only if all keys match and values match
    if not gt_dict and not pred_dict:
        return {"exact_match": 1.0}
    if gt_dict.keys() != pred_dict.keys():
        return {"exact_match": 0.0}
    return {"exact_match": 1.0 if gt_dict == pred_dict else 0.0}


# Process docs functions for individual tasks
process_docs_molecule_captioning = partial(
    process_docs, task_name="molecule_captioning", benchmark_name="ChemLLMBench"
)
process_docs_molecule_design = partial(
    process_docs, task_name="molecule_design", benchmark_name="ChemLLMBench"
)
process_docs_name_prediction = partial(
    process_docs, task_name="name_prediction", benchmark_name="ChemLLMBench"
)
process_docs_reaction_prediction = partial(
    process_docs, task_name="reaction_prediction", benchmark_name="ChemLLMBench"
)
process_docs_retrosynthesis = partial(
    process_docs, task_name="retrosynthesis", benchmark_name="ChemLLMBench"
)

# AGIEval tasks
process_docs_logiqa_en = partial(
    process_docs, task_name="LogiQA-en", benchmark_name="Civil Service Examination"
)
process_docs_aqua_rat = partial(
    process_docs, task_name="AQuA-RAT", benchmark_name="GRE & GMAT"
)
process_docs_lsat_ar = partial(
    process_docs, task_name="LSAT-AR", benchmark_name="LSAT"
)
process_docs_lsat_lr = partial(
    process_docs, task_name="LSAT-LR", benchmark_name="LSAT"
)
process_docs_lsat_rc = partial(
    process_docs, task_name="LSAT-RC", benchmark_name="LSAT"
)
process_docs_sat_en = partial(
    process_docs, task_name="SAT-En", benchmark_name="SAT"
)
process_docs_sat_math = partial(
    process_docs, task_name="SAT-Math", benchmark_name="SAT"
)

# LiveBench tasks
process_docs_livebench_cta = partial(
    process_docs, task_name="cta", benchmark_name="Data Analysis"
)
process_docs_livebench_connections = partial(
    process_docs, task_name="connections", benchmark_name="Language"
)
process_docs_livebench_amps_hard = partial(
    process_docs, task_name="AMPS_Hard", benchmark_name="Math"
)
process_docs_livebench_math_comp = partial(
    process_docs, task_name="math_comp", benchmark_name="Math"
)
process_docs_livebench_olympiad = partial(
    process_docs, task_name="olympiad", benchmark_name="Math"
)
process_docs_livebench_spatial = partial(
    process_docs, task_name="spatial", benchmark_name="Reasoning"
)
process_docs_livebench_zebra_puzzle = partial(
    process_docs, task_name="zebra_puzzle", benchmark_name="Reasoning"
)

# MMLU-Pro tasks (single benchmark "MMLU-Pro")
process_docs_mmlu_pro_biology = partial(
    process_docs, task_name="biology", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_business = partial(
    process_docs, task_name="business", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_chemistry = partial(
    process_docs, task_name="chemistry", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_computer_science = partial(
    process_docs, task_name="computer science", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_economics = partial(
    process_docs, task_name="economics", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_engineering = partial(
    process_docs, task_name="engineering", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_health = partial(
    process_docs, task_name="health", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_history = partial(
    process_docs, task_name="history", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_law = partial(
    process_docs, task_name="law", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_math = partial(
    process_docs, task_name="math", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_other = partial(
    process_docs, task_name="other", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_philosophy = partial(
    process_docs, task_name="philosophy", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_physics = partial(
    process_docs, task_name="physics", benchmark_name="MMLU-Pro"
)
process_docs_mmlu_pro_psychology = partial(
    process_docs, task_name="psychology", benchmark_name="MMLU-Pro"
)

# MedCalcBench tasks (single benchmark "MedCalcBench")
process_docs_medcalcbench_date = partial(
    process_docs, task_name="date", benchmark_name="MedCalcBench"
)
process_docs_medcalcbench_diagnosis = partial(
    process_docs, task_name="diagnosis", benchmark_name="MedCalcBench"
)
process_docs_medcalcbench_dosage = partial(
    process_docs, task_name="dosage", benchmark_name="MedCalcBench"
)
process_docs_medcalcbench_lab = partial(
    process_docs, task_name="lab", benchmark_name="MedCalcBench"
)
process_docs_medcalcbench_physical = partial(
    process_docs, task_name="physical", benchmark_name="MedCalcBench"
)
process_docs_medcalcbench_risk = partial(
    process_docs, task_name="risk", benchmark_name="MedCalcBench"
)
process_docs_medcalcbench_severity = partial(
    process_docs, task_name="severity", benchmark_name="MedCalcBench"
)

# OmniMath tasks (single benchmark "OmniMath")
process_docs_omnimath_algebra = partial(
    process_docs, task_name="Algebra", benchmark_name="OmniMath"
)
process_docs_omnimath_applied_mathematics = partial(
    process_docs, task_name="Applied Mathematics", benchmark_name="OmniMath"
)
process_docs_omnimath_calculus = partial(
    process_docs, task_name="Calculus", benchmark_name="OmniMath"
)
process_docs_omnimath_discrete_mathematics = partial(
    process_docs, task_name="Discrete Mathematics", benchmark_name="OmniMath"
)
process_docs_omnimath_geometry = partial(
    process_docs, task_name="Geometry", benchmark_name="OmniMath"
)
process_docs_omnimath_number_theory = partial(
    process_docs, task_name="Number Theory", benchmark_name="OmniMath"
)
process_docs_omnimath_precalculus = partial(
    process_docs, task_name="Precalculus", benchmark_name="OmniMath"
)

# SciBench tasks (single benchmark "SciBench")
process_docs_scibench_chemistry = partial(
    process_docs, task_name="Chemistry", benchmark_name="SciBench"
)
process_docs_scibench_math = partial(
    process_docs, task_name="Math", benchmark_name="SciBench"
)
process_docs_scibench_physics = partial(
    process_docs, task_name="Physics", benchmark_name="SciBench"
)

# TimeBench tasks
process_docs_timebench_date_arithmetic = partial(
    process_docs, task_name="Date Arithmetic", benchmark_name="Date Arithmetic"
)
process_docs_timebench_mctaco = partial(
    process_docs, task_name="MCTACO", benchmark_name="MCTACO"
)
process_docs_timebench_menatqa_counterfactual = partial(
    process_docs, task_name="MenatQA-Counterfactual", benchmark_name="MenatQA"
)
process_docs_timebench_menatqa_order = partial(
    process_docs, task_name="MenatQA-Order", benchmark_name="MenatQA"
)
process_docs_timebench_menatqa_scope = partial(
    process_docs, task_name="MenatQA-Scope", benchmark_name="MenatQA"
)
process_docs_timebench_tempreason_l2 = partial(
    process_docs, task_name="TempReason-L2", benchmark_name="TempReason"
)
process_docs_timebench_tempreason_l3 = partial(
    process_docs, task_name="TempReason-L3", benchmark_name="TempReason"
)
process_docs_timebench_timedial = partial(
    process_docs, task_name="TimeDial", benchmark_name="TimeDial"
)
process_docs_timebench_timeqa_explicit = partial(
    process_docs, task_name="TimeQA-explicit", benchmark_name="TimeQA"
)
process_docs_timebench_timeqa_implicit = partial(
    process_docs, task_name="TimeQA-implicit", benchmark_name="TimeQA"
)

# TruthQuest tasks (single benchmark "TruthQuest")
process_docs_truthquest_e = partial(
    process_docs, task_name="E", benchmark_name="TruthQuest"
)
process_docs_truthquest_i = partial(
    process_docs, task_name="I", benchmark_name="TruthQuest"
)
process_docs_truthquest_s = partial(
    process_docs, task_name="S", benchmark_name="TruthQuest"
)





