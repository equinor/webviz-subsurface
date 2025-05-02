import logging

import pandas as pd

LOGGER = logging.getLogger(__name__)


def rename_design_matrix_parameter_columns(parameter_df: pd.DataFrame) -> pd.DataFrame:
    """Given a dataframe of parameters, checks if the DESIGN_MATRIX prefix is present.
    If present assume this is a design matrix run. Return the dataframe with the prefix
    removed. Also do a check if removing the prefix result in any duplicates.
    If duplicates remove those and give a warning.
    """

    if any(col.startswith("DESIGN_MATRIX:") for col in parameter_df.columns):
        original_columns = parameter_df.columns
        stripped_columns = original_columns.str.replace(
            r"^DESIGN_MATRIX:", "", regex=True
        )
        rename_map = {
            old: new
            for old, new in zip(original_columns, stripped_columns)
            if old != new
        }
        conflict_names = set(rename_map.values()) & set(original_columns)
        if conflict_names:
            LOGGER.info(
                "DESIGN_MATRIX run detected, but non design matrix parameters was found."
            )
            LOGGER.info(
                f"The following parameters will be dropped: {sorted(conflict_names)}"
            )
        parameter_df = parameter_df.drop(columns=conflict_names)

        parameter_df = parameter_df.rename(columns=rename_map)
    return parameter_df
