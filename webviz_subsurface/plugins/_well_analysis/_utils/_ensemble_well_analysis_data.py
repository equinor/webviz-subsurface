import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd

from webviz_subsurface._models import GruptreeModel, WellAttributesModel
from webviz_subsurface._providers import EnsembleSummaryProvider

from .._types import NodeType, PressurePlotMode


class EnsembleWellAnalysisData:
    """This class holds the summary data provider."""

    def __init__(
        self,
        ensemble_name: str,
        provider: EnsembleSummaryProvider,
        gruptree_model: GruptreeModel,
        well_attributes_model: WellAttributesModel,
        filter_out_startswith: Optional[str] = None,
    ):
        self._ensemble_name = ensemble_name
        self._gruptree_model = gruptree_model
        self._well_attributes_model = well_attributes_model
        self._provider = provider
        self._vector_names = self._provider.vector_names()
        self._realizations = self._provider.realizations()
        self._wells: List[str] = [
            vec.split(":")[1] for vec in self._vector_names if vec.startswith("WOPT:")
        ]
        if filter_out_startswith is not None:
            self._wells = [
                well
                for well in self._wells
                if not well.startswith(filter_out_startswith)
            ]

        well_sumvecs = [vec for vec in self._vector_names if vec.startswith("W")]
        group_sumvecs = [vec for vec in self._vector_names if vec.startswith("GPR:")]
        self._smry = provider.get_vectors_df(well_sumvecs + group_sumvecs, None)

    @property
    def webviz_store(self) -> List[Tuple[Callable, List[Dict]]]:
        return [
            self._gruptree_model.webviz_store,
            self._well_attributes_model.webviz_store,
        ]

    @property
    def summary_data(self) -> pd.DataFrame:
        return self._smry

    @property
    def dates(self) -> List[datetime.datetime]:
        return list(self._smry["DATE"].unique())

    @property
    def realizations(self) -> List[int]:
        return self._realizations

    @property
    def wells(self) -> List[str]:
        return self._wells

    @property
    def well_attributes(self) -> pd.DataFrame:
        return self._well_attributes_model.category_dict

    def filter_on_well_attributes(
        self, well_attributes_filter: Dict[str, List[str]]
    ) -> Set[str]:
        """Filters wells based on the input well attributes filter.

        The input parameter well_attribute_filter has the form:
        {
            "welltype":["oil_producer", "water_injector", ...],
            "category2": ...
        }

        Any categories in the filter than does not exist in the ensemble
        well attributes will be ignored. If no categories match, then all
        wells is returned.
        """
        well_attr_df = self._well_attributes_model.dataframe_melted.fillna("Undefined")
        filtered_wells = set(self._wells)
        for category, values in well_attributes_filter.items():
            if category in self._well_attributes_model.categories:
                df = well_attr_df[
                    (well_attr_df["CATEGORY"] == category)
                    & (well_attr_df["VALUE"].isin(values))
                ]
                filtered_wells = filtered_wells.intersection(set(df["WELL"].unique()))
        return filtered_wells

    def get_summary_data(
        self,
        well_sumvec: str,
        prod_from_date: Union[datetime.datetime, None],
        prod_until_date: Union[datetime.datetime, None],
    ) -> pd.DataFrame:
        """Returns all summary data matching the well_sumvec. If the prod_from_date
        is not None it will return all dates after that date and subtract the cumulative
        production at that date. If prod_until_dates is not None it will filter out all
        dates after that date.
        """
        sumvecs = [f"{well_sumvec}:{well}" for well in self._wells]
        df = self._smry[["REAL", "DATE"] + sumvecs]
        max_date = df["DATE"].max()
        min_date = df["DATE"].min()

        if prod_from_date is not None:
            df = df[df["DATE"] >= prod_from_date]

            # If the prod_from_date exists in the ensemble, subtract the
            # production at that date from all dates.
            if min_date <= prod_from_date <= max_date:
                df_date = df[df["DATE"] == prod_from_date].copy()
                df_merged = df.merge(df_date, on=["REAL"], how="inner")
                for vec in sumvecs:
                    df_merged[vec] = df_merged[f"{vec}_x"] - df_merged[f"{vec}_y"]
                df = df_merged[["REAL", "DATE_x"] + sumvecs].rename(
                    {"DATE_x": "DATE"}, axis=1
                )

        if prod_until_date is not None:
            df = df[df["DATE"] <= prod_until_date]

        return df

    def get_dataframe_melted(
        self,
        well_sumvec: str,
        prod_from_date: Union[datetime.datetime, None],
        prod_until_date: Union[datetime.datetime, None],
    ) -> pd.DataFrame:
        """Returns a dataframe on long form consisting of these columns:
        * WELL
        * well_sumvec (f.ex WOPT)
        * ENSEMBLE
        """
        sumvecs = [f"{well_sumvec}:{well}" for well in self._wells]
        df = self._smry[["REAL", "DATE"] + sumvecs]
        max_date = df["DATE"].max()
        min_date = df["DATE"].min()

        if prod_until_date is None:
            prod_until_date = max_date
        else:
            # Set prod_until_date to min_date or max_date if it is outside the
            # ensemble date range
            prod_until_date = max(min(prod_until_date, max_date), min_date)

        df = df[df["DATE"] == prod_until_date]

        # If prod_from_date is None, do nothing
        if prod_from_date is not None:
            # Set prod_from_date to min_date or max_date if it is outside the
            # ensemble date range
            prod_from_date = max(min(prod_from_date, max_date), min_date)

            # Subtract the production at the prod_from_date
            df_date = self._smry[["REAL", "DATE"] + sumvecs]
            df_date = df_date[df_date["DATE"] >= prod_from_date]
            df_date = df_date[df_date["DATE"] == df_date["DATE"].min()]
            df_merged = df.merge(df_date, on=["REAL"], how="inner")
            for vec in sumvecs:
                df_merged[vec] = df_merged[f"{vec}_x"] - df_merged[f"{vec}_y"]
            df = df_merged[["REAL"] + sumvecs]

        df_melted = pd.melt(
            df, value_vars=sumvecs, var_name="WELL", value_name=well_sumvec
        )
        df_melted["WELL"] = df_melted.agg(
            lambda x: f"{x['WELL'].split(':')[1]}", axis=1
        )
        df_melted["ENSEMBLE"] = self._ensemble_name
        return df_melted

    def get_node_info(
        self,
        node: str,
        pressure_plot_mode: PressurePlotMode,
        real: int,
        node_type: NodeType = NodeType.WELL,
    ) -> Dict[str, Any]:
        """Returns a list of dictionaries containing the network nodes
        ending in the input node, with from_date and end_date. If end_date
        is None it means that the network is valid for the rest of the
        simulations.
        Dict[str, Any]
        The output has the form:
        {
            "name": "A1",
            "type: "well",
            "ctrlmode_sumvec": "WMCTL:A1",
            "networks: [
                {
                    "start_date": "2018-01-01",
                    "end_date": "2018-05-01",
                    "nodes": [
                        {
                            "name": "A1",
                            "label": "THP"
                            "pressure_sumvec": "WTHP:A1"
                            "type": "well"
                        },
                        ...
                    ],
                },
                ...
            ]
        }
        """

        gruptree_df = self._gruptree_model.dataframe

        if gruptree_df.empty or (
            pressure_plot_mode == PressurePlotMode.MEAN
            and not self._gruptree_model.gruptrees_are_equal_over_reals
        ):
            # If there is no gruptree OR
            # the plot mode is MEAN and the gruptrees are different over
            # realization, we return only data for the current node.
            nodes = [_get_node_field(node_type, node)]
            if node_type == NodeType.WELL:
                nodes.append(_get_node_field(NodeType.WELL_BH, node))
            return {
                "name": node,
                "type": node_type.value,
                "ctrlmode_sumvec": _get_ctrlmode_sumvec(node_type, node),
                "networks": [
                    {
                        "start_date": self._smry["DATE"].min(),
                        "end_date": None,
                        "nodes": nodes,
                    }
                ],
            }

        if (
            pressure_plot_mode == PressurePlotMode.SINGLE_REAL
            and not self._gruptree_model.gruptrees_are_equal_over_reals
        ):
            # If the plot mode is SINGLE_REAL and gruptrees are
            # different over realizations, then we need to filter
            # the gruptree dataframe on realization
            gruptree_df = gruptree_df[gruptree_df["REAL"] == real]

        node_networks: List[Dict[str, Any]] = []
        prev_nodelist: List[Dict[str, Any]] = []
        for date, df in gruptree_df.groupby("DATE"):
            nodelist = _get_nodelist(df, node_type, node)
            remaining_dates = gruptree_df[gruptree_df["DATE"] > date].DATE
            if remaining_dates.empty:
                next_date = None
            else:
                next_date = remaining_dates.min()

            if nodelist != prev_nodelist:
                node_networks.append(
                    {"start_date": date, "end_date": next_date, "nodes": nodelist}
                )
                prev_nodelist = nodelist
            else:
                if node_networks:
                    node_networks[-1]["end_date"] = next_date
        return {
            "name": node,
            "type": node_type.value,
            "ctrlmode_sumvec": _get_ctrlmode_sumvec(node_type, node),
            "networks": node_networks,
        }


