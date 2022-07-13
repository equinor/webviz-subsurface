from typing import Dict, List


def _get_well_names_combined(
    well_collections: Dict[str, List[str]],
    selected_collection_names: list,
    selected_wells: list,
    combine_type: str = "intersection",
) -> List[str]:
    """Return union or intersection of well list and well collection lists."""

    selected_collection_wells = []
    for collection_name in selected_collection_names:
        selected_collection_wells.extend(well_collections[collection_name])
    selected_collection_wells = list(set(selected_collection_wells))
    if combine_type == "intersection":
        # find intersection of selector wells and selector well collections
        well_names_combined = [
            well for well in selected_wells if well in selected_collection_wells
        ]
    else:
        # find union of selector wells and selector well collections
        well_names_combined = list(selected_collection_wells)
        well_names_combined.extend(selected_wells)
        well_names_combined = list(set(well_names_combined))

    return well_names_combined
