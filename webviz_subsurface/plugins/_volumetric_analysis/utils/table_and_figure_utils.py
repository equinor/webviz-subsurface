import math
from typing import List, Optional, Tuple, Union

import numpy as np
import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import dash_table

from webviz_subsurface._abbreviations.number_formatting import si_prefixed
from webviz_subsurface._models import InplaceVolumesModel
from webviz_subsurface._utils.colors import StandardColors

FLUID_COLORS = {
    "oil": StandardColors.OIL_GREEN,
    "gas": StandardColors.GAS_RED,
    "water": StandardColors.WATER_BLUE,
}


def create_table_columns(
    columns: list,
    text_columns: list = None,
    use_si_format: Optional[list] = None,
    use_percentage: Optional[list] = None,
) -> List[dict]:
    text_columns = text_columns if text_columns is not None else []
    use_si_format = use_si_format if use_si_format is not None else []
    use_percentage = use_percentage if use_percentage is not None else []

    table_columns = []
    for col in columns:
        data = {"id": col, "name": col}
        if col not in text_columns:
            data["type"] = "numeric"
            if col in use_percentage:
                data["format"] = {"specifier": ".1f"}
            elif col in use_si_format:
                data["format"] = {"locale": {"symbol": ["", ""]}, "specifier": "$.4s"}
            else:
                data["format"] = {"specifier": ".3~r"}
        table_columns.append(data)
    return table_columns


def create_data_table(
    columns: list,
    height: str,
    data: List[dict],
    table_id: dict,
    selectors: Optional[list] = None,
    style_cell: Optional[dict] = None,
    style_cell_conditional: Optional[list] = None,
    style_data_conditional: Optional[list] = None,
) -> Union[list, wcc.WebvizPluginPlaceholder]:
    if not data:
        return []

    if selectors is None:
        selectors = []
    conditional_cell_style = [
        {
            "if": {"column_id": selectors + ["Response", "Property", "Sensitivity"]},
            "width": "10%",
            "textAlign": "left",
        },
        {"if": {"column_id": "FLUID_ZONE"}, "width": "10%", "textAlign": "right"},
    ]
    if style_cell_conditional is not None:
        conditional_cell_style.extend(style_cell_conditional)

    style_data_conditional = (
        style_data_conditional if style_data_conditional is not None else []
    )
    style_data_conditional.extend(fluid_table_style())

    return wcc.WebvizPluginPlaceholder(
        id={"request": "table_data", "table_id": table_id["table_id"]},
        buttons=["expand", "download"],
        children=dash_table.DataTable(
            id=table_id,
            sort_action="native",
            sort_mode="multi",
            filter_action="native",
            columns=columns,
            data=data,
            style_as_list_view=True,
            style_cell=style_cell,
            style_cell_conditional=conditional_cell_style,
            style_data_conditional=style_data_conditional,
            style_table={
                "height": height,
                "overflowY": "auto",
            },
        ),
    )


def fluid_table_style() -> list:
    return [
        {
            "if": {
                "filter_query": "{FLUID_ZONE} = " + f"'{fluid}'",
                "column_id": "FLUID_ZONE",
            },
            "color": color,
            "fontWeight": "bold",
        }
        for fluid, color in FLUID_COLORS.items()
    ]


def fluid_annotation(selections: dict) -> dict:
    fluid_text = (" + ").join(selections["filters"]["FLUID_ZONE"])

    return {
        "visible": bool(selections["Fluid annotation"])
        and selections["Subplots"] != "FLUID_ZONE",
        "x": 1,
        "y": 1,
        "xref": "paper",
        "yref": "paper",
        "showarrow": False,
        "text": "Fluid zone<br>" + fluid_text,
        "font": {"size": 15, "color": "black"},
        "bgcolor": "#E8E8E8",
    }


def add_correlation_line(figure: go.Figure, xy_min: float, xy_max: float) -> go.Figure:
    return figure.add_shape(
        type="line",
        layer="below",
        xref="x",
        yref="y",
        x0=xy_min,
        y0=xy_min,
        x1=xy_max,
        y1=xy_max,
        line={"color": "black", "width": 2, "dash": "dash"},
    )


def create_figure_matrix(figures: List[go.Figure]) -> List[List[go.Figure]]:
    """Convert a list of figures into a matrix for display"""

    x = math.ceil((math.sqrt(1 + 4 * len(figures)) - 1) / 2)
    figs_in_row = min(x, 20)

    len_of_matrix = figs_in_row * math.ceil(len(figures) / figs_in_row)
    # extend figure list with None to fit size of matrix
    figures.extend([None] * (len_of_matrix - len(figures)))
    return [figures[i : i + figs_in_row] for i in range(0, len_of_matrix, figs_in_row)]


def update_tornado_figures_xaxis(figures: List[go.Figure]) -> None:
    """
    Update the x-axis range for a list of tornado figures with the maximum absolute
    x-value from all figures. Axis will be centered around 0.
    """
    x_absmax = max(max(abs(trace.x)) for fig in figures for trace in fig.data)
    for fig in figures:
        fig.update_layout(xaxis_range=[-x_absmax, x_absmax])


def get_text_format_bar_plot(
    responses: list, selections: dict, volumemodel: InplaceVolumesModel
) -> Union[bool, str]:
    """Get number format for bar plot labels"""
    if not selections["textformat"]:
        return False

    if selections["textformat"] == "default":
        if any(x in responses for x in volumemodel.volume_columns):
            return f".{selections['decimals']}s"
        if any(x in responses for x in volumemodel.property_columns):
            return f".{selections['decimals']}f"

    return f".{selections['decimals']}{selections['textformat']}"


