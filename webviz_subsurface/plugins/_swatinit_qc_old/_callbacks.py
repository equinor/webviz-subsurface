from typing import Callable, Dict, List, Optional, Union

from dash import ALL, Input, Output, State, callback, callback_context
from dash.exceptions import PreventUpdate

from ._business_logic import SwatinitQcDataModel
from ._figures import MapFigure, PropertiesVsDepthSubplots, WaterfallPlot
from ._layout import LayoutElements, TabMaxPcInfoLayout, TabQqPlotLayout, Tabs


def plugin_callbacks(get_uuid: Callable, datamodel: SwatinitQcDataModel) -> None:
    qc_plot_layout = TabQqPlotLayout(get_uuid, datamodel)
    table_layout = TabMaxPcInfoLayout(get_uuid, datamodel)

    @callback(
        Output(get_uuid(LayoutElements.PLOT_WRAPPER), "children"),
        Input(get_uuid(LayoutElements.SELECTED_TAB), "value"),
        Input(get_uuid(LayoutElements.PLOT_EQLNUM_SELECTOR), "value"),
        Input({"id": get_uuid(LayoutElements.FILTERS_DISCRETE), "col": ALL}, "value"),
        Input({"id": get_uuid(LayoutElements.FILTERS_CONTINOUS), "col": ALL}, "value"),
        Input(get_uuid(LayoutElements.COLOR_BY), "value"),
        Input(get_uuid(LayoutElements.MAX_POINTS), "value"),
        Input(get_uuid(LayoutElements.PLOT_SELECTOR), "value"),
        State({"id": get_uuid(LayoutElements.FILTERS_DISCRETE), "col": ALL}, "id"),
        State({"id": get_uuid(LayoutElements.FILTERS_CONTINOUS), "col": ALL}, "id"),
    )
    # pylint: disable=too-many-arguments
    def _update_plot(
        tab_selected: str,
        eqlnums: List[str],
        dicrete_filters: List[List[str]],
        continous_filters: List[List[str]],
        color_by: str,
        max_points: int,
        plot_selector: str,
        dicrete_filters_ids: List[Dict[str, str]],
        continous_filters_ids: List[Dict[str, str]],
    ) -> list:

        if tab_selected != Tabs.QC_PLOTS or max_points is None:
            raise PreventUpdate

        filters = zip_filters(dicrete_filters, dicrete_filters_ids)
        filters.update({"EQLNUM": eqlnums})

        df = datamodel.get_dataframe(
            filters=filters,
            range_filters=zip_filters(continous_filters, continous_filters_ids),
        )
        if df.empty:
            return ["No data left after filtering"]

        qc_volumes = datamodel.compute_qc_volumes(df)

        df = datamodel.filter_dframe_on_depth(df)
        df = datamodel.resample_dataframe(df, max_points=max_points)

        colormap = datamodel.create_colormap(color_by)
        main_plot = (
            WaterfallPlot(qc_vols=qc_volumes).figure
            if plot_selector == qc_plot_layout.MainPlots.WATERFALL
            else PropertiesVsDepthSubplots(
                dframe=df,
                color_by=color_by,
                colormap=colormap,
                discrete_color=color_by in datamodel.SELECTORS,
            ).figure
        )
        map_figure = MapFigure(
            dframe=df,
            color_by=color_by,
            faultlinedf=datamodel.faultlines_df,
            colormap=colormap,
        ).figure

        return qc_plot_layout.main_layout(
            main_figure=main_plot,
            map_figure=map_figure,
            qc_volumes=qc_volumes,
        )

    @callback(
        Output(get_uuid(LayoutElements.MAIN_FIGURE), "figure"),
        Output(get_uuid(LayoutElements.MAP_FIGURE), "figure"),
        Input(get_uuid(LayoutElements.MAIN_FIGURE), "selectedData"),
        Input(get_uuid(LayoutElements.MAP_FIGURE), "selectedData"),
        State(get_uuid(LayoutElements.MAIN_FIGURE), "figure"),
        State(get_uuid(LayoutElements.MAP_FIGURE), "figure"),
    )
    def _update_selected_points_in_figures(
        selected_data: dict, selected_data_map: dict, mainfig: dict, mapfig: dict
    ) -> tuple:
        ctx = callback_context.triggered[0]["prop_id"]

        selected = (
            selected_data_map if LayoutElements.MAP_FIGURE in ctx else selected_data
        )
        point_indexes = get_point_indexes_from_selected(selected)

        for trace in mainfig["data"]:
            update_selected_points_in_trace(trace, point_indexes)
        for trace in mapfig["data"]:
            update_selected_points_in_trace(trace, point_indexes)

        return mainfig, mapfig

    def get_point_indexes_from_selected(selected: Optional[dict]) -> Union[list, dict]:
        if not (isinstance(selected, dict) and "points" in selected):
            return []

        continous_color = "marker.color" in selected["points"][0]
        if continous_color:
            return [point["pointNumber"] for point in selected["points"]]

        point_indexes: dict = {}
        for point in selected["points"]:
            trace_name = str(point["customdata"][0])
            if trace_name not in point_indexes:
                point_indexes[trace_name] = []
            point_indexes[trace_name].append(point["pointNumber"])
        return point_indexes

    def update_selected_points_in_trace(
        trace: dict, point_indexes: Union[dict, list]
    ) -> None:
        if "name" in trace:
            selectedpoints = (
                point_indexes
                if isinstance(point_indexes, list)
                else point_indexes.get(trace["name"], [])
            )
            trace.update(selectedpoints=selectedpoints if point_indexes else None)

    @callback(
        Output(get_uuid(LayoutElements.TABLE_WRAPPER), "children"),
        Input(get_uuid(LayoutElements.SELECTED_TAB), "value"),
        Input(get_uuid(LayoutElements.TABLE_EQLNUM_SELECTOR), "value"),
        Input(get_uuid(LayoutElements.HIGHLIGHT_ABOVE), "value"),
        Input(get_uuid(LayoutElements.GROUPBY_EQLNUM), "value"),
        Input(
            {"id": get_uuid(LayoutElements.FILTERS_CONTINOUS_MAX_PC), "col": ALL},
            "value",
        ),
        State(
            {"id": get_uuid(LayoutElements.FILTERS_CONTINOUS_MAX_PC), "col": ALL}, "id"
        ),
    )
    def _update_capillary_pressure_tab_layout(
        tab_selected: str,
        eqlnums: list,
        threshold: Optional[int],
        groupby_eqlnum: list,
        continous_filters: List[List[str]],
        continous_filters_ids: List[Dict[str, str]],
    ) -> str:
        if tab_selected != Tabs.MAX_PC_SCALING:
            raise PreventUpdate

        df = datamodel.get_dataframe(
            filters={"EQLNUM": eqlnums},
            range_filters=zip_filters(continous_filters, continous_filters_ids),
        )
        df_for_map = df[df["PC_SCALING"] >= threshold]
        if threshold is None:
            df_for_map = datamodel.resample_dataframe(df, max_points=10000)

        map_figure = MapFigure(
            dframe=df_for_map,
            color_by="EQLNUM",
            faultlinedf=datamodel.faultlines_df,
            colormap=datamodel.create_colormap("EQLNUM"),
        ).figure
        df = datamodel.get_max_pc_info_and_percent_for_data_matching_condition(
            dframe=df,
            condition=threshold,
            groupby_eqlnum=groupby_eqlnum == "both",
        )
        return table_layout.main_layout(
            dframe=df,
            selectors=datamodel.SELECTORS,
            map_figure=map_figure,
        )

    @callback(
        Output(get_uuid("info-dialog"), "open"),
        Input(get_uuid("info-button"), "n_clicks"),
        State(get_uuid("info-dialog"), "open"),
    )
    def open_close_information_dialog(_n_click: list, is_open: bool) -> bool:
        if _n_click is not None:
            return not is_open
        raise PreventUpdate


def zip_filters(filter_values: list, filter_ids: list) -> dict:
    return {id_val["col"]: values for values, id_val in zip(filter_values, filter_ids)}
