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

    print("pred: ", pred)
    print("refs: ", refs)
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





