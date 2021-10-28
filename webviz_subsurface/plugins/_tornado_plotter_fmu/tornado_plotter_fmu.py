import json
from pathlib import Path
from typing import Dict, List

import webviz_core_components as wcc
from dash import ALL, Dash, Input, Output, callback_context, html
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._components.tornado.tornado_widget import TornadoWidget
from webviz_subsurface._datainput.fmu_input import find_sens_type
from webviz_subsurface._providers import EnsembleTableProviderFactory


class TornadoPlotterFMU(WebvizPluginABC):
    """General tornado plotter for FMU data from a csv file of responses.
    ---
    * **`ensemble`:** Which ensemble in `shared_settings` to visualize.
    * **`csvfile`:** Relative ensemble path to csv file with responses
    * **`aggregated_csvfile`:** Alternative to ensemble + csvfile with
    aggregated responses. Requires REAL and ENSEMBLE columns
    * **`aggregated_parameterfile`:** Necessary when aggregated_csvfile
    is specified. File with sensitivity specification for each realization.
    Requires columns REAL, ENSEMBLE, SENSNAME and SENSCASE.
    * **`initial_response`:** Initialize plugin with this response column
    visualized
    * **`single_value_selectors`:** List of columns in response csv file
    that should be used to select/filter data. E.g. for UNSMRY data the DATE
    column can be used. For each entry a Dropdown is shown with all unique
    values and a single value can be selected at a time.
    * **`multi_value_selectors`:** List of columns in response csv file
    to filter/select data. For each entry a Select is shown with
    all unique values. Multiple values can be selected at a time,
    and a tornado plot will be shown from the matching response rows.
    Used e.g. for volumetrics data, to select a subset of ZONES and
    REGIONS.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        csvfile: str = None,
        ensemble: str = None,
        aggregated_csvfile: Path = None,
        aggregated_parameterfile: Path = None,
        initial_response: str = None,
        single_value_selectors: List[str] = None,
        multi_value_selectors: List[str] = None,
    ):
        super().__init__()
        self._single_filters = single_value_selectors if single_value_selectors else []
        self._multi_filters = multi_value_selectors if multi_value_selectors else []
        provider = EnsembleTableProviderFactory.instance()

        if ensemble is not None and csvfile is not None:
            ensemble_dict: Dict[str, str] = {
                ensemble: webviz_settings.shared_settings["scratch_ensembles"][ensemble]
            }
            self._parameterproviderset = (
                provider.create_provider_set_from_per_realization_parameter_file(
                    ensemble_dict
                )
            )
            self._tableproviderset = (
                provider.create_provider_set_from_per_realization_csv_file(
                    ensemble_dict, csvfile
                )
            )
            self._ensemble_name = ensemble
        elif aggregated_csvfile and aggregated_parameterfile is not None:
            self._tableproviderset = (
                provider.create_provider_set_from_aggregated_csv_file(
                    aggregated_csvfile
                )
            )
            self._parameterproviderset = (
                provider.create_provider_set_from_aggregated_csv_file(
                    aggregated_parameterfile
                )
            )
            if len(self._tableproviderset.ensemble_names()) != 1:
                raise ValueError(
                    "Csv file has multiple ensembles. "
                    "This plugin only supports a single ensemble"
                )
            self._ensemble_name = self._tableproviderset.ensemble_names()[0]
        else:
            raise ValueError(
                "Specify either ensembles and csvfile or aggregated_csvfile "
                "and aggregated_parameterfile"
            )

        try:
            design_matrix_df = self._parameterproviderset.ensemble_provider(
                self._ensemble_name
            ).get_column_data(column_names=["SENSNAME", "SENSCASE"])
        except KeyError as exc:
            raise KeyError(
                "Required columns 'SENSNAME' and 'SENSCASE' is missing "
                f"from {self._ensemble_name}. Cannot calculate tornado plots"
            ) from exc
        design_matrix_df["ENSEMBLE"] = self._ensemble_name
        design_matrix_df["SENSTYPE"] = design_matrix_df.apply(
            lambda row: find_sens_type(row.SENSCASE), axis=1
        )
        self._tornado_widget = TornadoWidget(
            realizations=design_matrix_df, app=app, webviz_settings=webviz_settings
        )
        self._responses: List[str] = self._tableproviderset.ensemble_provider(
            self._ensemble_name
        ).column_names()
        if self._single_filters:
            self._responses = [
                response
                for response in self._responses
                if response not in self._single_filters
            ]
        if self._multi_filters:
            self._responses = [
                response
                for response in self._responses
                if response not in self._multi_filters
            ]
        self._initial_response: str = (
            initial_response if initial_response else self._responses[0]
        )
        self.set_callbacks(app)

    @property
    def single_filter_layout(self) -> html.Div:
        """Creates dropdowns for any data columns added as single value filters"""
        elements = []
        for selector in self._single_filters:
            values = (
                self._tableproviderset.ensemble_provider(self._ensemble_name)
                .get_column_data([selector])[selector]
                .unique()
            )
            elements.append(
                wcc.Dropdown(
                    label=selector,
                    id={
                        "id": self.uuid("selectors"),
                        "name": selector,
                        "type": "single_filter",
                    },
                    options=[{"label": val, "value": val} for val in values],
                    value=values[0],
                    clearable=False,
                )
            )
        return html.Div(children=elements)

    @property
    def multi_filter_layout(self) -> html.Div:
        """Creates wcc.Selects for any data columns added as multi value filters"""
        elements = []
        for selector in self._multi_filters:
            values = (
                self._tableproviderset.ensemble_provider(self._ensemble_name)
                .get_column_data([selector])[selector]
                .unique()
            )
            elements.append(
                wcc.SelectWithLabel(
                    label=selector,
                    id={
                        "id": self.uuid("selectors"),
                        "name": selector,
                        "type": "multi_filter",
                    },
                    options=[{"label": val, "value": val} for val in values],
                    value=values,
                    size=min(5, len(values)),
                )
            )
        return html.Div(children=elements)

    @property
    def response_layout(self) -> html.Div:
        """Creates a labelled dropdown with all response columns"""
        return wcc.Dropdown(
            label="Response",
            id=self.uuid("response"),
            options=[
                {"label": response, "value": response} for response in self._responses
            ],
            value=self._initial_response,
            clearable=False,
        )

    @property
    def layout(self) -> html.Div:
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": 1},
                    children=[
                        wcc.Selectors(label="Selectors", children=self.response_layout),
                        wcc.Selectors(
                            label="Filters",
                            children=[
                                self.single_filter_layout,
                                self.multi_filter_layout,
                            ],
                        ),
                    ],
                ),
                wcc.Frame(
                    color="white",
                    highlight=False,
                    style={"flex": 5},
                    children=self._tornado_widget.layout,
                ),
            ]
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self._tornado_widget.storage_id, "data"),
            Input(self.uuid("response"), "value"),
            Input(
                {"id": self.uuid("selectors"), "name": ALL, "type": "single_filter"},
                "value",
            ),
            Input(
                {"id": self.uuid("selectors"), "name": ALL, "type": "multi_filter"},
                "value",
            ),
        )
        def _update_tornado_with_response_values(
            response: str, single_filters: List, multi_filters: List
        ) -> str:
            """Returns a json dump for the tornado plot with the response values per realization"""

            data = self._tableproviderset.ensemble_provider(
                self._ensemble_name
            ).get_column_data([response] + self._single_filters + self._multi_filters)

            # Filter data
            if single_filters is not None:
                for value, input_dict in zip(
                    single_filters, callback_context.inputs_list[1]
                ):
                    data = data.loc[data[input_dict["id"]["name"]] == value]
            if multi_filters is not None:
                for value, input_dict in zip(
                    multi_filters, callback_context.inputs_list[2]
                ):
                    data = data.loc[data[input_dict["id"]["name"]].isin(value)]

            return json.dumps(
                {
                    "ENSEMBLE": self._ensemble_name,
                    "data": data.groupby("REAL")
                    .sum()
                    .reset_index()[["REAL", response]]
                    .values.tolist(),
                    "number_format": "#.4g",
                }
            )
