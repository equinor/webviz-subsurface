import webviz_core_components as wcc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC

from .._swatint import SwatinitQcDataModel
from ._dash_table import DashTable
from ._layout_style import LayoutStyle


class OverviewViewelement(ViewElementABC):
    """All elements visible in the 'Overview and Information'-tab
    gathered in one viewelement"""

    class IDs:
        # pylint: disable=too-few-public-methods
        LAYOUT = "layout"
        DESCRIBTION = "describtion"
        FRAME = "frame"
        KEY_NUMBERS = "key-numbers"
        BUTTON = "button"
        INFO_DIALOG = "info-dialog"
        TABLE_LABEL = "tabel-label"
        TABLE = "table"

    def __init__(self, datamodel: SwatinitQcDataModel) -> None:
        super().__init__()
        self.datamodel = datamodel
        max_pc, min_pc = datamodel.pc_scaling_min_max
        wvol, hcvol = datamodel.vol_diff_total
        self.number_style = {
            "font-weight": "bold",
            "font-size": "17px",
            "margin-left": "20px",
        }
        self.infodata = [
            ("HC Volume difference:", f"{hcvol:.2f} %"),
            ("Water Volume difference:", f"{wvol:.2f} %"),
            ("Maximum Capillary Pressure scaling:", f"{max_pc:.1f}"),
            ("Minimum Capillary Pressure scaling:", f"{min_pc:.3g}"),
        ]
        self.title = "Plugin and 'check_swatinit' information"

        self.tabledata, self.columns = datamodel.table_data_qc_vol_overview()
        self.label = (
            "Table showing volume changes from SWATINIT to SWAT at Reservoir conditions"
        )

    def inner_layout(self) -> html.Div:
        return html.Div(
            id=self.register_component_unique_id(OverviewViewelement.IDs.LAYOUT),
            children=[
                html.Div(
                    style={"height": "40vh", "overflow-y": "auto"},
                    children=[
                        wcc.FlexBox(
                            children=[
                                wcc.FlexColumn(
                                    [
                                        self.table,
                                    ],
                                    flex=7,
                                    style={"margin-right": "20px"},
                                ),
                                wcc.FlexColumn(self.infobox, flex=3),
                            ],
                        ),
                    ],
                ),
                self.describtion,
            ],
        )

    @property
    def describtion(self) -> html.Div:
        return html.Div(
            style={"margin-top": "20px"},
            id=OverviewViewelement.IDs.DESCRIBTION,
            children=[
                wcc.Header("QC_FLAG descriptions", style=LayoutStyle.HEADER),
                dcc.Markdown(qc_flag_description()),
            ],
        )

    @property
    def infobox(self) -> Component:
        return wcc.Frame(
            style={"height": "90%"},
            id=self.register_component_unique_id(OverviewViewelement.IDs.FRAME),
            children=[
                wcc.Header("Information", style=LayoutStyle.HEADER),
                self.info_dialog,
                wcc.Header("Key numbers", style=LayoutStyle.HEADER),
                html.Div(
                    [
                        html.Div([text, html.Span(num, style=self.number_style)])
                        for text, num in self.infodata
                    ],
                    id=self.register_component_unique_id(
                        OverviewViewelement.IDs.KEY_NUMBERS
                    ),
                ),
            ],
        )

    @property
    def info_dialog(self) -> html.Div:
        return html.Div(
            style={"margin-bottom": "30px"},
            children=[
                html.Button(
                    "CLICK HERE FOR INFORMATION",
                    style={"width": "100%", "background-color": "white"},
                    id=self.register_component_unique_id(
                        OverviewViewelement.IDs.BUTTON
                    ),
                ),
                wcc.Dialog(
                    title=self.title,
                    id=self.register_component_unique_id(
                        OverviewViewelement.IDs.INFO_DIALOG
                    ),
                    max_width="md",
                    open=False,
                    children=dcc.Markdown(check_swatinit_description()),
                ),
            ],
        )

    @property
    def table(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    html.Label(self.label, className="webviz-underlined-label"),
                    style={"margin-bottom": "20px"},
                    id=self.register_component_unique_id(
                        OverviewViewelement.IDs.TABLE_LABEL
                    ),
                ),
                DashTable(
                    id=self.register_component_unique_id(OverviewViewelement.IDs.TABLE),
                    data=self.tabledata,
                    columns=self.columns,
                    style_data_conditional=[
                        {
                            "if": {"row_index": [0, len(self.tabledata) - 1]},
                            **LayoutStyle.TABLE_HIGHLIGHT,
                        },
                    ],
                ),
            ],
        )


def qc_flag_description() -> str:
    return """
- **PC_SCALED**  - Capillary pressure have been scaled and SWATINIT was accepted.
- **FINE_EQUIL**  - If item 9 in EQUIL is nonzero then initialization happens in a vertically
    refined model. Capillary pressure is still scaled, but water might be added or lost.
- **SWL_TRUNC**  - If SWL is larger than SWATINIT, SWAT will be reset to SWL. Extra water is
    added and hydrocarbons are lost.
- **SWATINIT_1**  - When SWATINIT is 1 above the contact, Eclipse will ignore SWATINIT and not
    touch the capillary pressure function which typically results in extra hydrocarbons.
    This could be ok as long as the porosities and/or permeabilities of these cells are small.
    If SWU is included, cells where SWATINIT is equal or larger than SWU will
    also be flagged as SWATINIT_1
- **HC_BELOW_FWL**  - If SWATINIT is less than 1 below the contact provided in EQUIL, Eclipse will
    ignore it and not scale the capillary pressure function. SWAT will be 1, unless a capillary
    pressure function with negative values is in SWOF/SWFN. This results in the loss of HC volumes.
- **PPCWMAX**  - If an upper limit of how much capillary pressure scaling is allowed is set, water will be
    lost if this limit is hit.
- **WATER**  - SWATINIT was 1 in the water zone, and SWAT is set to 1.
> **Consult the [check_swatinit](https://fmu-docs.equinor.com/docs/subscript/scripts/check_swatinit.html) 
  documentation for more detailed descriptions**
"""


def check_swatinit_description() -> str:
    return """
This plugin is used to visualize the output from **check_swatinit** which is a **QC tool for Water Initialization in Eclipse runs
when the SWATINIT keyword has been used**. It is used to quantify how much the volume changes from **SWATINIT** to **SWAT** at time
zero in the dynamical model, and help understand why it changes.
When the keyword SWATINIT has been used as water initialization option in Eclipse, capillary pressure scaling on a cell-by-cell basis will
occur in order to match SWATINIT from the geomodel. 
This process has some exceptions which can cause volume changes from SWATINIT to SWAT at time zero.
Each cell in the dynamical model has been flagged according to what has happened during initialization, and information is stored
in the **QC_FLAG** column.
> Check the maximum capillary pressure pr SATNUM in each EQLNUM to ensure extreme values were not necessary
[check_swatinit documentation](https://fmu-docs.equinor.com/docs/subscript/scripts/check_swatinit.html) 
"""
