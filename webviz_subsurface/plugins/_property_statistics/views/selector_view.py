from typing import Union, TYPE_CHECKING

import dash_html_components as html
import webviz_core_components as wcc

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from ..property_statistics import PropertyStatistics


def ensemble_selector(
    parent: "PropertyStatistics", tab: str, multi: bool = False, value: str = None
) -> html.Div:
    return wcc.Dropdown(
        label="Ensemble",
        id={"id": parent.uuid("ensemble-selector"), "tab": tab},
        options=[{"label": ens, "value": ens} for ens in parent.pmodel.ensembles],
        multi=multi,
        value=value if value is not None else parent.pmodel.ensembles[0],
        clearable=False,
    )


def delta_ensemble_selector(
    parent: "PropertyStatistics", tab: str, multi: bool = False
) -> html.Div:
    return wcc.Dropdown(
        label="Delta Ensemble",
        id={"id": parent.uuid("delta-ensemble-selector"), "tab": tab},
        options=[{"label": ens, "value": ens} for ens in parent.pmodel.ensembles],
        multi=multi,
        value=parent.pmodel.ensembles[-1],
        clearable=False,
    )


def property_selector(
    parent: "PropertyStatistics", tab: str, multi: bool = False, value: str = None
) -> html.Div:
    display = "none" if len(parent.pmodel.properties) < 2 else "inline"
    return html.Div(
        style={"display": display},
        children=[
            wcc.Dropdown(
                label="Property",
                id={"id": parent.uuid("property-selector"), "tab": tab},
                options=[
                    {"label": prop, "value": prop} for prop in parent.pmodel.properties
                ],
                multi=multi,
                value=value if value is not None else parent.pmodel.properties[0],
                clearable=False,
            )
        ],
    )


def source_selector(
    parent: "PropertyStatistics", tab: str, multi: bool = False, value: str = None
) -> html.Div:
    display = "none" if len(parent.pmodel.sources) < 2 else "inline"
    return html.Div(
        style={"display": display},
        children=[
            wcc.Dropdown(
                label="Source",
                id={"id": parent.uuid("source-selector"), "tab": tab},
                options=[
                    {"label": source, "value": source}
                    for source in parent.pmodel.sources
                ],
                multi=multi,
                value=value if value is not None else parent.pmodel.sources[0],
                clearable=False,
            ),
        ],
    )


def make_filter(
    parent: "PropertyStatistics",
    tab: str,
    df_column: str,
    column_values: list,
    multi: bool = True,
    value: Union[str, float] = None,
) -> html.Div:
    return wcc.SelectWithLabel(
        label=df_column.lower().capitalize(),
        id={
            "id": parent.uuid("filter-selector"),
            "tab": tab,
            "selector": df_column,
        },
        options=[{"label": i, "value": i} for i in column_values],
        value=[value] if value is not None else column_values,
        multi=multi,
        size=min(20, len(column_values)),
    )


def filter_selector(
    parent: "PropertyStatistics",
    tab: str,
    multi: bool = True,
    value: Union[str, float] = None,
) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                children=[
                    make_filter(
                        parent=parent,
                        tab=tab,
                        df_column=sel,
                        column_values=parent.pmodel.selector_values(sel),
                        multi=multi,
                        value=value,
                    )
                    for sel in parent.pmodel.selectors
                ]
            ),
        ]
    )
