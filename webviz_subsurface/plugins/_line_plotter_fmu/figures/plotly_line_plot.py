from typing import List, Dict, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go


class PlotlyLinePlot:
    def __init__(self, active_x_value: Optional[str]) -> None:
        self._active_x_value = active_x_value
        self._realization_traces: List = []
        self._statistical_traces: List = []
        self._observation_traces: List = []
        self._layout: go.Layout = go.Layout(paper_bgcolor="rgba(0,0,0,0)")

    def add_realization_traces(
        self,
        dframe: pd.DataFrame,
        x_column: str,
        y_column: str,
        color_column: str,
        realization_slider: bool = False,
        color: str = "Realizations",
    ) -> List[dict]:
        """Renders line trace for each realization, includes history line if present"""
        colors = ["red", "blue", "green"]

        for idx, (ensemble, ens_df) in enumerate(dframe.groupby("ENSEMBLE")):
            if (
                self._active_x_value
                and self._active_x_value in ens_df[x_column].unique()
            ):
                parameter_order = ens_df.loc[
                    ens_df[x_column] == self._active_x_value
                ].sort_values(by=color_column)
            else:
                parameter_order = ens_df.loc[
                    ens_df[x_column] == ens_df[x_column].max()
                ].sort_values(by=color_column)

            for real_no, (real, real_df) in enumerate(ens_df.groupby("REAL")):
                self._realization_traces.append(
                    {
                        "x": real_df[x_column],
                        "y": real_df[y_column],
                        "hovertemplate": f"Realization: {real}, Ensemble: {ensemble}",
                        "name": ensemble,
                        "legendgroup": ensemble,
                        "marker": {
                            "color": "rgba(128,128,128,0.2)"
                            if color == "Realizations"
                            else "black"
                        },
                        "showlegend": real_no == 0,
                    }
                )
        self._layout["sliders"] = (
            self._realization_slider() if realization_slider is True else []
        )

    def _realization_slider(self):
        steps = []
        for trace_no, _ in enumerate(self._realization_traces):
            step: Dict = {
                "method": "update",
                "label": str(trace_no),
                "args": [
                    {
                        "marker.color": [
                            "rgba(128,128,128,0.2)"
                            for idx, _ in enumerate(self._realization_traces)
                        ]
                    },
                ],
            }
            step["args"][0]["marker.color"][trace_no] = "black"
            steps.append(step)
        return [
            dict(
                steps=steps,
                active=0,
                currentvalue={"prefix": "Realization: ", "visible": True},
                pad={"t": 50},
                y=0,
            )
        ]

    def add_statistical_lines(
        self, dframe: pd.DataFrame, x_column: str, y_column: str, traces: List
    ):
        colors = ["red", "blue", "green"]
        for idx, (ensemble, ens_df) in enumerate(dframe.groupby("ENSEMBLE")):
            if "Low/High" in traces:
                self._statistical_traces.append(
                    {
                        "line": {"dash": "dot", "width": 1},
                        "x": ens_df[x_column],
                        "y": ens_df[(y_column, "max")],
                        "hovertemplate": f"Calculation: {'mac'}, Ensemble: {ensemble}",
                        "name": ensemble,
                        "legendgroup": ensemble,
                        "showlegend": False,
                        "marker": {"color": colors[idx]},
                    }
                )
            if "P10/P90" in traces:
                self._statistical_traces.append(
                    {
                        "line": {"dash": "dash"},
                        "x": ens_df[x_column],
                        "y": ens_df[(y_column, "high_p10")],
                        "hovertemplate": f"Calculation: {'high_p10'}, Ensemble: {ensemble}",
                        "name": ensemble,
                        "legendgroup": ensemble,
                        "showlegend": False,
                        "marker": {"color": colors[idx]},
                    }
                )
            if "Mean" in traces:
                self._statistical_traces.append(
                    {
                        "x": ens_df[x_column],
                        "y": ens_df[(y_column, "mean")],
                        "hovertemplate": f"Calculation: {'mean'}, Ensemble: {ensemble}",
                        "name": ensemble,
                        "legendgroup": ensemble,
                        # "fill": "tonexty",
                        "marker": {"color": colors[idx]},
                    }
                )
            if "P10/P90" in traces:
                self._statistical_traces.append(
                    {
                        "line": {"dash": "dash"},
                        "x": ens_df[x_column],
                        "y": ens_df[(y_column, "low_p90")],
                        "hovertemplate": f"Calculation: {'low_p90'}, Ensemble: {ensemble}",
                        "name": ensemble,
                        "legendgroup": ensemble,
                        "showlegend": False,
                        # "fill": "tonexty",
                        "marker": {"color": colors[idx]},
                    }
                )
            if "Low/High" in traces:
                self._statistical_traces.append(
                    {
                        "line": {"dash": "dot", "width": 1},
                        "x": ens_df[x_column],
                        "y": ens_df[(y_column, "min")],
                        "hovertemplate": f"Calculation: {'min'}, Ensemble: {ensemble}",
                        "name": ensemble,
                        "legendgroup": ensemble,
                        "showlegend": False,
                        "marker": {"color": colors[idx]},
                    }
                )

    def add_observations(self, observations: dict, x_value: str) -> None:
        self._observation_traces.append(
            [
                {
                    "x": obs.get(x_value, []),
                    "y": obs.get("value", []),
                    "marker": {"color": "black"},
                    "text": obs.get("comment", None),
                    "hoverinfo": "y+x+text",
                    "showlegend": False,
                    "error_y": {
                        "type": "data",
                        "array": [obs.get("error"), []],
                        "visible": True,
                    },
                }
                for obs in observations
            ]
        )

    def get_figure(self) -> Dict:
        traces = (
            self._realization_traces
            + self._statistical_traces
            + self._observation_traces
        )
        return dict(layout=self._layout, data=traces)
