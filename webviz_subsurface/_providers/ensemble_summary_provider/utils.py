import fnmatch
import re
from typing import List

from .ensemble_summary_provider import EnsembleSummaryProvider


def get_matching_vector_names(
    provider: EnsembleSummaryProvider, column_keys: List[str]
) -> List[str]:
    """Returns a list of vectors that match the input columns_keys that
    can have unix shell wildcards.

    Example of use:
    column_keys = ["FOPT", "WGOR*"]
    matching_vector_names = get_matching_vector_names(provider, column_keys)
    df = provider.get_vectors_df(matching_vector_names, None)

    """
    regex = re.compile(
        "|".join([fnmatch.translate(col) for col in column_keys]),
        flags=re.IGNORECASE,
    )
    return [vec for vec in provider.vector_names() if regex.fullmatch(vec)]
