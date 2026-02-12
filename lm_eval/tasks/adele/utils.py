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



def process_docs(dataset: datasets.Dataset, task_name: str = None) -> datasets.Dataset:
    """
    Filter the ADeLe dataset by the 'task' column to get only the rows
    corresponding to the specific ADeLe task.
    
    Args:
        dataset: The full ADeLe dataset from HuggingFace
        task_name: The task name to filter by (e.g., "molecule_captioning", "biology")
    
    Returns:
        Filtered dataset containing only examples for the specified task
    """
    if task_name is None:
        # If no task name is provided, return the whole dataset
        return dataset
        
    # Filter the dataset by the 'task' column
    return dataset.filter(lambda example: example["task"] == task_name)


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
process_docs_molecule_captioning = partial(process_docs, task_name="molecule_captioning")
process_docs_molecule_design = partial(process_docs, task_name="molecule_design")
process_docs_name_prediction = partial(process_docs, task_name="name_prediction")
process_docs_reaction_prediction = partial(process_docs, task_name="reaction_prediction")
process_docs_retrosynthesis = partial(process_docs, task_name="retrosynthesis")

# AGIEval tasks
process_docs_logiqa_en = partial(process_docs, task_name="LogiQA-en")
process_docs_aqua_rat = partial(process_docs, task_name="AQuA-RAT")
process_docs_lsat_ar = partial(process_docs, task_name="LSAT-AR")
process_docs_lsat_lr = partial(process_docs, task_name="LSAT-LR")
process_docs_lsat_rc = partial(process_docs, task_name="LSAT-RC")
process_docs_sat_en = partial(process_docs, task_name="SAT-En")
process_docs_sat_math = partial(process_docs, task_name="SAT-Math")

# LiveBench tasks
process_docs_livebench_cta = partial(process_docs, task_name="cta")
process_docs_livebench_connections = partial(process_docs, task_name="connections")
process_docs_livebench_amps_hard = partial(process_docs, task_name="AMPS_Hard")
process_docs_livebench_math_comp = partial(process_docs, task_name="math_comp")
process_docs_livebench_olympiad = partial(process_docs, task_name="olympiad")
process_docs_livebench_spatial = partial(process_docs, task_name="spatial")
process_docs_livebench_zebra_puzzle = partial(process_docs, task_name="zebra_puzzle")





