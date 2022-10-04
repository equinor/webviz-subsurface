import datetime
import shutil
import warnings
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import pandas as pd
import webviz_core_components as wcc
from dash import html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


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

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        scratch_dir: Path,
        date: Optional["str"] = None,
    ):

        super().__init__()

        self.scratch_dir = scratch_dir
        self.date_input = date
        self.disk_usage = get_disk_usage(self.scratch_dir, self.date_input)
        self.date = str(self.disk_usage["date"][0])
        self.theme = webviz_settings.theme

    @property
    def layout(self) -> html.Div:
        return html.Div(
            [
                wcc.Header(
                    f"Disk usage on {self.scratch_dir} per user as of {self.date}",
                    style={"text-align": "center"},
                ),
                wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            color="white",
                            children=wcc.FlexColumn(
                                wcc.Graph(
                                    figure=self.pie_chart,
                                    config={"displayModeBar": False},
                                )
                            ),
                        ),
                        wcc.Frame(
                            color="white",
                            children=wcc.FlexColumn(
                                flex=2,
                                children=wcc.Graph(figure=self.bar_chart),
                            ),
                        ),
                    ]
                ),
            ]
        )

    @property
    def pie_chart(self) -> dict:
        return {
            "data": [
                {
                    "values": self.disk_usage["usageGiB"],
                    "labels": self.disk_usage["userid"],
                    "pull": (self.disk_usage["userid"].values == "<b>Free space</b>")
                    * 0.05,
                    "text": self.disk_usage["usageGiB"].map(lambda x: f"{x:.2f} GiB"),
                    "textinfo": "label",
                    "textposition": "inside",
                    "hoverinfo": "label+text",
                    "type": "pie",
                }
            ],
            "layout": self.theme.create_themed_layout({}),
        }

    @property
    def bar_chart(self) -> dict:
        return {
            "data": [
                {
                    "y": self.disk_usage["usageGiB"],
                    "x": self.disk_usage["userid"],
                    "text": self.disk_usage["usageGiB"].map(lambda x: f"{x:.2f} GiB"),
                    "hoverinfo": "x+text",
                    "type": "bar",
                }
            ],
            "layout": self.theme.create_themed_layout(
                {"yaxis": {"title": "GiB (GibiBytes)"}}
            ),
        }

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            (
                get_disk_usage,
                [{"scratch_dir": self.scratch_dir, "date": self.date_input}],
            )
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_disk_usage(scratch_dir: Path, date: Optional[str]) -> pd.DataFrame:
    if date is None:
        df, date = _loop_dates(scratch_dir)
    else:
        df = _get_disk_usage_for_date(scratch_dir, date)
        if df is None:
            raise FileNotFoundError(
                f"No disk usage file found for {date} in {scratch_dir}."
            )

    df.rename(
        columns={"usageKB": "usageKiB"}, inplace=True
    )  # Old format had an error (KB instead of KiB)

    df["usageGiB"] = df["usageKiB"] / (1024**2)

    df.drop(columns="usageKiB", inplace=True)

    free_space_gib = _estimate_free_space(df, scratch_dir, date)
    if free_space_gib < 0:
        warnings.warn(
            f"Reported disk usage in "
            f"{scratch_dir}/.disk_usage for {date}"
            f"must be wrong (unless total disk size has changed after {date}). "
            f"Total reported usage is {int(df['usageGiB'])} GiB, "
            f"but the disk size is only {int(shutil.disk_usage(scratch_dir).total / 1024**3)} GiB "
            f"(this would imply negative free space of {int(free_space_gib)} GiB).",
            UserWarning,
            stacklevel=0,
        )
    else:
        df = pd.concat(
            [
                df,
                pd.DataFrame.from_records(
                    [
                        {
                            "userid": "<b>Free space</b>",
                            "usageGiB": free_space_gib,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    df["date"] = date
    return df.sort_values(by="usageGiB", axis=0, ascending=False)


def _get_disk_usage_for_date(scratch_dir: Path, date: str) -> Optional[pd.DataFrame]:
    csv_file = scratch_dir / ".disk_usage" / f"disk_usage_user_test_{date}.csv"
    if csv_file.exists():
        return pd.read_csv(csv_file)
    # If file does not exist, look for old format
    csv_file = scratch_dir / ".disk_usage" / f"disk_usage_user_{date}.csv"
    if csv_file.exists():
        return pd.read_csv(csv_file)
    return None


def _loop_dates(scratch_dir: Path) -> Tuple[pd.DataFrame, str]:
    today = datetime.datetime.today()
    for i in range(7):
        date = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        df = _get_disk_usage_for_date(scratch_dir, date)
        if df is not None:
            return (df, date)
    raise FileNotFoundError(
        f"No disk usage file found for the last week in {scratch_dir}."
    )


def _estimate_free_space(df: pd.DataFrame, scratch_dir: Path, date: str) -> float:
    txt_file = Path(scratch_dir / ".disk_usage" / f"disk_usage_user_test_{date}.txt")
    total_usage = None
    if txt_file.exists():
        lines = txt_file.read_text().splitlines()
        for line in lines[::-1]:  # reversed as last line is most likely
            if line.startswith("Total usage without overhead"):
                line = line[len("Total usage without overhead") :]
                total_usage = float(line.split()[0])
                break

    total_usage = df["usageGiB"].sum() if total_usage is None else total_usage
    return shutil.disk_usage(scratch_dir).total / (1024**3) - total_usage
