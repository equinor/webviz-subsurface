from typing import Dict, List, Optional

from dash import ALL, Input, Output, State, callback, html
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._plugin_ids import PlugInIDs
from .._swatint import SwatinitQcDataModel
from ..settings_groups import CapilarFilters, CapilarSelections
from ..view_elements import CapilarViewelement, MapFigure


class TabMaxPcInfoLayout(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        CAPILAR_TAB = "capilar-tab"
        MAIN_CLOUMN = "main-column"

    def __init__(
        self,
        datamodel: SwatinitQcDataModel,
    ) -> None:
        super().__init__("Capillary pressure scaling")
        self.datamodel = datamodel
        self.selectors = self.datamodel.SELECTORS

        main_column = self.add_column(TabMaxPcInfoLayout.IDs.MAIN_CLOUMN)
        row = main_column.make_row()
        row.add_view_element(
            CapilarViewelement(self.datamodel),
            TabMaxPcInfoLayout.IDs.CAPILAR_TAB,
        )

        self.add_settings_group(CapilarSelections(self.datamodel), PlugInIDs.SettingsGroups.CAPILAR_SELECTORS)
        self.add_settings_group(CapilarFilters(self.datamodel), PlugInIDs.SettingsGroups.CAPILAR_FILTERS)

    def set_callbacks(self) -> None:
        # update map
        @callback(
            Output(
                self.view_element(TabMaxPcInfoLayout.IDs.CAPILAR_TAB)
                .component_unique_id(CapilarViewelement.IDs.MAP)
                .to_string(),
                "figure",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Capilary.EQLNUM),
                "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Capilary.MAX_PC_SCALE),
                "data",
            ),
            Input(
                {
                    "id": self.view_element(TabMaxPcInfoLayout.IDs.CAPILAR_TAB)
                    .component_unique_id(CapilarFilters.IDs.RANGE_FILTERS)
                    .to_string(), # litt usikker på denne...?
                    "col": ALL
                },
                "value",
            ),
            State(
                {
                    "id": self.view_element(TabMaxPcInfoLayout.IDs.CAPILAR_TAB)
                    .component_unique_id(CapilarFilters.IDs.RANGE_FILTERS)
                    .to_string(),
                    "col": ALL
                },
                "id",
            ),
        )
        def _update_map(
            eqlnums: list, 
            threshold: Optional[int], 
            continous_filters: List[List[str]], 
            continous_filters_ids: List[Dict[str, str]]
        ) -> MapFigure:
            df = self.datamodel.get_dataframe(
                filters={"EQLNUM": eqlnums},
                range_filters=zip_filters(continous_filters, continous_filters_ids),
            )
            df_for_map = df[df["PC_SCALING"] >= threshold]
            if threshold is None:
                df_for_map = self.datamodel.resample_dataframe(df, max_points=10000)
            
            return MapFigure(
                dframe=df_for_map,
                color_by="EQLNUM",
                faultlinedf=self.datamodel.faultlines_df,
                colormap=self.datamodel.create_colormap("EQLNUM"),
            ).figure

        # update table
        @callback(
            Output(
                self.view_element(TabMaxPcInfoLayout.IDs.CAPILAR_TAB)
                .component_unique_id(CapilarViewelement.IDs.TABLE)
                .to_string(),
                "columns"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Capilary.MAX_PC_SCALE),
                "data",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Capilary.SPLIT_TABLE_BY),
                "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Capilary.EQLNUM),
                "data"
            ),
            Input(
                {
                    "id": CapilarFilters.IDs.RANGE_FILTERS,
                    "col": ALL
                },
                "value",
            ),
            State(
                {
                    "id": CapilarFilters.IDs.RANGE_FILTERS,
                    "col": ALL
                },
                "id",
            ),
        )
        def _update_table(
            threshold: Optional[list],
            groupby_eqlnum: list,
            eqlnums: list,
            continous_filters: List[List[str]], 
            continous_filters_ids: List[Dict[str, str]]
        ) -> List[dict]:
            df = self.datamodel.get_dataframe(
                filters={"EQLNUM": eqlnums},
                range_filters=zip_filters(continous_filters, continous_filters_ids),
            )
            dframe = self.datamodel.get_max_pc_info_and_percent_for_data_matching_condition(
                dframe=df,
                condition=threshold,
                groupby_eqlnum=groupby_eqlnum == "both",
            )
            text_columns=self.selectors
            columns=[
                {
                    "name": i,
                    "id": i,
                    "type": "numeric" if i not in text_columns else "text",
                    "format": {"specifier": ".4~r"} if i not in text_columns else {},
                }
                for i in dframe.columns
            ]
            return columns


def zip_filters(filter_values: list, filter_ids: list) -> dict:
    print(zip(filter_values, filter_ids))
    return {id_val["col"]: values for values, id_val in zip(filter_values, filter_ids)}
