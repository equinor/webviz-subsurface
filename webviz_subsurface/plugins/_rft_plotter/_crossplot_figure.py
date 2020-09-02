import webviz_core_components as wcc


def update_crossplot(df, sizeby, colorby):

    sim_range = find_sim_range(df)
    sizeref, cmin, cmax = size_color_settings(df, sizeby, colorby)

    figures = []

    for _ens, ensdf in df.groupby("ENSEMBLE"):

        dframe = (
            ensdf.groupby(["WELL", "DATE", "ZONE", "TVD"]).mean().reset_index().copy()
        )
        trace = {
            "x": dframe["OBS"],
            "y": dframe["SIMULATED"],
            "type": "scatter",
            "mode": "markers",
            "hovertext": [
                f"Well: {well}"
                f"<br>Zone: {zone}"
                f"<br>Pressure observation: {obs:.2f}"
                f"<br>Mean simulated pressure: {pressure:.2f}"
                f"<br>Mean misfit: {misfit:.2f}"
                f"<br>Stddev pressure: {stddev:.2f}"
                for well, zone, obs, stddev, misfit, pressure in zip(
                    dframe["WELL"],
                    dframe["ZONE"],
                    dframe["OBS"],
                    dframe["STDDEV"],
                    dframe["DIFF"],
                    dframe["SIMULATED"],
                )
            ],
            "hoverinfo": "text",
            "marker": {
                "size": dframe[sizeby],
                "sizeref": 2.0 * sizeref / (30.0 ** 2),
                "sizemode": "area",
                "sizemin": 6,
                "color": dframe[colorby],
                "cmin": cmin,
                "cmax": cmax,
                "colorscale": [[0, "#2584DE"], [1, "#E50000"]],
                "colorbar": {"x": 1.05},
                "showscale": True,
            },
        }

        layout = {
            "height": 400,
            "title": {
                "text": _ens,
                "y": 0.95,
                "x": 0.15,
                "xanchor": "center",
                "yanchor": "top",
            },
            "margin": {"l": 100, "r": 0, "b": 50, "t": 30},
            "showlegend": False,
            "xaxis": {
                "range": sim_range,
                "title": "Pressure Observation",
                "showticklabels": True,
            },
            "yaxis": {"range": sim_range, "title": "Simulated mean pressure"},
            "shapes": [
                {
                    "type": "line",
                    "x0": sim_range[0],
                    "y0": sim_range[0],
                    "x1": sim_range[1],
                    "y1": sim_range[1],
                    "line": {
                        "color": "#007079",
                        "width": 2,
                    },
                }
            ],
        }

        figures.append(wcc.Graph(figure={"data": [trace], "layout": layout}))
    return figures


def size_color_settings(df, sizeby, colorby):

    df = df.groupby(["WELL", "DATE", "ZONE", "TVD", "ENSEMBLE"]).mean().reset_index()

    sizeref = df[sizeby].quantile(0.9)
    cmin = df[colorby].min()
    cmax = df[colorby].quantile(0.9)

    return sizeref, cmin, cmax


def find_sim_range(df):

    df = df.groupby(["WELL", "DATE", "ZONE", "TVD", "ENSEMBLE"]).mean().reset_index()

    max_sim = (
        df["SIMULATED"].max()
        if df["SIMULATED"].max() > df["OBS"].max()
        else df["OBS"].max()
    )
    min_sim = (
        df["SIMULATED"].min()
        if df["SIMULATED"].min() < df["OBS"].min()
        else df["OBS"].min()
    )

    axis_extend = (max_sim - min_sim) * 0.1

    return [min_sim - axis_extend, max_sim + axis_extend]
