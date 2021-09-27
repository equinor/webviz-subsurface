from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go


class PlotlyLinePlot:
    def __init__(
        self,
        xaxis_title: str = None,
        yaxis_title: str = None,
        ensemble_colors: Dict = None,
    ) -> None:
        self._ensemble_colors = ensemble_colors if ensemble_colors else {}
        self._realization_traces: List = []
        self._statistical_traces: List = []
        self._observation_traces: List = []
        self._layout: go.Layout = go.Layout(
            xaxis={"title": xaxis_title},
            yaxis={"title": yaxis_title},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

    def add_realization_traces(
        self,
        dframe: pd.DataFrame,
        x_column: str,
        y_column: str,
        color_column: Optional[str],
        highlight_reals: List = None,
        opacity: float = None,
        mode: str = "lines",
    ) -> None:
        """Renders line trace for each realization"""
        # If color parameter is given, normalize values for coloring
        if color_column is not None:
            dframe["VALUE_NORM"] = (
                dframe[color_column] - dframe[color_column].min()
            ) / (dframe[color_column].max() - dframe[color_column].min())
        highlight_reals = highlight_reals if highlight_reals else []
        for ensemble, ens_df in dframe.groupby("ENSEMBLE"):
            for real_no, (real, real_df) in enumerate(ens_df.groupby("REAL")):
                self._realization_traces.append(
                    {
                        "x": real_df[x_column],
                        "y": real_df[y_column],
                        "hovertemplate": (
                            f"Realization: {real}, Ensemble: {ensemble}"
                            f"<br>{color_column}: {real_df[color_column].unique()[0]}"
                        )
                        if color_column is not None
                        else f"Realization {real}, Ensemble: {ensemble}",
                        "name": ensemble,
                        "text": real,
                        "legendgroup": ensemble,
                        "marker": {
                            "color": "black"
                            if real in highlight_reals
                            else set_real_color(real_no=real, df_norm=dframe)
                            if color_column is not None
                            else self._ensemble_colors.get(
                                ensemble, "rgba(128,128,128,0.2)"
                            ),
                        },
                        "opacity": opacity,
                        "line": {"width": 3 if real in highlight_reals else 0.5},
                        "mode": mode,
                        "showlegend": real_no == 0 and color_column is None,
                    }
                )
        # Add a colorbar if parameter is used for coloring
        if color_column is not None:
            self._realization_traces.append(
                {
                    "x": [None],
                    "y": [None],
                    "mode": "markers",
                    "marker": {
                        "colorscale": [
                            ["0.0", "rgba(255,18,67, 1)"],
                            ["0.5", "rgba(220,220,220,1)"],
                            ["1.0", "rgba(62,208,62, 1)"],
                        ],
                        "cmin": dframe[color_column].min(),
                        "cmax": dframe[color_column].max(),
                        "colorbar": {
                            "thickness": 10,
                            "tickvals": [
                                dframe[color_column].min(),
                                dframe[color_column].max(),
                            ],
                            "tickmode": "array",
                        },
                        "showscale": True,
                    },
                    "hoverinfo": "none",
                    "showlegend": False,
                }
            )

    def add_statistical_lines(
        self,
        dframe: pd.DataFrame,
        x_column: str,
        y_column: str,
        traces: List,
        mode: str = "lines",
    ) -> None:
        for ensemble, ens_df in dframe.groupby("ENSEMBLE"):
            color = self._ensemble_colors.get(ensemble, "rgba(128,128,128,1)")
            if "Low/High" in traces:
                self._statistical_traces.append(
                    {
                        "line": {"dash": "dot", "width": 3},
                        "x": ens_df[x_column],
                        "y": ens_df[(y_column, "max")],
                        "hovertemplate": f"Calculation: {'mac'}, Ensemble: {ensemble}",
                        "name": ensemble,
                        "legendgroup": ensemble,
                        "showlegend": False,
                        "marker": {"color": color},
                        "mode": mode,
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
                        "marker": {"color": color},
                        "mode": mode,
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
                        "marker": {"color": color},
                        "mode": mode,
                        "line": {"width": 3},
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
                        "marker": {"color": color},
                        "mode": mode,
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
                        "marker": {"color": color},
                        "mode": mode,
                    }
                )

    def add_observations(self, observations: list, x_value: str) -> None:
        for obs in observations:
            self._observation_traces.append(
                {
                    "x": [obs.get(x_value, [])],
                    "y": [obs.get("value", [])],
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
            )

    def get_figure(self) -> Dict:
        traces = []
        if self._realization_traces:
            traces.extend(self._realization_traces)
        if self._statistical_traces:
            traces.extend(self._statistical_traces)
        if self._observation_traces:
            traces.extend(self._observation_traces)
        return dict(layout=self._layout, data=traces)


def set_real_color(df_norm: pd.DataFrame, real_no: str) -> str:
    """
    Return color for trace based on normalized parameter value.
    Midpoint for the colorscale is set on the average value
    """
    red = "rgba(255,18,67, 1)"
    mid_color = "rgba(220,220,220,1)"
    green = "rgba(62,208,62, 1)"
    df_norm = df_norm.reset_index(drop=True)
    mean = df_norm["VALUE_NORM"].mean()
    norm_value = df_norm.loc[df_norm["REAL"] == real_no].iloc[0]["VALUE_NORM"]
    if norm_value <= mean:
        intermed = norm_value / mean
        return find_intermediate_color(red, mid_color, intermed, colortype="rgba")
    if norm_value > mean:
        intermed = (norm_value - mean) / (1 - mean)
        return find_intermediate_color(mid_color, green, intermed, colortype="rgba")
    return "rgba(220,220,220, 0.8)"


def find_intermediate_color(
    lowcolor: str, highcolor: str, intermed: float, colortype: str = "tuple"
) -> str:
    """
    Returns the color at a given distance between two colors
    This function takes two color tuples, where each element is between 0
    and 1, along with a value 0 < intermed < 1 and returns a color that is
    intermed-percent from lowcolor to highcolor. If colortype is set to 'rgb',
    the function will automatically convert the rgb type to a tuple, find the
    intermediate color and return it as an rgb color.
    """

    if colortype == "rgba":
        # convert to tuple color, eg. (1, 0.45, 0.7)
        low = unlabel_rgba(lowcolor)
        high = unlabel_rgba(highcolor)

    diff_0 = float(high[0] - low[0])
    diff_1 = float(high[1] - low[1])
    diff_2 = float(high[2] - low[2])
    diff_3 = float(high[3] - low[3])

    inter_med_tuple = (
        low[0] + intermed * diff_0,
        low[1] + intermed * diff_1,
        low[2] + intermed * diff_2,
        low[3] + intermed * diff_3,
    )

    if colortype == "rgba":
        # back to an rgba string, e.g. rgba(30, 20, 10)
        inter_med_rgba = label_rgba(inter_med_tuple)
        return inter_med_rgba

    return str(inter_med_tuple)


def label_rgba(colors: Tuple) -> str:
    """
    Takes tuple (a, b, c, d) and returns an rgba color 'rgba(a, b, c, d)'
    """
    return f"rgba({colors[0]}, {colors[1]}, {colors[2]}, {colors[3]})"


def unlabel_rgba(colors: str) -> Tuple:
    """
    Takes rgba color(s) 'rgba(a, b, c, d)' and returns tuple(s) (a, b, c, d)
    This function takes either an 'rgba(a, b, c, d)' color or a list of
    such colors and returns the color tuples in tuple(s) (a, b, c, d)
    """
    str_vals = ""
    for index, _col in enumerate(colors):
        try:
            float(colors[index])
            str_vals = str_vals + colors[index]
        except ValueError:
            if colors[index] == "," or colors[index] == ".":
                str_vals = str_vals + colors[index]

    str_vals = str_vals + ","
    numbers = []
    str_num = ""
    for char in str_vals:
        if char != ",":
            str_num = str_num + char
        else:
            numbers.append(float(str_num))
            str_num = ""
    return tuple(numbers)
