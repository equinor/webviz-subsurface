from typing import List, Optional

from webviz_subsurface._providers import EnsembleSummaryProvider


def create_valid_realizations_query(
    selected_realizations: List[int], provider: EnsembleSummaryProvider
) -> Optional[List[int]]:
    """Create realizations query for provider based on selected realizations.

    `Returns:`
    - None - If all realizations for provider is selected, i.e. the query is non-filtering
    - List[int] - List of realization numbers existing for the provider - empty list
    is returned if no realizations exist.
    """
    if set(provider.realizations()).issubset(set(selected_realizations)):
        return None
    return [
        realization
        for realization in selected_realizations
        if realization in provider.realizations()
    ]
