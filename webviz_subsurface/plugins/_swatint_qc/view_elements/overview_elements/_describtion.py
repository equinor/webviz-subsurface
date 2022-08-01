import webviz_core_components as wcc
from dash import dcc, html
from webviz_config.webviz_plugin_subclasses import ViewElementABC

from .._layout_style import LayoutStyle


class Describtion(ViewElementABC):
    class IDs:
        TEXT = "text"

    def __init__(
        self,
    ) -> None:
        super().__init__()

    def inner_layout(self) -> html.Div:
        return html.Div(
            style={"margin-top": "20px"},
            id=Describtion.IDs.TEXT,
            children=[
                wcc.Header("QC_FLAG descriptions", style=LayoutStyle.HEADER),
                dcc.Markdown(qc_flag_description()),
            ],
        )


def qc_flag_description() -> str:  # listen på bunnen av første side
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
