import datasets
from functools import partial


def process_docs(dataset: datasets.Dataset, task_name: str = None) -> datasets.Dataset:
    """
    Filter the BBEH dataset by the 'task' column to get only the rows
    corresponding to the specific BBEH task.
    
    Args:
        dataset: The full BBEH dataset from HuggingFace
        task_name: The task name to filter by (e.g., "boolean expressions", "boardgame qa")
    
    Returns:
        Filtered dataset containing only examples for the specified task
    """
    if task_name is None:
        # If no task name is provided, return the whole dataset
        return dataset
        
    # Filter the dataset by the 'task' column
    return dataset.filter(lambda example: example["task"] == task_name)



process_docs_boolean_expressions = partial(process_docs, task_name="boolean expressions")
process_docs_causal_understanding = partial(process_docs, task_name="causal understanding")
process_docs_disambiguation_qa = partial(process_docs, task_name="disambiguation qa")
process_docs_geometric_shapes = partial(process_docs, task_name="geometric shapes")
process_docs_hyperbaton = partial(process_docs, task_name="hyperbaton")
process_docs_movie_recommendation = partial(process_docs, task_name="movie recommendation")
process_docs_object_counting = partial(process_docs, task_name="object counting")
process_docs_sportqa = partial(process_docs, task_name="sportqa")
process_docs_temporal_sequence = partial(process_docs, task_name="temporal sequence")
process_docs_shuffled_objects = partial(process_docs, task_name="shuffled objects")
process_docs_web_of_lies = partial(process_docs, task_name="web of lies")
process_docs_boardgame_qa = partial(process_docs, task_name="boardgame qa")
process_docs_buggy_tables = partial(process_docs, task_name="buggy tables")
process_docs_dyck_languages = partial(process_docs, task_name="dyck languages")
process_docs_linguini = partial(process_docs, task_name="linguini")
process_docs_multistep_arithmetic = partial(process_docs, task_name="multistep arithmetic")
process_docs_nycc = partial(process_docs, task_name="nycc")
process_docs_object_properties = partial(process_docs, task_name="object properties")
process_docs_sarc_triples = partial(process_docs, task_name="sarc triples")
process_docs_spatial_reasoning = partial(process_docs, task_name="spatial reasoning")
process_docs_time_arithmetic = partial(process_docs, task_name="time arithmetic")
process_docs_word_sorting = partial(process_docs, task_name="word sorting")
process_docs_zebra_puzzles = partial(process_docs, task_name="zebra puzzles")
