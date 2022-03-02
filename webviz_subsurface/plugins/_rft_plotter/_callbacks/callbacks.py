from typing import Any, Callable, Dict, List, Tuple, Union

import webviz_core_components as wcc
from dash import Dash, Input, Output, State
from dash.exceptions import PreventUpdate

from .._business_logic import RftPlotterDataModel, filter_frame
from .._figures._crossplot_figure import update_crossplot
from .._figures._errorplot_figure import update_errorplot
from .._figures._formation_figure import FormationFigure
from .._figures._map_figure import MapFigure
from .._figures._misfit_figure import update_misfit_plot
from .._layout import LayoutElements


def plugin_callbacks(
    app: Dash, get_uuid: Callable, datamodel: RftPlotterDataModel
) -> None:
    @app.callback(
        Output(get_uuid(LayoutElements.FORMATIONS_WELL), "value"),
        Input(get_uuid(LayoutElements.MAP_GRAPH), "clickData"),
        State(get_uuid(LayoutElements.FORMATIONS_WELL), "value"),
    )
    def _get_clicked_well(
        click_data: Dict[str, List[Dict[str, Any]]], well: str
    ) -> str:
        if not click_data:
            return well
        for layer in click_data["points"]:
            try:
                return layer["customdata"]
            except KeyError:
                pass
        raise PreventUpdate

    @app.callback(
        Output(get_uuid(LayoutElements.MAP), "children"),
        Input(get_uuid(LayoutElements.MAP_ENSEMBLE), "value"),
        Input(get_uuid(LayoutElements.MAP_SIZE_BY), "value"),
        Input(get_uuid(LayoutElements.MAP_COLOR_BY), "value"),
        Input(get_uuid(LayoutElements.MAP_DATE_RANGE), "value"),
        Input(get_uuid(LayoutElements.MAP_ZONES), "value"),
    )
    def _update_map(
        ensemble: str, sizeby: str, colorby: str, dates: List[float], zones: List[str]
    ) -> Union[str, List[wcc.Graph]]:
        figure = MapFigure(datamodel.ertdatadf, ensemble, zones)
        if datamodel.faultlinesdf is not None:
            figure.add_fault_lines(datamodel.faultlinesdf)
        figure.add_misfit_plot(sizeby, colorby, dates)

        return [
            wcc.Graph(
                style={"height": "84vh"},
                figure={"data": figure.traces, "layout": figure.layout},
                id=get_uuid(LayoutElements.MAP_GRAPH),
            )
        ]

    @app.callback(
        Output(get_uuid(LayoutElements.FORMATIONS_GRAPH), "children"),
        Input(get_uuid(LayoutElements.FORMATIONS_WELL), "value"),
        Input(get_uuid(LayoutElements.FORMATIONS_DATE), "value"),
        Input(get_uuid(LayoutElements.FORMATIONS_ENSEMBLE), "value"),
        Input(get_uuid(LayoutElements.FORMATIONS_LINETYPE), "value"),
        Input(get_uuid(LayoutElements.FORMATIONS_DEPTHOPTION), "value"),
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
        if figure.ertdf.empty:
            return ["No data matching the given filter criterias."]

        if datamodel.formations is not None:
            figure.add_formation(datamodel.formationdf)

        figure.add_simulated_lines(linetype)
        figure.add_additional_observations()
        figure.add_ert_observed()

        return [
            wcc.Graph(
                style={"height": "84vh"},
                figure=figure.figure,
            )
        ]

    @app.callback(
        Output(get_uuid(LayoutElements.FORMATIONS_LINETYPE), "options"),
        Output(get_uuid(LayoutElements.FORMATIONS_LINETYPE), "value"),
        Input(get_uuid(LayoutElements.FORMATIONS_DEPTHOPTION), "value"),
        State(get_uuid(LayoutElements.FORMATIONS_LINETYPE), "value"),
        State(get_uuid(LayoutElements.FORMATIONS_WELL), "value"),
        State(get_uuid(LayoutElements.FORMATIONS_DATE), "value"),
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
        Output(get_uuid(LayoutElements.FORMATIONS_DATE), "options"),
        Output(get_uuid(LayoutElements.FORMATIONS_DATE), "value"),
        Input(get_uuid(LayoutElements.FORMATIONS_WELL), "value"),
        State(get_uuid(LayoutElements.FORMATIONS_DATE), "value"),
    )
    def _update_date(well: str, current_date: str) -> Tuple[List[Dict[str, str]], str]:
        dates = datamodel.date_in_well(well)
        available_dates = [{"label": date, "value": date} for date in dates]
        date = current_date if current_date in dates else dates[0]
        return available_dates, date

    @app.callback(
        Output(get_uuid(LayoutElements.MISFITPLOT_GRAPH), "children"),
        Input(get_uuid(LayoutElements.FILTER_WELLS["misfitplot"]), "value"),
        Input(get_uuid(LayoutElements.FILTER_ZONES["misfitplot"]), "value"),
        Input(get_uuid(LayoutElements.FILTER_DATES["misfitplot"]), "value"),
        Input(get_uuid(LayoutElements.FILTER_ENSEMBLES["misfitplot"]), "value"),
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
        Output(get_uuid(LayoutElements.CROSSPLOT_GRAPH), "children"),
        Input(get_uuid(LayoutElements.FILTER_WELLS["crossplot"]), "value"),
        Input(get_uuid(LayoutElements.FILTER_ZONES["crossplot"]), "value"),
        Input(get_uuid(LayoutElements.FILTER_DATES["crossplot"]), "value"),
        Input(get_uuid(LayoutElements.FILTER_ENSEMBLES["crossplot"]), "value"),
        Input(get_uuid(LayoutElements.CROSSPLOT_SIZE_BY), "value"),
        Input(get_uuid(LayoutElements.CROSSPLOT_COLOR_BY), "value"),
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
        Output(get_uuid(LayoutElements.ERRORPLOT_GRAPH), "children"),
        Input(get_uuid(LayoutElements.FILTER_WELLS["errorplot"]), "value"),
        Input(get_uuid(LayoutElements.FILTER_ZONES["errorplot"]), "value"),
        Input(get_uuid(LayoutElements.FILTER_DATES["errorplot"]), "value"),
        Input(get_uuid(LayoutElements.FILTER_ENSEMBLES["errorplot"]), "value"),
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
