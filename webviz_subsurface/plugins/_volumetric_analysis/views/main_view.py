from typing import Callable, Optional

import pandas as pd
import webviz_core_components as wcc
from dash import dcc
from webviz_config import WebvizConfigTheme

from webviz_subsurface._models import InplaceVolumesModel

from .comparison_layout import comparison_main_layout, comparison_selections
from .distribution_main_layout import distributions_main_layout, table_main_layout
from .filter_view import filter_layout
from .fipfile_qc_layout import (
    fipfile_qc_filters,
    fipfile_qc_main_layout,
    fipfile_qc_selections,
)
from .selections_view import selections_layout, table_selections_layout
from .tornado_view import tornado_main_layout, tornado_selections_layout


def main_view(
    get_uuid: Callable,
    volumemodel: InplaceVolumesModel,
    theme: WebvizConfigTheme,
    disjoint_set_df: Optional[pd.DataFrame] = None,
) -> dcc.Tabs:

    tabs = []
    tabs.append(
        wcc.Tab(
            label="Inplace distributions",
            value="voldist",
            children=tab_view_layout(
                main_layout=distributions_main_layout(uuid=get_uuid("main-voldist")),
                sidebar_layout=[
                    selections_layout(
                        uuid=get_uuid("selections"),
                        tab="voldist",
                        volumemodel=volumemodel,
                        theme=theme,
                    ),
                    filter_layout(
                        uuid=get_uuid("filters"), tab="voldist", volumemodel=volumemodel
                    ),
                ],
            ),
        )
    )
    tabs.append(
        wcc.Tab(
            label="Tables",
            value="table",
            children=tab_view_layout(
                main_layout=table_main_layout(
                    uuid=get_uuid("main-table"),
                ),
                sidebar_layout=[
                    table_selections_layout(
                        uuid=get_uuid("selections"),
                        tab="table",
                        volumemodel=volumemodel,
                    ),
                    filter_layout(
                        uuid=get_uuid("filters"), tab="table", volumemodel=volumemodel
                    ),
                ],
            ),
        )
    )
    if volumemodel.sensrun:
        tabs.append(
            wcc.Tab(
                label="Tornadoplots",
                value="tornado",
                children=tab_view_layout(
                    main_layout=tornado_main_layout(
                        uuid=get_uuid("main-tornado"),
                    ),
                    sidebar_layout=[
                        tornado_selections_layout(
                            uuid=get_uuid("selections"),
                            tab="tornado",
                            volumemodel=volumemodel,
                        ),
                        filter_layout(
                            uuid=get_uuid("filters"),
                            tab="tornado",
                            volumemodel=volumemodel,
                            hide_selectors=["SENSNAME_CASE"],
                        ),
                    ],
                ),
            )
        )
    if len(volumemodel.sources) > 1:
        tabs.append(
            wcc.Tab(
                label="Source comparison",
                value="src-comp",
                children=tab_view_layout(
                    main_layout=comparison_main_layout(get_uuid("main-src-comp")),
                    sidebar_layout=[
                        comparison_selections(
                            uuid=get_uuid("selections"),
                            tab="src-comp",
                            volumemodel=volumemodel,
                            compare_on="Source",
                        ),
                        filter_layout(
                            uuid=get_uuid("filters"),
                            tab="src-comp",
                            volumemodel=volumemodel,
                            hide_selectors=["SOURCE", "FLUID_ZONE"],
                        ),
                    ],
                ),
            )
        )
    if len(volumemodel.ensembles) > 1 or volumemodel.sensrun:
        compare_on = "Ensemble" if len(volumemodel.ensembles) > 1 else "Sensitivity"
        tabs.append(
            wcc.Tab(
                label=f"{compare_on} comparison",
                value="ens-comp",
                children=tab_view_layout(
                    main_layout=comparison_main_layout(get_uuid("main-ens-comp")),
                    sidebar_layout=[
                        comparison_selections(
                            uuid=get_uuid("selections"),
                            tab="ens-comp",
                            volumemodel=volumemodel,
                            compare_on=compare_on,
                        ),
                        filter_layout(
                            uuid=get_uuid("filters"),
                            tab="ens-comp",
                            volumemodel=volumemodel,
                            hide_selectors=["ENSEMBLE", "FLUID_ZONE", "SENSNAME_CASE"],
                        ),
                    ],
                ),
            )
        )
    if disjoint_set_df is not None:
        tabs.append(
            wcc.Tab(
                label="Fipfile QC",
                value="fipqc",
                children=tab_view_layout(
                    main_layout=fipfile_qc_main_layout(get_uuid("main-fipqc")),
                    sidebar_layout=[
                        fipfile_qc_selections(uuid=get_uuid("selections"), tab="fipqc"),
                        fipfile_qc_filters(
                            uuid=get_uuid("filters"),
                            tab="fipqc",
                            disjoint_set_df=disjoint_set_df,
                        ),
                    ],
                ),
            )
        )

    initial_tab = "voldist"
    if volumemodel.volume_type == "mixed":
        initial_tab = "src-comp"
    elif volumemodel.sensrun:
        initial_tab = "tornado"

    return wcc.Tabs(
        id=get_uuid("tabs"),
        value=initial_tab,
        style={"width": "100%"},
        persistence=True,
        children=tabs,
    )


def tab_view_layout(main_layout: list, sidebar_layout: list) -> wcc.FlexBox:
    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style={"flex": 1, "height": "87vh"},
                children=sidebar_layout,
            ),
            wcc.Frame(
                style={"flex": 6, "height": "87vh"},
                color="white",
                highlight=False,
                children=main_layout,
            ),
        ]
    )
