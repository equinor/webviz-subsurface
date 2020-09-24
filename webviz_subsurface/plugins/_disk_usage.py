import shutil
import warnings
import pathlib
import datetime
from typing import Optional

import pandas as pd
import dash_html_components as html
import webviz_core_components as wcc
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC


class DiskUsage(WebvizPluginABC):
    """Visualize disk usage in a FMU project. It adds a dashboard showing disk usage per user.

    ---

    * **`scratch_dir`:** Path to the scratch directory to show disk usage for.
    * **`date`:** Date as string of form YYYY-MM-DD to request an explisit date. Default is to
    to use the most recent file avaialable, limited to the last week.

    ---

    ?> The `scratch_dir` directory must have a hidden folder `.disk_usage` containing daily
    csv files called `disk_usage_user_YYYY-MM-DD.csv`, where YYYY-MM-DD is the date.
    The plugin will search backwards from the current date, and throw an error if no file was found
    from the last week.

    The csv file must have the columns `userid` and `usageKB` (where KB means
    [kibibytes](https://en.wikipedia.org/wiki/Kibibyte)). All other columns are ignored.
    """

    def __init__(self, app, scratch_dir: pathlib.Path, date: Optional["str"] = None):

        super().__init__()

        self.scratch_dir = scratch_dir
        self.date_input = date
        self.disk_usage = get_disk_usage(self.scratch_dir, self.date_input)
        self.date = str(self.disk_usage["date"].unique()[0])
        self.users = self.disk_usage["userid"]
        self.usage_gib = self.disk_usage["usageKB"] / (1024 ** 2)
        self.theme = app.webviz_settings["theme"]

    @property
    def layout(self):
        return html.Div(
            [
                html.H5(
                    f"Disk usage on {self.scratch_dir} per user as of {self.date}",
                    style={"text-align": "center"},
                ),
                wcc.FlexBox(
                    children=[
                        wcc.Graph(
                            style={"flex": 1},
                            figure=self.pie_chart,
                            config={"displayModeBar": False},
                        ),
                        wcc.Graph(style={"flex": 2}, figure=self.bar_chart),
                    ]
                ),
            ]
        )

    @property
    def pie_chart(self):
        return {
            "data": [
                {
                    "values": self.usage_gib,
                    "labels": self.users,
                    "pull": (self.users.values == "<b>Free space</b>") * 0.05,
                    "text": (self.usage_gib).map("{:.2f} GiB".format),
                    "textinfo": "label",
                    "textposition": "inside",
                    "hoverinfo": "label+text",
                    "type": "pie",
                }
            ],
            "layout": self.theme.create_themed_layout({}),
        }

    @property
    def bar_chart(self):
        return {
            "data": [
                {
                    "y": self.usage_gib,
                    "x": self.users,
                    "text": (self.usage_gib).map("{:.2f} GiB".format),
                    "hoverinfo": "x+text",
                    "type": "bar",
                }
            ],
            "layout": self.theme.create_themed_layout(
                {"yaxis": {"title": "GiB (GibiBytes)"}}
            ),
        }

    def add_webvizstore(self):
        return [
            (
                get_disk_usage,
                [{"scratch_dir": self.scratch_dir, "date": self.date_input}],
            )
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_disk_usage(scratch_dir, date) -> pd.DataFrame:
    def _loop_dates(scratch_dir):
        today = datetime.datetime.today()
        for i in range(7):
            date = today - datetime.timedelta(days=i)
            try:
                return pd.read_csv(
                    scratch_dir
                    / ".disk_usage"
                    / f"disk_usage_user_{date.strftime('%Y-%m-%d')}.csv"
                ).assign(date=date.strftime("%Y-%m-%d"))
            except FileNotFoundError:
                continue
        raise FileNotFoundError(
            f"No disk usage file found for last week in {scratch_dir}."
        )

    if date is None:
        df = _loop_dates(scratch_dir)
    else:
        try:
            df = pd.read_csv(
                scratch_dir / ".disk_usage" / f"disk_usage_user_{date}.csv"
            ).assign(date=date)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"No disk usage file found for {date} in {scratch_dir}."
            ) from exc

    free_space_kib = (shutil.disk_usage(scratch_dir).total / 1024) - df["usageKB"].sum()

    if free_space_kib < 0:
        warnings.warn(
            f"Reported disk usage in "
            f"{scratch_dir}/.disk_usage/disk_usage_user_{df['date'].unique()[0]}.csv "
            f"must be wrong (unless total disk size has changed after {df['date'].unique()[0]}). "
            f"Total reported usage is {int(df['usageKB'].sum() / 1024**2)} GiB, "
            f"but the disk size is only {int(shutil.disk_usage(scratch_dir).total / 1024**3)} GiB "
            f"(this would imply negative free space of {int(free_space_kib / 1024**2)} GiB).",
            UserWarning,
            stacklevel=0,
        )
    else:
        df = df.append(
            {
                "userid": "<b>Free space</b>",
                "usageKB": free_space_kib,
                "date": df["date"].unique()[0],
            },
            ignore_index=True,
        )

    return df.sort_values(by="usageKB", axis=0, ascending=False)
