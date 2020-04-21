import colorlover as cl
import numpy as np
import pandas as pd
from ._processing import interpolate_depth, filter_frame


class FormationFigure:
    def __init__(self, well, formationdf, simdf, obsdf, ertdf=None):
        self.well = well
        self.simdf = filter_frame(simdf, {"WELL": well})
        self.obsdf = filter_frame(obsdf, {"WELL": well})
        self.formationdf = filter_frame(formationdf, {"WELL": well})
        self.ertdf = filter_frame(ertdf, {"WELL": well})
        self.enscolors = [
            "#243746",
            "#eb0036",
            "#919ba2",
            "#7d0023",
            "#66737d",
            "#4c9ba1",
            "#a44c65",
            "#80b7bc",
            "#ff1243",
            "#919ba2",
            "#be8091",
            "#b2d4d7",
            "#ff597b",
            "#bdc3c7",
            "#d8b2bd",
            "#ffe7d6",
            "#d5eaf4",
            "#ff88a1",
        ]
        self.traces = []
        self.formation_names = []
        self.formation_colors = cl.interp(cl.scales["8"]["qual"]["Pastel2"], 20)

    @property
    def max_pressure(self):
        max_obs = self.obsdf["PRESSURE"].max()
        max_sim = self.simdf["PRESSURE"].max()
        return max_obs if max_obs > max_sim else max_sim

    @property
    def layout(self):
        return {
            "yaxis": {"autorange": "reversed", "title": "Depth", "showgrid": False},
            "xaxis": {"title": "Pressure", "showgrid": False},
            "height": 800,
            "legend": {"orientation": "h"},
            "margin": {"t": 50},
            "hovermode": "closest",
            "shapes": self.formation_names,
        }

    def add_formation(self):
        """Plot zonation"""

        for i, (index, row) in enumerate(self.formationdf.iterrows()):
            if pd.isnull(row["BASE_TVD"]):
                if self.simdf["DEPTH"].max() > row["TOP_TVD"]:
                    base_tvd = self.simdf["DEPTH"].max()
                else:
                    continue
            else:
                base_tvd = row["BASE_TVD"]

            self.formation_names.append(
                {
                    "xref": "paper",
                    "yref": "y",
                    "x0": 0,
                    "x1": 1,
                    "name": row["ZONE"],
                    "y0": row["TOP_TVD"],
                    "y1": base_tvd,
                    "linecolor": self.formation_colors[i],
                    "fillcolor": self.formation_colors[i],
                    "type": "rect",
                    "layer": "below",
                }
            )
            self.traces.append(
                {
                    "showlegend": False,
                    "type": "scatter",
                    "y": [(base_tvd + row["TOP_TVD"]) / 2],
                    "x": [self.max_pressure],
                    "xref": "paper",
                    "text": row["ZONE"],
                    "mode": "text",
                    "hoverinfo": "skip",
                }
            )

    def add_observed(self, date):
        df = filter_frame(self.obsdf, {"DATE": date})
        self.traces.append(
            {
                "x": df["PRESSURE"],
                "y": df["DEPTH"],
                "type": "scatter",
                "mode": "markers",
                "name": "Observations",
                "marker": {"color": "black", "size": 20},
            }
        )

    def add_ert_observed(self, date, filter_zero=True):
        df = self.ertdf.copy()

        df = filter_frame(
            df,
            {
                "DATE": date,
                "REAL": df["REAL"].unique()[0],
                "ENSEMBLE": df["ENSEMBLE"].unique()[0],
            },
        )
        self.traces.append(
            {
                "x": df["OBS"],
                "y": df["TVD"],
                "type": "scatter",
                "mode": "markers",
                "name": "Ert observations",
                "marker": {"color": "blue", "size": 20},
                "error_x": {"type": "data", "array": df["OBS_ERR"], "visible": True,},
            }
        )

    def add_simulated_lines(self, date, ensembles):
        df = filter_frame(self.simdf, {"DATE": date, "ENSEMBLE": ensembles})
        traces = []
        frames = []
        for j, (ensemble, ensdf) in enumerate(df.groupby("ENSEMBLE")):
            for i, (real, realdf) in enumerate(ensdf.groupby("REAL")):
                self.traces.append(
                    {
                        "x": realdf["PRESSURE"],
                        "y": realdf["DEPTH"],
                        "hoverinfo": "y+x+text",
                        "hovertext": f"Realization: {real}, Ensemble: {ensemble}",
                        "type": "scatter",
                        "mode": "lines",
                        "line": {"color": self.enscolors[j]},
                        "name": ensemble,
                        "showlegend": i == 0,
                        "legendgroup": ensemble,
                    }
                )

    def add_fanchart(self, date, ensembles):
        df = filter_frame(self.simdf, {"DATE": date, "ENSEMBLE": ensembles})
        for j, (ensemble, ensdf) in enumerate(df.groupby("ENSEMBLE")):
            dframe = interpolate_depth(ensdf)
            quantiles = [10, 90]
            traces = []
            dframe = dframe.drop(columns=["REAL"]).groupby("DEPTH")
            # Build a dictionary of dataframes to be concatenated
            dframes = {}
            dframes["mean"] = dframe.mean()
            for quantile in quantiles:
                quantile_str = "p" + str(quantile)
                dframes[quantile_str] = dframe.quantile(q=quantile / 100.0)
            dframes["maximum"] = dframe.max()
            dframes["minimum"] = dframe.min()
            self.traces.extend(
                add_fanchart_traces(
                    pd.concat(dframes, names=["STATISTIC"], sort=False)["PRESSURE"],
                    self.enscolors[j],
                    ensemble,
                )
            )


def add_fanchart_traces(vector_stats, color, legend_group: str):
    """Renders a fanchart for an ensemble vector"""
    fill_color = hex_to_rgb(color, 0.3)
    line_color = hex_to_rgb(color, 1)
    return [
        {
            "name": legend_group,
            "hovertext": "Maximum",
            "y": vector_stats["maximum"].index.tolist(),
            "x": vector_stats["maximum"].values,
            "mode": "lines",
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P10",
            "y": vector_stats["p10"].index.tolist(),
            "x": vector_stats["p10"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Mean",
            "y": vector_stats["mean"].index.tolist(),
            "x": vector_stats["mean"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"color": line_color},
            "legendgroup": legend_group,
            "showlegend": True,
        },
        {
            "name": legend_group,
            "hovertext": "P90",
            "y": vector_stats["p90"].index.tolist(),
            "x": vector_stats["p90"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Minimum",
            "y": vector_stats["minimum"].index.tolist(),
            "x": vector_stats["minimum"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
    ]


def hex_to_rgb(hex_string, opacity=1):
    """Converts a hex color to rgb"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    rgb.append(opacity)
    return f"rgba{tuple(rgb)}"
