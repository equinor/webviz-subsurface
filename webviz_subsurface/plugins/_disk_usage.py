import pathlib
import datetime

import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC


class DiskUsage(WebvizPluginABC):
    """Visualize disk usage in a FMU project. It adds a dashboard showing disk usage per user,
    where the user can choose to plot as a pie chart or as a bar chart.

---

* **`scratch_dir`:** Path to the scratch directory to show disk usage for.

---

?> The `scratch_dir` directory must have a hidden folder `.disk_usage` containing daily
csv files called `disk_usage_user_YYYY-MM-DD.csv` (where YYYY-MM-DD is the date).
The plugin will search backwards from the current date, and throw an error if no file was found
from the last week.

The csv file must have the columns `userid` and `usageKB` (where KB means kilobytes).
All other columns are ignored.
"""

    def __init__(self, app, scratch_dir: pathlib.Path):

        super().__init__()

        self.scratch_dir = scratch_dir
        self.disk_usage = get_disk_usage(self.scratch_dir)
        self.date = str(self.disk_usage["date"].unique()[0])
        self.users = self.disk_usage["userid"]
        self.usage_gb = self.disk_usage["usageKB"] / (1024 ** 2)
        self.set_callbacks(app)
        self.theme = app.webviz_settings["theme"]

    @property
    def layout(self):
        return html.Div(
            [
                html.P(
                    f"This is the disk usage on \
                        {self.scratch_dir} per user, \
                        as of {self.date}."
                ),
                dcc.RadioItems(
                    id=self.uuid("plot_type"),
                    options=[
                        {"label": i, "value": i} for i in ["Pie chart", "Bar chart"]
                    ],
                    value="Pie chart",
                ),
                wcc.Graph(id=self.uuid("chart")),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("chart"), "figure"),
            [Input(self.uuid("plot_type"), "value")],
        )
        def _update_plot(plot_type):
            if plot_type == "Pie chart":
                data = [
                    {
                        "values": self.usage_gb,
                        "labels": self.users,
                        "text": (self.usage_gb).map("{:.2f} GB".format),
                        "textinfo": "label",
                        "textposition": "inside",
                        "hoverinfo": "label+text",
                        "type": "pie",
                    }
                ]
                layout = {}

            elif plot_type == "Bar chart":
                data = [
                    {
                        "y": self.usage_gb,
                        "x": self.users,
                        "text": (self.usage_gb).map("{:.2f} GB".format),
                        "hoverinfo": "x+text",
                        "type": "bar",
                    }
                ]
                layout = {
                    "yaxis": {"title": "Usage in Gigabytes"},
                    "xaxis": {"title": "User name"},
                }

            layout["height"] = 800
            layout["width"] = 1000

            return {"data": data, "layout": self.theme.create_themed_layout(layout)}

    def add_webvizstore(self):
        return [(get_disk_usage, [{"scratch_dir": self.scratch_dir}])]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_disk_usage(scratch_dir) -> pd.DataFrame:
    today = datetime.datetime.today()
    for i in range(0, 7):
        date = today - datetime.timedelta(days=i)
        try:
            return pd.read_csv(
                pathlib.Path(scratch_dir)
                / ".disk_usage"
                / f"disk_usage_user_{date.strftime('%Y-%m-%d')}.csv"
            ).assign(date=date.strftime("%Y-%m-%d"))
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f"No disk usage file found for last week at {scratch_dir}")
