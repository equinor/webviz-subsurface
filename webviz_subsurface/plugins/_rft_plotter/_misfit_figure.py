from plotly.subplots import make_subplots


def update_misfit_plot(dframe, wells):
    wells = wells if isinstance(wells, list) else [wells]

    df = dframe[dframe["WELL"].isin(wells)]
    fig = make_subplots(
        rows=len(list(df["ENSEMBLE"].unique())), cols=1, vertical_spacing=0.1
    )
    layout = fig["layout"]
    max_diff = find_max_diff(df)
    shapes = []
    annotations = []
    for i, (ens, ensdf) in enumerate(df.groupby("ENSEMBLE")):

        realdf = ensdf.groupby("REAL").sum().reset_index()

        mean_diff = realdf["DIFF"].mean()
        realdf = realdf.sort_values(by=["DIFF"])
        trace = {"x": realdf["REAL"], "y": realdf["DIFF"], "type": "bar", "name": ens}

        fig.add_trace(trace, i + 1, 1)
        # First figure ('yaxis')
        if i == 0:
            layout.update(
                {
                    "xaxis": {"type": "category", "title": "Realization"},
                    "yaxis": {"range": [0, max_diff], "title": "Cumulative misfit"},
                }
            )
            shapes.append(average_line_shape(mean_diff, "y"))
            annotations.append(average_arrow_annotation(mean_diff, "y"))
        # Remaining figures ('yaxisX')
        else:
            layout.update(
                {
                    f"xaxis{i+1}": {"type": "category", "title": "Realization"},
                    f"yaxis{i+1}": {
                        "range": [0, max_diff],
                        "title": "Cumulative misfit",
                    },
                }
            )
            shapes.append(average_line_shape(mean_diff, f"y{i+1}"))
            annotations.append(average_arrow_annotation(mean_diff, f"y{i+1}"))

    layout.update({"height": 800, "shapes": shapes, "annotations": annotations})
    return {"data": fig["data"], "layout": layout}


def average_line_shape(mean_value, yref="y"):
    return {
        "type": "line",
        "yref": yref,
        "y0": mean_value,
        "y1": mean_value,
        "xref": "paper",
        "x0": 0,
        "x1": 1,
    }


def average_arrow_annotation(mean_value, yref="y"):
    return {
        "x": 0.5,
        "y": mean_value,
        "xref": "paper",
        "yref": yref,
        "text": f"Average: {mean_value:.2f}",
        "showarrow": True,
        "align": "center",
        "arrowhead": 2,
        "arrowsize": 1,
        "arrowwidth": 1,
        "arrowcolor": "#636363",
        "ax": 20,
        "ay": -25,
    }


def find_max_diff(df):
    max_diff = 0
    for ens, ensdf in df.groupby("ENSEMBLE"):
        realdf = ensdf.groupby("REAL").sum().reset_index()
        max_diff = max_diff if max_diff > realdf["DIFF"].max() else realdf["DIFF"].max()
    return max_diff
