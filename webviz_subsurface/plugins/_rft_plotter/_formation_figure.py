import pandas as pd
import numpy as np

from ._processing import interpolate_depth, filter_frame


class FormationFigure:
    def __init__(self, well, simdf, ertdf, enscolors, obsdf=None):
        self.well = well
        self.simdf = filter_frame(simdf, {"WELL": well})
        self.obsdf = filter_frame(obsdf, {"WELL": well}) if obsdf is not None else None
        self.ertdf = filter_frame(ertdf, {"WELL": well})

        self.enscolors = enscolors

        self.traces = []
        self._layout = {
            "yaxis": {"autorange": "reversed", "title": "Depth", "showgrid": False},
            "xaxis": {"title": "Pressure", "showgrid": False},
            "height": 800,
            "legend": {"orientation": "h"},
            "margin": {"t": 50},
            "hovermode": "closest",
        }

    @property
    def layout(self):
        return self._layout

    @property
    def max_pressure(self):
        max_obs = self.ertdf["SIMULATED"].max()
        max_sim = self.simdf["PRESSURE"].max()
        return max_obs if max_obs > max_sim else max_sim

    def add_formation(self, df):
        """Plot zonation"""
        formation_names = []
        formation_colors = [
            f"hsl({210*(1-x) + 202*x}, {100*(1-x) + 56*x}%, {98*(1-x) + 62*x}%)"
            for x in np.linspace(0, 1, len(df["ZONE"].unique()))
        ]

        df = filter_frame(df, {"WELL": self.well})
        for i, (_index, row) in enumerate(df.iterrows()):
            if pd.isnull(row["BASE_TVD"]):
                if self.simdf["DEPTH"].max() > row["TOP_TVD"]:
                    base_tvd = self.simdf["DEPTH"].max()
                else:
                    continue
            else:
                base_tvd = row["BASE_TVD"]

            formation_names.append(
                {
                    "xref": "paper",
                    "yref": "y",
                    "x0": 0,
                    "x1": 1,
                    "name": row["ZONE"],
                    "y0": row["TOP_TVD"],
                    "y1": base_tvd,
                    "linecolor": formation_colors[i],
                    "fillcolor": formation_colors[i],
                    "type": "rect",
                    "layer": "below",
                }
            )
            # Do not show label if zone thickness less than 3 meters
            if (base_tvd - row["TOP_TVD"]) > 3:
                self.traces.append(
                    {
                        "showlegend": False,
                        "type": "scatter",
                        "y": [(base_tvd + row["TOP_TVD"]) / 2],
                        "x": [self.max_pressure + 5],
                        "text": f"<b>{row['ZONE']}</b>",
                        "textfont": {"size": 14, "color": "#E50000"},
                        "textposition": "middle left",
                        "mode": "text",
                        "hoverinfo": "skip",
                    }
                )
        self._layout.update({"shapes": formation_names})

    def add_observed(self, date):
        if self.obsdf is not None:
            df = filter_frame(self.obsdf, {"DATE": date})
            self.traces.append(
                {
                    "x": df["PRESSURE"],
                    "y": df["DEPTH"],
                    "type": "scatter",
                    "mode": "markers",
                    "name": "Observations",
                    "marker": {"color": "Black", "size": 20},
                }
            )

    def add_ert_observed(self, date):
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
                "marker": {"color": "#2584DE", "size": 20,},
                "error_x": {
                    "type": "data",
                    "array": df["OBS_ERR"],
                    "visible": True,
                    "thickness": 6,
                },
            }
        )

    def add_simulated_lines(self, date, ensembles):
        df = filter_frame(self.simdf, {"DATE": date, "ENSEMBLE": ensembles})

        for ensemble, ensdf in df.groupby("ENSEMBLE"):
            for i, (real, realdf) in enumerate(ensdf.groupby("REAL")):
                self.traces.append(
                    {
                        "x": realdf["PRESSURE"],
                        "y": realdf["DEPTH"],
                        "hoverinfo": "y+x+text",
                        "hovertext": f"Realization: {real}, Ensemble: {ensemble}",
                        "type": "scatter",
                        "mode": "lines",
                        "line": {"color": self.enscolors[ensemble]},
                        "name": ensemble,
                        "showlegend": i == 0,
                        "legendgroup": ensemble,
                    }
                )

    def add_fanchart(self, date, ensembles):
        df = filter_frame(self.simdf, {"DATE": date, "ENSEMBLE": ensembles})
        for ensemble, ensdf in df.groupby("ENSEMBLE"):
            dframe = interpolate_depth(ensdf)
            quantiles = [10, 90]
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
                    self.enscolors[ensemble],
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
