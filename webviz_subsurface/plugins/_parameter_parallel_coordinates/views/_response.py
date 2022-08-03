from typing import List

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

import webviz_subsurface._utils.parameter_response as parresp

from .._plugin_ids import PluginIds
from ._view_functions import render_parcoord


class ViewSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        RESPONSE_SETTINGS = "response-settings"
        RESPONSE = "response"
        DATE = "date"

    def __init__(
        self, response_columns, response_filters, responsedf: pd.DataFrame
    ) -> None:
        super().__init__("Response Settings")

        self.response_columns = response_columns
        self.response_filters = response_filters
        self.responsedf = responsedf

    def layout(self) -> List[Component]:
        children = [
            wcc.Dropdown(
                label="Response",
                id=self.register_component_unique_id(ViewSettings.Ids.RESPONSE),
                options=[{"label": ens, "value": ens} for ens in self.response_columns],
                clearable=False,
                value=self.response_columns[0],
                style={"marginBottom": "20px"},
            ),
        ]
        if self.response_filters is not None:
            for col_name, col_type in self.response_filters.items():
                values = list(self.responsedf[col_name].unique())
                if col_type == "multi":
                    children.append(
                        wcc.SelectWithLabel(
                            label=col_name,
                            id=self.register_component_unique_id(f"filter-{col_name}"),
                            options=[{"label": val, "value": val} for val in values],
                            value=values,
                            multi=True,
                            size=min(20, len(values)),
                        )
                    )
                elif col_type == "single":
                    children.append(
                        wcc.Dropdown(
                            label=col_name,
                            id=self.register_component_unique_id(ViewSettings.Ids.DATE),
                            options=[{"label": val, "value": val} for val in values],
                            value=values[0],
                            multi=False,
                            clearable=False,
                        )
                    )
        return children


class ResponseView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        RESPONSE_CHART = "response-chart"
        SETTINGS = "settings"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        parallel_df: pd.DataFrame,
        theme: WebvizConfigTheme,
        parameter_columns: List[str],
        ensembles: List[str],
        ens_colormap: List[str],
        response_columns: List[str],
        response_filters: dict,
        responsedf: pd.DataFrame,
        aggregation: str,
    ) -> None:
        super().__init__("Response chart")

        self.parallel_df = parallel_df
        self.parameter_columns = parameter_columns
        self.ensembles = ensembles
        self.ens_colormap = ens_colormap
        self.response_columns = response_columns
        self.response_filters = response_filters
        self.responsedf = responsedf
        self.aggregation = aggregation

        column = self.add_column()
        column.make_row(ResponseView.Ids.RESPONSE_CHART, flex_grow=4)
        self.add_settings_group(
            ViewSettings(self.response_columns, self.response_filters, self.responsedf),
            ResponseView.Ids.SETTINGS,
        )
        self.theme = theme

    @property
    def parcoord_inputs(self):
        inputs = [
            Input(
                self.settings_group(ResponseView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.RESPONSE)
                .to_string(),
                "value",
            ),
        ]
        if self.response_filters is not None:
            inputs.extend(
                [
                    Input(
                        self.settings_group(ResponseView.Ids.SETTINGS)
                        .component_unique_id(ViewSettings.Ids.DATE)
                        .to_string(),
                        "value",
                    )
                ]
            )
        return inputs

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(ResponseView.Ids.RESPONSE_CHART)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLE), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_EXCLUDE_INCLUDE),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_PARAMETERS),
                "data",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.REMOVE_CONSTANT), "data"),
            self.parcoord_inputs,
        )
        def _update_plot(
            ensemble: List[str],
            exclude_include: str,
            parameters: List[str],
            remove_constant: str,
            *opt_args,
        ) -> dict:
            ensemble = ensemble if isinstance(ensemble, list) else [ensemble]
            parameters = parameters if isinstance(parameters, list) else [parameters]
            special_columns = ["ENSEMBLE", "REAL"]
            if exclude_include == "exc":
                parallel_df = self.parallel_df.drop(parameters, axis=1)
            elif exclude_include == "inc":
                parallel_df = self.parallel_df[special_columns + parameters]
            params = [
                param
                for param in parallel_df.columns
                if param not in special_columns and param in self.parameter_columns
            ]
            if len(ensemble) != 1:
                # Need to wait for update of ensemble selector to multi=False
                raise PreventUpdate
            df = parallel_df.loc[self.parallel_df["ENSEMBLE"] == ensemble[0]]
            response = opt_args[0]
            response_filter_values = opt_args[1:] if len(opt_args) > 1 else {}
            filteroptions = parresp.make_response_filters(
                response_filters=self.response_filters,
                response_filter_values=response_filter_values,
            )
            responsedf = parresp.filter_and_sum_responses(
                self.responsedf,
                ensemble[0],
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )

            # Renaming to make it clear in plot.
            responsedf.rename(columns={response: f"Response: {response}"}, inplace=True)
            df = pd.merge(responsedf, df, on=["REAL"]).drop(columns=special_columns)
            df["COLOR"] = df.apply(
                lambda row: self.ensembles.index(ensemble[0]), axis=1
            )
            fig = render_parcoord(
                df,
                self.theme,
                self.ens_colormap,
                "COLOR",
                self.ensembles,
                "response",
                params,
                response,
                remove_constant,
            )
            return wcc.Graph(
                figure=fig,
                style={
                    "transform": "rotate(90deg)",
                    "width": 900,
                    "height": 1100,
                    "margin": {
                        "r": 60,
                        "t": 0,
                    },
                },
            )
