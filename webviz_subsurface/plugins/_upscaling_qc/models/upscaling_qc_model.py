from typing import List, Optional
from pathlib import Path
import json

import pandas as pd

from fmu.tools.rms.upscaling_qc._types import (
    UpscalingQCFiles,
    MetaData,
)


class UpscalingQCModel:
    def __init__(self, model_folder: Path):
        self._well_df = self._load_well_data(model_folder)
        self._bw_df = self._load_bw_data(model_folder)
        self._grid_df = self._load_grid_data(model_folder)
        self._metadata = self._load_metadata(model_folder)
        self._validate_input()
        self._set_selectors_categorical()

    def _load_well_data(self, model_folder: Path) -> pd.DataFrame:
        return pd.read_csv(model_folder / UpscalingQCFiles.WELLS)

    def _load_bw_data(self, model_folder: Path) -> pd.DataFrame:
        return pd.read_csv(model_folder / UpscalingQCFiles.BLOCKEDWELLS)

    def _load_grid_data(self, model_folder: Path) -> pd.DataFrame:
        return pd.read_csv(model_folder / UpscalingQCFiles.GRID)

    def _load_metadata(self, model_folder: Path) -> pd.DataFrame:
        with open(model_folder / UpscalingQCFiles.METADATA, "r") as fp:
            return MetaData(**json.load(fp))

    def _validate_input(self) -> None:
        """Check data for equality"""
        columns = set(self.selectors + self.properties)
        if set(self._well_df.columns) != columns:
            raise KeyError("Well dataframe does not contain expected columns!")
        if set(self._bw_df.columns) != columns:
            raise KeyError("Blocked well dataframe does not contain expected columns!")
        if set(self._grid_df.columns) != columns:
            raise KeyError("Grid dataframe does not contain expected columns!")

        for selector in self.selectors:
            self._check_column_value_equality(selector)

    def _check_column_value_equality(self, column) -> None:
        if (
            not set(self._well_df[column].unique())
            == set(self._bw_df[column].unique())
            == set(self._grid_df[column].unique())
        ):
            raise ValueError(
                f"Data column {column} has different values in dataframes!"
            )

    def _set_selectors_categorical(self) -> None:
        """Selector columns will have few unique values.
        Set to categorical dtype for optimization"""

        for selector in self.selectors:
            self._well_df[selector] = self._well_df[selector].astype("category")
            self._bw_df[selector] = self._bw_df[selector].astype("category")
            self._grid_df[selector] = self._grid_df[selector].astype("category")

    @property
    def selectors(self) -> List[str]:
        """Returns the selector column (discrete filters)"""
        return self._metadata.selectors

    @property
    def properties(self) -> List[str]:
        """Returns the property columns (values for plotting)"""
        return self._metadata.properties

    def get_unique_selector_values(self, selector: str) -> List[str]:
        """Returns the unique values for a given selector.
        Use the blocked well data for lookup as it has the smallest size"""
        if selector not in self.selectors:
            raise KeyError("{selector} is not a valid selector.")
        return list(self._bw_df[selector].unique())

    def get_dataframe(
        self,
        selectors: List[str],
        selector_values: List[str],
        responses: List[str],
        max_points: Optional[int] = None,
        drop_na: bool = True,
    ) -> pd.DataFrame:
        """Creates a dataframe from a subset of selectors and their value,
        and a subset of responses. Optionally a max number of points can
        be given. If any of the data sets have more points after filtering,
        the dataset will be reduced by sampling a size of points equal
        to this number."""
        dfs = []
        for source, df in zip(
            ["Wells", "Blocked wells", "Grid"],
            [self._well_df, self._bw_df, self._grid_df],
        ):
            df = df[selectors + responses]

            for selector, value in zip(selectors, selector_values):
                df = df[df[selector].isin(value)]
            if max_points is not None and df.shape[0] > max_points:
                df = df.sample(max_points)
            df["SOURCE"] = source
            dfs.append(df)

        combined_df = pd.concat(dfs)
        if drop_na:
            combined_df = combined_df.dropna()
        return combined_df
