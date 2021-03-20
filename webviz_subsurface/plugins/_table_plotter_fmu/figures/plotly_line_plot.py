from typing import List, Dict, Optional

import numpy as np
import pandas as pd


class PlotlyLinePlot:
    def __init__(self) -> None:
        self._traces: List = []
        self._layout: Dict = {}

    def add_line(self, x: np.ndarray, y: np.ndarray) -> None:
        trace = {"type": "scatter", "x": x, "y": y}
        self._traces.append(trace)

    def add_realization_traces(
        self,
        dframe: pd.DataFrame,
        x_column: str,
        y_column: str,
        groupby: List = ["ENSEMBLE"],
        aggregation: Optional[str] = None,
    ) -> List[dict]:
        """Renders line trace for each realization, includes history line if present"""
        dframe["label"] = dframe.agg(
            lambda x: " | ".join([f"{x[sel]}" for sel in groupby]), axis=1
        )
        if aggregation is None:
            for idx, (label, label_df) in enumerate(dframe.groupby("label")):

                for real_no, (real, real_df) in enumerate(label_df.groupby("REAL")):
                    self._traces.append(
                        self._add_line_trace(
                            real_df[x_column], real_df[y_column], label, label
                        )
                    )
        else:
            df = self.calc_series_statistics(dframe, [y_column], x_column)
            print(df)
            for idx, (label, label_df) in enumerate(df.groupby("label")):
                self._traces.append(
                    self._add_line_trace(
                        label_df[x_column], label_df[(y_column, "mean")], label, label
                    )
                )

    @staticmethod
    def calc_series_statistics(
        df: pd.DataFrame, vectors: list, refaxis: str = "DATE"
    ) -> pd.DataFrame:
        """Calculate statistics for given vectors over the ensembles
        refaxis is used if another column than DATE should be used to groupby.
        """
        # Invert p10 and p90 due to oil industry convention.
        def p10(x: List[float]) -> List[float]:
            return np.nanpercentile(x, q=90)

        def p90(x: List[float]) -> List[float]:
            return np.nanpercentile(x, q=10)

        # Calculate statistics, ignoring NaNs.
        stat_df = (
            df[["label", refaxis] + vectors]
            .groupby(["label", refaxis])
            .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90])
            .reset_index()  # (level=["label", refaxis], col_level=1)
        )
        # Rename nanmin, nanmax and nanmean to min, max and mean.
        col_stat_label_map = {
            "nanmin": "min",
            "nanmax": "max",
            "nanmean": "mean",
            "p10": "high_p10",
            "p90": "low_p90",
        }
        stat_df.rename(columns=col_stat_label_map, level=1, inplace=True)

        return stat_df

    def _add_line_trace(self, x, y, name, legendgroup):
        print(x, y)
        return {
            # "line": {"shape": line_shape},
            "x": list(x),
            "y": list(y),
            # "hovertemplate": f"Realization: {real}, Ensemble: {ensemble}",
            "name": name,
            "legendgroup": legendgroup,
            # "marker": {
            #     "color": colors.get(ensemble, colors[list(colors.keys())[0]])
            # },
            # "showlegend": real_no == 0,
        }

    def add_observations(self, observations: dict, x_value: str) -> None:
        self._traces.extend(
            [
                {
                    "x": [value.get(x_value), []],
                    "y": [value.get("value"), []],
                    "marker": {"color": "black"},
                    "text": value.get("comment", None),
                    "hoverinfo": "y+x+text",
                    "showlegend": False,
                    "error_y": {
                        "type": "data",
                        "array": [value.get("error"), []],
                        "visible": True,
                    },
                }
                for value in observations
            ]
        )

    @property
    def figure(self) -> Dict:
        return dict(layout=self._layout, data=self._traces)
