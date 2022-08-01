import webviz_core_components as wcc
from dash import dcc, html
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class InfoDialog(ViewElementABC):
    class IDs:
        # pylint:diable=too-few-public-methods
        BUTTON = "button"
        INFO_DIALOG = "info-dialog"

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.title = "Plugin and 'check_swatinit' information"

    def inner_layout(self) -> html.Div:
        return html.Div(
            style={"margin-bottom": "30px"},
            children=[
                html.Button(
                    "CLICK HERE FOR INFORMATION",  # var egt samme som tittelen til wcc.Dialog
                    style={"width": "100%", "background-color": "white"},
                    id=self.register_component_unique_id(InfoDialog.IDs.BUTTON),
                ),
                wcc.Dialog(
                    title=self.title,
                    id=self.register_component_unique_id(InfoDialog.IDs.INFO_DIALOG),
                    max_width="md",
                    open=False,
                    children=dcc.Markdown(check_swatinit_description()),
                ),
            ],
        )


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
