from pathlib import Path
from typing import List, Optional, Tuple

import webviz_core_components as wcc
from webviz_config import WebvizPluginABC, WebvizSettings

from ._error import error
from ._plugin_ids import PlugInIDs
from ._swatint import SwatinitQcDataModel
from .views import OverviewTabLayout, TabMaxPcInfoLayout, TabQqPlotLayout


class SwatinitQC(WebvizPluginABC):
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        csvfile: str = "share/results/tables/check_swatinit.csv",
        ensemble: Optional[str] = None,
        realization: Optional[int] = None,
        faultlines: Path = None,
    ) -> None:
        super().__init__()

        self._datamodel = SwatinitQcDataModel(
            webviz_settings=webviz_settings,
            csvfile=csvfile,
            ensemble=ensemble,
            realization=realization,
            faultlines=faultlines,
        )
        self.error_message = ""

        # Stores used in Overview tab
        self.add_store(
            PlugInIDs.Stores.Overview.BUTTON, WebvizPluginABC.StorageType.SESSION
        )

        # Stores used in Water tab
        self.add_store(
            PlugInIDs.Stores.Water.QC_VIZ, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.EQLNUM, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.COLOR_BY, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.MAX_POINTS, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.QC_FLAG, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.SATNUM, WebvizPluginABC.StorageType.SESSION
        )

        # Stores used in Capilaty tab
        self.add_store(
            PlugInIDs.Stores.Capilary.SPLIT_TABLE_BY,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PlugInIDs.Stores.Capilary.MAX_PC_SCALE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Capilary.EQLNUM, WebvizPluginABC.StorageType.SESSION
        )

        self.add_view(
            OverviewTabLayout(self._datamodel),
            PlugInIDs.SwatinitViews.OVERVIEW,
            PlugInIDs.SwatinitViews.GROUP_NAME,
        )
        """self.add_view(
            TabQqPlotLayout(self._datamodel),
            PlugInIDs.SwatinitViews.WATER,
            PlugInIDs.SwatinitViews.GROUP_NAME
        )"""
        self.add_view(
            TabMaxPcInfoLayout(self._datamodel),
            PlugInIDs.SwatinitViews.WATER,
            PlugInIDs.SwatinitViews.GROUP_NAME
        )

    @property
    def layout(self) -> wcc.Tabs:
        return error(self.error_message)
"""
    def add_webvizstore(self) -> List[Tuple[Callable, List[dict]]]:
        return self._datamodel.webviz_store




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


"""