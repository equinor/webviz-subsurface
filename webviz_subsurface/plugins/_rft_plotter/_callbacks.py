from typing import Any, Callable, Dict, List, Tuple, Union

import webviz_core_components as wcc
from dash import Dash, Input, Output, State
from dash.exceptions import PreventUpdate

from ._business_logic import RftPlotterDataModel
from ._crossplot_figure import update_crossplot
from ._errorplot_figure import update_errorplot
from ._formation_figure import FormationFigure
from ._map_figure import MapFigure
from ._misfit_figure import update_misfit_plot
from ._processing import filter_frame


def plugin_callbacks(
    app: Dash, get_uuid: Callable, datamodel: RftPlotterDataModel
) -> None:
    @app.callback(
        Output(get_uuid("well"), "value"),
        [
            Input(get_uuid("map"), "clickData"),
        ],
    )
    def _get_clicked_well(click_data: Dict[str, List[Dict[str, Any]]]) -> str:
        if not click_data:
            return datamodel.well_names[0]
        for layer in click_data["points"]:
            try:
                return layer["customdata"]
            except KeyError:
                pass
        raise PreventUpdate

    @app.callback(
        Output(get_uuid("map"), "children"),
        [
            Input(get_uuid("map_ensemble"), "value"),
            Input(get_uuid("map_size"), "value"),
            Input(get_uuid("map_color"), "value"),
            Input(get_uuid("map_date"), "value"),
        ],
    )
    def _update_map(
        ensemble: str, sizeby: str, colorby: str, dates: List[float]
    ) -> Union[str, List[wcc.Graph]]:
        figure = MapFigure(datamodel.ertdatadf, ensemble)
        if datamodel.faultlinesdf is not None:
            figure.add_fault_lines(datamodel.faultlinesdf)
        figure.add_misfit_plot(sizeby, colorby, dates)

        return [
            wcc.Graph(
                style={"height": "84vh"},
                figure={"data": figure.traces, "layout": figure.layout},
            )
        ]

    @app.callback(
        Output(get_uuid("formations-graph-wrapper"), "children"),
        [
            Input(get_uuid("well"), "value"),
            Input(get_uuid("date"), "value"),
            Input(get_uuid("ensemble"), "value"),
            Input(get_uuid("linetype"), "value"),
            Input(get_uuid("depth_option"), "value"),
        ],
    )
    def _update_formation_plot(
        well: str, date: str, ensembles: List[str], linetype: str, depth_option: str
    ) -> Union[str, List[wcc.Graph]]:

        if not ensembles:
            return "No ensembles selected"

        if date not in datamodel.date_in_well(well):
            raise PreventUpdate

        figure = FormationFigure(
            well=well,
            ertdf=datamodel.ertdatadf,
            enscolors=datamodel.enscolors,
            depth_option=depth_option,
            date=date,
            ensembles=ensembles,
            simdf=datamodel.simdf,
            obsdf=datamodel.obsdatadf,
        )

        if datamodel.formations is not None:
            figure.add_formation(datamodel.formationdf)

        figure.add_simulated_lines(linetype)
        figure.add_additional_observations()
        figure.add_ert_observed()

        return [
            wcc.Graph(
                style={"height": "84vh"},
                figure={"data": figure.traces, "layout": figure.layout},
            )
        ]

    @app.callback(
        Output(get_uuid("linetype"), "options"),
        Output(get_uuid("linetype"), "value"),
        Input(get_uuid("depth_option"), "value"),
        State(get_uuid("linetype"), "value"),
        State(get_uuid("well"), "value"),
        State(get_uuid("date"), "value"),
    )
    def _update_linetype(
        depth_option: str,
        current_linetype: str,
        current_well: str,
        current_date: str,
    ) -> Tuple[List[Dict[str, str]], str]:
        if datamodel.simdf is not None:
            df = filter_frame(
                datamodel.simdf,
                {"WELL": current_well, "DATE": current_date},
            )
            if depth_option == "TVD" or (
                depth_option == "MD"
                and "CONMD" in datamodel.simdf
                and len(df["CONMD"].unique()) == len(df["DEPTH"].unique())
            ):

                return [
                    {
                        "label": "Realization lines",
                        "value": "realization",
                    },
                    {
                        "label": "Statistical fanchart",
                        "value": "fanchart",
                    },
                ], current_linetype

        return [
            {
                "label": "Realization lines",
                "value": "realization",
            },
        ], "realization"

    @app.callback(
        [Output(get_uuid("date"), "options"), Output(get_uuid("date"), "value")],
        [
            Input(get_uuid("well"), "value"),
        ],
        [State(get_uuid("date"), "value")],
    )
    def _update_date(well: str, current_date: str) -> Tuple[List[Dict[str, str]], str]:
        dates = datamodel.date_in_well(well)
        available_dates = [{"label": date, "value": date} for date in dates]
        date = current_date if current_date in dates else dates[0]
        return available_dates, date

    @app.callback(
        Output(get_uuid("misfit-graph-wrapper"), "children"),
        [
            Input(get_uuid("well-misfitplot"), "value"),
            Input(get_uuid("zone-misfitplot"), "value"),
            Input(get_uuid("date-misfitplot"), "value"),
            Input(get_uuid("ensemble-misfitplot"), "value"),
        ],
    )
    def _misfit_plot(
        wells: List[str], zones: List[str], dates: List[str], ensembles: List[str]
    ) -> Union[str, List[wcc.Graph]]:
        df = filter_frame(
            datamodel.ertdatadf,
            {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
        )
        if df.empty:
            return "No data matching the given filter criterias"

        return update_misfit_plot(df, datamodel.enscolors)

    @app.callback(
        Output(get_uuid("crossplot-graph-wrapper"), "children"),
        [
            Input(get_uuid("well-crossplot"), "value"),
            Input(get_uuid("zone-crossplot"), "value"),
            Input(get_uuid("date-crossplot"), "value"),
            Input(get_uuid("ensemble-crossplot"), "value"),
            Input(get_uuid("crossplot_size"), "value"),
            Input(get_uuid("crossplot_color"), "value"),
        ],
    )
    def _crossplot(
        wells: List[str],
        zones: List[str],
        dates: List[str],
        ensembles: List[str],
        sizeby: str,
        colorby: str,
    ) -> Union[str, List[wcc.Graph]]:
        df = filter_frame(
            datamodel.ertdatadf,
            {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
        )
        if df.empty:
            return "No data matching the given filter criterias"
        return update_crossplot(df, sizeby, colorby)

    @app.callback(
        Output(get_uuid("errorplot-graph-wrapper"), "children"),
        [
            Input(get_uuid("well-errorplot"), "value"),
            Input(get_uuid("zone-errorplot"), "value"),
            Input(get_uuid("date-errorplot"), "value"),
            Input(get_uuid("ensemble-errorplot"), "value"),
        ],
    )
    def _errorplot(
        wells: List[str], zones: List[str], dates: List[str], ensembles: List[str]
    ) -> Union[str, List[wcc.Graph]]:
        df = filter_frame(
            datamodel.ertdatadf,
            {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
        )
        if df.empty:
            return "No data matching the given filter criterias"
        return [update_errorplot(df, datamodel.enscolors)]
