from itertools import chain
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
from webviz_config.common_cache import CACHE

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._utils.simulation_timeseries import (
    get_simulation_line_shape,
    set_simulation_line_shape_fallback,
)


class SimulationTimeSeriesModel:
    """Class to process and and visualize ensemble timeseries"""

    def __init__(
        self,
        dataframe: pd.DataFrame,
        metadata: Optional[pd.DataFrame] = None,
        line_shape_fallback: str = "linear",
    ) -> None:

        for column in ["ENSEMBLE", "REAL", "DATE"]:
            if column not in dataframe.columns:
                raise KeyError(f"{column} column is missing from UNSMRY data")

        self._dataframe = dataframe
        self._metadata = metadata
        self.line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )

        self._vector_names = SimulationTimeSeriesModel._determine_vector_names(
            self._dataframe, self._metadata
        )
        # Strip out vector names where all data is 0
        self._vector_names = (
            SimulationTimeSeriesModel._filter_vector_names_discard_0_columns(
                self._vector_names, self._dataframe
            )
        )

        self._vector_groups = SimulationTimeSeriesModel._split_vectors_by_type(
            self._vector_names
        )

        self._dates = sorted(self._dataframe["DATE"].unique().astype(str))

        # Currently we cannot be sure what data type the DATE column has.
        # Apparently it will have datetime if the source is SMRY files, but
        # may be of type str if the source is CSV files.
        # Try and detect if the data type is string by sampling the first entry
        sample_date = self._dataframe["DATE"].iloc[0]
        self._date_column_is_str = isinstance(sample_date, str)

    @staticmethod
    def _determine_vector_names(
        dataframe: pd.DataFrame, metadata: Optional[pd.DataFrame]
    ) -> List[str]:
        """Determine which vectors we should make available"""
        vecnames = [
            c
            for c in dataframe.columns
            if c not in ["REAL", "ENSEMBLE", "DATE"]
            and not historical_vector(c, metadata, False) in dataframe.columns
        ]
        return vecnames

    @staticmethod
    def _filter_vector_names_discard_0_columns(
        vector_names: Iterable[str], dataframe: pd.DataFrame
    ) -> List[str]:
        """Filter list of vector names by removing vector names where the data is all zeros"""
        non_zero_column_mask = (dataframe != 0).any(axis=0)
        non_zero_column_names = set(dataframe.columns[non_zero_column_mask])
        filtered_vecnames = [n for n in vector_names if n in non_zero_column_names]
        return filtered_vecnames

    @staticmethod
    def _split_vectors_by_type(vector_names: Iterable[str]) -> Dict[str, dict]:
        vtypes = ["Field", "Well", "Region", "Block", "Group", "Connection"]
        vgroups = {}
        for vtype in vtypes:
            vectors = [v for v in vector_names if v.startswith(vtype[0])]
            if vectors:
                shortnames, items = SimulationTimeSeriesModel._vector_subitems(vectors)
                vgroups[vtype] = dict(
                    vectors=vectors, shortnames=shortnames, items=items
                )

        other_vectors = [
            x
            for x in vector_names
            if x
            not in list(
                chain.from_iterable(
                    [vtype_dict["vectors"] for vtype_dict in vgroups.values()]
                )
            )
        ]
        if other_vectors:
            vgroups["Others"] = dict(
                vectors=other_vectors, shortnames=other_vectors, items=[]
            )
        return vgroups

    @staticmethod
    def _vector_subitems(vectors: Iterable[str]) -> Tuple[List[str], List[str]]:
        shortnames = {v.split(":")[0] for v in vectors}
        items = {":".join(v.split(":")[1:]) for v in vectors if len(v.split(":")) > 1}

        return sorted(shortnames), sorted(
            items, key=int if all(item.isdigit() for item in items) else None
        )

    @property
    def dates(self) -> List[str]:
        return self._dates

    @property
    def vectors(self) -> List[str]:
        return self._vector_names

    @property
    def vector_groups(self) -> Dict[str, dict]:
        return self._vector_groups

    @property
    def ensembles(self) -> List[str]:
        return list(self._dataframe["ENSEMBLE"].unique())

    def get_line_shape(self, vector: str) -> str:
        return get_simulation_line_shape(
            line_shape_fallback=self.line_shape_fallback,
            vector=vector,
            smry_meta=self._metadata,
        )

    def get_ensemble_vectors_for_date(
        self, ensemble: str, date: str, vectors: list = None
    ) -> pd.DataFrame:
        vectors = vectors if vectors is not None else self._vector_names

        # If the data type of the DATE column is string, use the passed date argument
        # directly. Otherwise convert to datetime before doing query
        query_date = date if self._date_column_is_str else pd.to_datetime(date)
        df = self._dataframe.loc[
            (self._dataframe["ENSEMBLE"] == ensemble)
            & (self._dataframe["DATE"] == query_date),
            vectors + ["REAL"],
        ]
        return df

    def _add_history_trace(self, dframe: pd.DataFrame, vector: str) -> dict:
        """Renders the history line"""
        df = dframe.loc[
            (dframe["REAL"] == dframe["REAL"].unique()[0])
            & (dframe["ENSEMBLE"] == dframe["ENSEMBLE"].unique()[0])
        ]
        return {
            "line": {"shape": self.get_line_shape(vector)},
            "x": df["DATE"].astype(str),
            "y": df[vector],
            "hovertext": "History",
            "hoverinfo": "y+x+text",
            "name": "History",
            "marker": {"color": "black"},
            "showlegend": True,
        }

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def add_realization_traces(
        self, ensemble: str, vector: str, real_filter: Optional[list] = None
    ) -> list:
        """Renders line trace for each realization, includes history line if present"""
        dataframe = self._dataframe[self._dataframe["ENSEMBLE"] == ensemble]
        dataframe = (
            dataframe[dataframe["REAL"].isin(real_filter)]
            if real_filter is not None
            else dataframe
        )
        traces = [
            {
                "line": {"shape": self.get_line_shape(vector)},
                "x": list(real_df["DATE"].astype(str)),
                "y": list(real_df[vector]),
                "name": ensemble,
                "customdata": real,
                "legendgroup": ensemble,
                "marker": {"color": "red"},
                "showlegend": real_idx == 0,
            }
            for real_idx, (real, real_df) in enumerate(dataframe.groupby("REAL"))
        ]

        hist_vecname = historical_vector(vector=vector, smry_meta=self._metadata)
        if hist_vecname and hist_vecname in dataframe.columns:
            traces.append(
                self._add_history_trace(
                    dataframe,
                    hist_vecname,
                )
            )

        return traces

    def daterange_for_plot(self, vector: str) -> List[str]:
        date = self._dataframe["DATE"][self._dataframe[vector] != 0]
        return [str(date.min()), str(date.max())]
