from typing import Any, List

import pandas as pd
import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.utils import calculate_slider_step
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Filter(SettingsGroupABC):
    # pylint: disable=too-many-arguments
    class Ids:
        # pylint: disable=too-few-public-methods
        # Controls
        CONTROLS = "controls"
        ENSEMBLE = "ensemble"
        RESPONSE = "response"
        CORRELATION_METHOD = "correlation-method"
        RESPONSE_AGGREGATION = "response-aggregation"
        CORRELATION_CUTOFF = "correlation-cutoff"
        MAX_NUMBER_PARAMETERS = "max-number-parameters"
        # Filters
        FILTERS = "filters"
        ZONE = "zone"
        REGION = "region"
        PARAMETERS = "parameters"

    def __init__(
        self,
        response_df: pd.DataFrame,
        ensembles: List[str],
        response_filters: dict,
        parameter_columns: list,
        response_columns: List[str],
        aggregation: str,
        corr_method: str,
        mode: str,
    ) -> None:
        super().__init__(mode)

        self.responsedf = response_df
        self.ensembles = ensembles
        self.response_filters = response_filters
        self.parameter_columns = parameter_columns
        self.response_columns = response_columns
        self.aggregation = aggregation
        self.corr_method = corr_method
        self.mode = mode

    @property
    def filter_layout(self) -> List[Any]:
        """Layout to display selectors for response filters"""
        children = []
        for col_name, col_type in self.response_filters.items():
            domid = self.register_component_unique_id(f"filter-{col_name}")
            values = list(self.responsedf[col_name].unique())
            if col_type == "multi":
                selector = wcc.SelectWithLabel(
                    label=f"{col_name}:",
                    id=domid,
                    options=[{"label": val, "value": val} for val in values],
                    value=values,
                    multi=True,
                    size=min(10, len(values)),
                    collapsible=True,
                )
            elif col_type == "single":
                selector = wcc.Dropdown(
                    label=f"{col_name}:",
                    id=domid,
                    options=[{"label": val, "value": val} for val in values],
                    value=values[-1],
                    multi=False,
                    clearable=False,
                )
            elif col_type == "range":
                selector = make_range_slider(domid, self.responsedf[col_name], col_name)
            else:
                return children
            children.append(selector)

        children.append(
            wcc.SelectWithLabel(
                label="Parameters:",
                id=self.register_component_unique_id(Filter.Ids.PARAMETERS),
                options=[
                    {"label": val, "value": val} for val in self.parameter_columns
                ],
                value=self.parameter_columns,
                multi=True,
                size=min(10, len(self.parameter_columns)),
                collapsible=True,
            )
        )

        return children

    @property
    def control_layout(self) -> List[Any]:
        """Layout to select e.g. iteration and response"""
        max_params = len(self.parameter_columns)
        return [
            wcc.Dropdown(
                label="Ensemble:",
                id=self.register_component_unique_id(Filter.Ids.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self.ensembles],
                clearable=False,
                value=self.ensembles[0],
            ),
            wcc.Dropdown(
                label="Response:",
                id=self.register_component_unique_id(Filter.Ids.RESPONSE),
                options=[{"label": col, "value": col} for col in self.response_columns],
                clearable=False,
                value=self.response_columns[0],
            ),
            wcc.RadioItems(
                label="Correlation method:",
                id=self.register_component_unique_id(Filter.Ids.CORRELATION_METHOD),
                options=[
                    {"label": opt.capitalize(), "value": opt}
                    for opt in ["pearson", "spearman"]
                ],
                vertical=False,
                value=self.corr_method,
            ),
            wcc.RadioItems(
                label="Response aggregation:",
                id=self.register_component_unique_id(Filter.Ids.RESPONSE_AGGREGATION),
                options=[
                    {"label": opt.capitalize(), "value": opt} for opt in ["sum", "mean"]
                ],
                vertical=False,
                value=self.aggregation,
            ),
            html.Div(
                wcc.Slider(
                    label="Correlation cut-off (abs):",
                    id=self.register_component_unique_id(Filter.Ids.CORRELATION_CUTOFF),
                    min=0,
                    max=1,
                    step=0.1,
                    marks={"0": 0, "1": 1},
                    value=0,
                ),
                style={"margin-top": "10px"},
            ),
            html.Div(
                wcc.Slider(
                    label="Max number of parameters:",
                    id=self.register_component_unique_id(
                        Filter.Ids.MAX_NUMBER_PARAMETERS
                    ),
                    min=1,
                    max=max_params,
                    step=1,
                    marks={1: "1", max_params: str(max_params)},
                    value=max_params,
                ),
                style={"marginTop": "10px"},
            ),
        ]

    def layout(self) -> List[Component]:
        if self.mode == "Controls":
            return self.control_layout
        if self.mode == "Filters":
            return self.filter_layout
        else:
            return []


def make_range_slider(domid, values, col_name) -> wcc.RangeSlider:
    try:
        values.apply(pd.to_numeric, errors="raise")
    except ValueError as exc:
        raise ValueError(
            f"Cannot calculate filter range for {col_name}. "
            "Ensure that it is a numerical column."
        ) from exc
    return wcc.RangeSlider(
        label=f"{col_name}:",
        id=domid,
        min=values.min(),
        max=values.max(),
        step=calculate_slider_step(
            min_value=values.min(),
            max_value=values.max(),
            steps=len(list(values.unique())) - 1,
        ),
        value=[values.min(), values.max()],
        marks={
            str(values.min()): {"label": f"{values.min():.2f}"},
            str(values.max()): {"label": f"{values.max():.2f}"},
        },
    )