def _get_nodelist(
    df: pd.DataFrame, node_type: NodeType, node: str
) -> List[Dict[str, str]]:
    """Returns a list of node dictionaries ending up in the input
    node. The input dataframe has only one date.

    The function is recursively getting all the nodes ending up in
    the node which the function was called from the outside.

    For wells, both THP and BHP nodes are added
    """
    if node == "FIELD":
        return [_get_node_field(node_type, node)]

    child_row = df[df.CHILD == node]

    if child_row.empty:
        return []
    if child_row.shape[0] > 1:
        raise ValueError(
            f"There can be maximum one row per child per date: {child_row}"
        )
    if is_terminal_node(node, child_row):
        return [_get_node_field(NodeType.GROUP, node)]
    parent = child_row.PARENT.values[0]
    nodelist = [_get_node_field(node_type, node)]
    if node_type == NodeType.WELL:
        nodelist.append(_get_node_field(NodeType.WELL_BH, node))
    return nodelist + _get_nodelist(df, NodeType.GROUP, parent)


def is_terminal_node(node: str, row: pd.Series) -> bool:
    """Checks if the input node is a terminal node in the network.
    FIELD is always a terminal node, but other nodes are terminal if they
    have a value in the TERMINAL_PRESSURE column.
    """
    if node == "FIELD":
        return True
    if (
        "TERMINAL_PRESSURE" in row
        and row["TERMINAL_PRESSURE"].values[0] is not None
        and not np.isnan(row["TERMINAL_PRESSURE"].values[0])
    ):
        return True
    return False


def _get_node_field(node_type: NodeType, node: str) -> Dict[str, str]:
    """Returns a dictionary with info about a single node:
    * Name
    * Label to be used in pressure plot
    * Type: well, well-bh, group or terminal-node
    """
    if node_type == NodeType.GROUP:
        return {
            "name": node,
            "label": node,
            "type": node_type,
            "pressure": f"GPR:{node}",
        }
    if node_type == NodeType.WELL:
        return {
            "name": node,
            "label": "THP",
            "type": node_type,
            "pressure": f"WTHP:{node}",
        }
    if node_type == NodeType.WELL_BH:
        return {
            "name": node,
            "label": "BHP",
            "type": node_type,
            "pressure": f"WBHP:{node}",
        }
    raise ValueError(f"Node type {node_type} not implemented.")


def _get_ctrlmode_sumvec(node_type: NodeType, node: str) -> str:
    """Returns the control mode sumvec for a given node type
    and node name. Only production network implemented so far.
    """
    if node == "FIELD":
        return "FMCTP"
    if node_type == NodeType.WELL:
        return f"WMCTL:{node}"
    if node_type == NodeType.GROUP:
        return f"GMCTP:{node}"
    raise ValueError(f"Node type {node_type} not implemented")
