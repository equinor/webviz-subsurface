import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from webviz_subsurface._utils.colors import hex_to_rgb, rgb_to_str, scale_rgb_lightness


def axis_defaults(showgrid: bool = True) -> dict:
    return {
        "showline": True,
        "linewidth": 2,
        "linecolor": "black",
        "mirror": True,
        "showgrid": showgrid,
        "gridwidth": 1,
        "gridcolor": "lightgrey",
    }


class PropertiesVsDepthSubplots:
    def __init__(
        self,
        dframe: pd.DataFrame,
        color_by: str,
        colormap: dict,
        discrete_color: bool = True,
    ) -> None:
        self.dframe = dframe
        self.color_by = color_by
        self.discrete_color = discrete_color
        self.colormap = colormap
        self.layout = [(1, 1), (1, 2), (2, 1), (2, 2)]
        self.responses = ["SWATINIT", "SWAT", "PRESSURE", "PC"]
        self.hover_data = self.create_hover_data(
            include_columns=["QC_FLAG", "EQLNUM", "SATNUM", "I", "J", "K"]
        )
        self.uirevision = "".join([str(x) for x in self.dframe["EQLNUM"].unique()])

        self._figure = self.create_empty_subplots_figure(rows=2, cols=2)
        self.add_subplotfigures_to_main_figure()
        self.add_contacts_to_plot()

    @property
    def figure(self) -> go.Figure:
        return self._figure

    @property
    def hovertemplate(self) -> go.Figure:
        return (
            "X: %{x}<br>Y: %{y}<br>"
            + "<br>".join(
                [
                    f"{col}:%{{customdata[{idx}]}}"
                    for idx, col in enumerate(self.hover_data)
                ]
            )
            + "<extra></extra>"
        )

    def create_empty_subplots_figure(self, rows: int, cols: int) -> go.Figure:
        return (
            make_subplots(
                rows=rows,
                cols=cols,
                subplot_titles=[f"Depth vs {resp}" for resp in self.responses],
                shared_yaxes=True,
                vertical_spacing=0.07,
                horizontal_spacing=0.05,
            )
            .update_layout(
                plot_bgcolor="white",
                uirevision=self.uirevision,
                margin={"t": 50, "b": 10, "l": 10, "r": 10},
                legend={"orientation": "h"},
                clickmode="event+select",
                coloraxis={"colorscale": "Viridis", **self.colorbar},
            )
            .update_yaxes(autorange="reversed", **axis_defaults())
            .update_xaxes(axis_defaults())
            .update_xaxes(row=1, col=2, matches="x")
        )

    def add_subplotfigures_to_main_figure(self) -> None:
        # for discrete colors there should be one trace per unique color
        unique_traces = (
            self.dframe[self.color_by].unique()
            if self.discrete_color
            else [self.color_by]
        )

        for color in unique_traces:
            df = self.dframe
            df = df[df[self.color_by] == color] if self.discrete_color else df
            customdata = np.stack([df[col] for col in self.hover_data], axis=-1)

            for idx, response in enumerate(self.responses):
                trace = go.Scattergl(
                    x=df[response],
                    y=df["Z"],
                    mode="markers",
                    name=color,
                    showlegend=idx == 0,
                    marker=self.set_marker_style(color, df),
                    unselected={"marker": self.set_unselected_marker_style(color)},
                    customdata=customdata,
                    hovertemplate=self.hovertemplate,
                    legendgroup=color,
                ).update(marker_size=10)

                row, col = self.layout[idx]
                self._figure.add_trace(trace, row=row, col=col)

    @property
    def colorbar(self) -> dict:
        if self.color_by != "PERMX":
            return {}
        tickvals = list(range(-4, 5, 1))
        return {
            "colorbar": {
                "tickvals": tickvals,
                "ticktext": [10**val for val in tickvals],
            }
        }

    def create_hover_data(self, include_columns: list) -> list:
        # ensure the colorby is the first entry in the list -> used in customdata in callback
        hover_data = [self.color_by]
        for col in include_columns:
            if col not in hover_data:
                hover_data.append(col)
        return hover_data

    def set_marker_style(self, color: str, df: pd.DataFrame) -> dict:
        if not self.discrete_color:
            return {
                "coloraxis": "coloraxis",
                "color": df[self.color_by]
                if self.color_by != "PERMX"
                else np.log10(df[self.color_by]),
            }
        return {"color": self.colormap[color], "opacity": 0.5}

    def set_unselected_marker_style(self, color: str) -> dict:
        if not self.discrete_color:
            return {"opacity": 0.1}
        return {
            "color": rgb_to_str(
                scale_rgb_lightness(hex_to_rgb(self.colormap[color]), 250)
            )
        }

    def add_contacts_to_plot(self) -> None:
        """Annotate axes with named horizontal lines for contacts."""
        for contact in ["OWC", "GWC", "GOC"]:
            if contact in self.dframe and self.dframe["EQLNUM"].nunique() == 1:
                # contacts are assumed constant in the dataframe
                value = self.dframe[contact].values[0]
                # do not include dummy contacts (shallower than the dataset)
                if value > self.dframe["Z"].min():
                    self._figure.add_hline(
                        value,
                        line={"color": "black", "dash": "dash", "width": 1.5},
                        annotation_text=f"{contact}={value:g}",
                        annotation_position="bottom left",
                    )