def add_histogram_lines(figure: go.Figure, statline_option: Optional[str]) -> None:
    """Update a histogram figure with vertical lines representing mean/p10/p90"""

    def add_line(
        figure: go.Figure, x: float, text: str, color: str, dash: bool = False
    ) -> None:
        figure.add_vline(
            x=x,
            label={
                "textposition": "end",
                "textangle": 35,
                "font": {"size": 14, "color": color},
                "yanchor": "bottom",
                "xanchor": "right",
                "texttemplate": f"<b>{text}</b>",
            },
            line_width=3,
            line_dash="dash" if dash else None,
            line_color=color,
        )

    if statline_option is not None:
        for trace in figure.data:
            color = trace.marker.line.color
            add_line(figure, x=trace.x.mean(), text="Mean", color=color)
            if statline_option == "all":
                p10 = np.nanpercentile(trace.x, 90)
                p90 = np.nanpercentile(trace.x, 10)
                add_line(figure, x=p10, text="P10", color=color, dash=True)
                add_line(figure, x=p90, text="P90", color=color, dash=True)

        # update margin to make room for the labels
        figure.update_layout({"margin_t": 100})


class VolumeWaterfallPlot:
    def __init__(
        self,
        bar_names: List[str],
        initial_volume: float,
        final_volume: float,
        volume_impact_properties: List[float],
        title: str,
    ) -> None:
        self.bar_names = bar_names
        self.title = title
        self.y = [initial_volume, *volume_impact_properties, final_volume]
        self.cumulative_volumes = self.compute_cumulative_volumes()

    @staticmethod
    def format_number(num: float) -> str:
        """Get a formatted number, use SI prefixes if value is larger than 1000"""
        if abs(num) < 1000:
            return si_prefixed(num, number_format=".1f", locked_si_prefix="")
        return si_prefixed(num, number_format=".3g")

    def compute_cumulative_volumes(self) -> List[float]:
        """
        Compute the cumulative volumes moving from one bar to another.
        First and last bar have volumes in absolute values, the middle
        bars have relative volumes.
        """
        cumulative_volumes = [sum(self.y[:idx]) for idx in range(1, len(self.y))]
        cumulative_volumes.append(self.y[-1])
        return cumulative_volumes

    def calculate_volume_change_for_bar(self, idx: int) -> Tuple[float, float]:
        """
        Calculate change in percent for a given bar index by
        comparing volumes to the previous bar.
        Return the change in actual value and in percent
        """
        prev_bar_volume = self.cumulative_volumes[idx - 1]
        vol_change = self.cumulative_volumes[idx] - prev_bar_volume
        vol_change_percent = (
            (100 * vol_change / prev_bar_volume) if prev_bar_volume != 0 else 0
        )
        return vol_change, vol_change_percent

    @property
    def number_of_bars(self) -> int:
        """Number of bars"""
        return len(self.bar_names)

    @property
    def textfont_size(self) -> int:
        """Text font size for the plot"""
        return 15

    @property
    def measures(self) -> List[str]:
        """
        List of measures. First and last bar have volumes in absolute
        values, the middle bars have relative volumes.
        """
        return ["absolute", *["relative"] * (self.number_of_bars - 2), "absolute"]

    @property
    def y_range(self) -> List[float]:
        """y axis range for the plot"""
        cum_vol_min = min(self.cumulative_volumes)
        cum_vol_max = max(self.cumulative_volumes)
        range_extension = (cum_vol_max - cum_vol_min) / 2
        return [cum_vol_min - range_extension, cum_vol_max + range_extension]

    @property
    def bartext(self) -> List[str]:
        """
        Create bartext for each bar with volume changes relative
        to previous bar. First and last bar show only absolute values.
        """
        texttemplate = [self.format_number(self.y[0])]
        for idx in range(self.number_of_bars):
            if idx not in [0, self.number_of_bars - 1]:
                delta, perc = self.calculate_volume_change_for_bar(idx)
                sign = "+" if perc > 0 else ""
                texttemplate.append(
                    f"{sign}{self.format_number(delta)}  {sign}{perc:.1f}%"
                )
        texttemplate.append(self.format_number(self.y[-1]))
        return texttemplate

    @property
    def axis_defaults(self) -> dict:
        """x and y axis defaults"""
        return {
            "showline": True,
            "linewidth": 2,
            "linecolor": "black",
            "mirror": True,
            "gridwidth": 1,
            "gridcolor": "lightgrey",
            "showgrid": False,
        }

    @property
    def colors(self) -> dict:
        """Color settings for the different bar types"""
        return {
            "decreasing_marker_color": "GoldenRod",
            "increasing_marker_color": "steelblue",
            "totals_marker_color": "darkgrey",
        }

    @property
    def figure(self) -> go.Figure:
        return (
            go.Figure(
                go.Waterfall(
                    orientation="v",
                    measure=self.measures,
                    x=self.bar_names,
                    textposition="outside",
                    text=self.bartext,
                    y=self.y,
                    connector={"mode": "spanning"},
                    textfont_size=self.textfont_size,
                    **self.colors,
                )
            )
            .update_yaxes(
                range=self.y_range,
                tickfont_size=self.textfont_size,
                **self.axis_defaults,
            )
            .update_xaxes(
                type="category",
                tickfont_size=self.textfont_size,
                **self.axis_defaults,
            )
            .update_layout(
                plot_bgcolor="white",
                title=self.title,
                margin={"t": 40, "b": 50, "l": 50, "r": 50},
            )
        )
