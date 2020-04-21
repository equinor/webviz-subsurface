from ._processing import filter_frame


class MapFigure:
    def __init__(self, ertdf, ensemble):

        self.ertdf = (
            ertdf.loc[ertdf["ENSEMBLE"] == ensemble]
            .groupby(["WELL", "DATE", "ENSEMBLE"])
            .aggregate("mean")
            .reset_index()
        )

        self.traces = []

    def add_misfit_plot(self, sizeby, colorby, dates):
        # TODO: Figure out hovertext ==> Therese ==> Roger

        df = self.ertdf.loc[
            (self.ertdf["YEAR"] >= dates[0]) & (self.ertdf["YEAR"] <= dates[1])
        ]

        self.traces.append(
            {
                "x": df["EAST"],
                "y": df["NORTH"],
                "text": df["WELL"],
                "customdata": df["WELL"],
                "mode": "markers",
                "hovertext": [
                    f"Well: {well}"
                    f"<br>Mean simulated pressure: {pressure:.2f}"
                    f"<br>Mean misfit: {misfit:.2f}"
                    f"<br>Stddev pressure: {stddev:.2f}"
                    for well, stddev, misfit, pressure in zip(
                        df["WELL"], df["STDDEV"], df["DIFF"], df["SIMULATED"]
                    )
                ],
                "hoverinfo": "text",
                # "name": date,
                # "showlegend":False,
                "marker": {
                    "size": df[sizeby],
                    "sizeref": 2.0 * self.ertdf[sizeby].quantile(0.9) / (40.0 ** 2),
                    "sizemode": "area",
                    "sizemin": 6,
                    "color": df[colorby],
                    "cmin" : self.ertdf[colorby].min(),
                    "cmax" : self.ertdf[colorby].quantile(0.9),
                    "colorscale":[[0, 'rgb(0,0,255)'], [1, 'rgb(255,0,0)']],
                    "showscale": True,
                    "colorbar":{"x":0}
                },
            }
        )

    def add_fault_lines(self, df):
        for fault, faultdf in df.groupby("POLY_ID"):
            self.traces.append(
                {
                    "x": faultdf["X_UTME"],
                    "y": faultdf["Y_UTMN"],
                    "mode": "lines",
                    "type": "scatter",
                    "hoverinfo": "none",
                    "showlegend": False,
                    "line": {"color": "grey", "width": 1},
                }
            )

    @property
    def layout(self):
        """The plotly figure layout"""
        return {
            "hovermode": "closest",
            "legend": {"itemsizing": "constant", "orientation": "h"},
            "height": 800,
            "colorway":["red", "blue"],
            "margin": {"t": 50, "l": 0, "r": 0},
            "xaxis": {"constrain": "domain", "showgrid": False},
            "yaxis": {"scaleanchor": "x", "showgrid": False},
        }
