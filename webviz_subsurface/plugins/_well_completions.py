import json

import dash
import dash_html_compontents as html

import webviz_subsurface_components

class WellCompletions(WebvizPluginABC):
    """
    Description goes here
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
    ):
        super().__init__()
        fn = "well-completions-with-attr.json"
        with open(fn, "r") as json_file:
            self.data = json.load(json_file)


    @property
    def layout(self) -> html.Div:
        return html.Div(
            style={"height": "600px"},
            children=[
                webviz_subsurface_components.WellCompletions(id="well_completions", data=data),
            ],

        )
