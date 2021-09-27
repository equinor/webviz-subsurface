from typing import Callable, Dict, List, Union

import webviz_core_components as wcc
from dash import html


def data_selectors_view(
    get_uuid: Callable,
    ensemble_names: List[str],
    data_column_names: List[str],
    parameter_names: List[str],
    initial_data: Dict,
) -> html.Div:
    return wcc.Selectors(
        label="Selectors",
        children=[
            dropdown_for_plotly_data(
                uuid=get_uuid("data_selectors"),
                source="table",
                data_attribute="x",
                title="X-value",
                options=[{"label": col, "value": col} for col in data_column_names],
                value=initial_data.get("x", data_column_names[0]),
            ),
            dropdown_for_plotly_data(
                uuid=get_uuid("data_selectors"),
                source="table",
                data_attribute="y",
                title="Y-value",
                options=[{"label": col, "value": col} for col in data_column_names],
                value=initial_data.get("y", data_column_names[-1]),
            ),
            dropdown_for_plotly_data(
                uuid=get_uuid("data_selectors"),
                source="table",
                data_attribute="ensemble",
                title="Ensemble",
                options=[{"label": col, "value": col} for col in ensemble_names],
                value=initial_data.get("ensembles", [ensemble_names[0]]),
                multi=True,
            ),
            dropdown_for_plotly_data(
                uuid=get_uuid("data_selectors"),
                source="parameter",
                data_attribute="parameter",
                title="Color by",
                options=[{"label": col, "value": col} for col in parameter_names],
                clearable=True,
                placeholder="Default ensemble color",
                value=initial_data.get("parameter"),
            ),
        ],
    )


# pylint: disable=too-many-arguments
def dropdown_for_plotly_data(
    uuid: str,
    source: str,
    data_attribute: str,
    title: str,
    options: List[Dict],
    value: Union[List, str] = None,
    flex: int = 1,
    placeholder: str = "Select...",
    multi: bool = False,
    clearable: bool = False,
) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            wcc.Dropdown(
                label=title,
                id={"id": uuid, "data_attribute": data_attribute, "source": source},
                options=options,
                value=value,
                clearable=clearable,
                placeholder=placeholder,
                multi=multi,
            ),
        ],
    )


def color_scale_dropdown(
    uuid: str,
    title: str,
    options: List[Dict],
    value: Union[List, str] = None,
    flex: int = 1,
    placeholder: str = "Select...",
    multi: bool = False,
    clearable: bool = False,
) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            wcc.Dropdown(
                label=title,
                id=uuid,
                options=options,
                value=value,
                clearable=clearable,
                placeholder=placeholder,
                multi=multi,
            ),
        ],
    )
