from typing import List

import pandas as pd
import webviz_core_components as wcc
from dash import html


def fipfile_qc_main_layout(uuid: str) -> wcc.Frame:
    return html.Div(
        children=[
            html.Div(
                style={"margin-bottom": "20px"},
                children=wcc.RadioItems(
                    vertical=False,
                    id={"id": uuid, "element": "display-option"},
                    options=[
                        {
                            "label": "QC plots",
                            "value": "plots",
                        },
                        {"label": "Table", "value": "table"},
                    ],
                    value="plots",
                ),
            ),
            html.Div(id=uuid),
        ],
    )


def fipfile_qc_selections(
    uuid: str,
    tab: str,
) -> wcc.Selectors:
    return wcc.Selectors(
        label="TABLE COTROLS",
        open_details=True,
        children=wcc.Checklist(
            id={"id": uuid, "tab": tab, "selector": "Group table"},
            options=[
                {"label": "Group table on set", "value": "grouped"},
            ],
            value=["grouped"],
        ),
    )


def fipfile_qc_filters(
    uuid: str, tab: str, disjoint_set_df: pd.DataFrame
) -> wcc.Selectors:
    return wcc.Selectors(
        label="FILTERS",
        open_details=True,
        children=filter_dropdowns(
            uuid=uuid,
            tab=tab,
            disjoint_set_df=disjoint_set_df,
        ),
    )


def filter_dropdowns(uuid: str, disjoint_set_df: pd.DataFrame, tab: str) -> html.Div:
    dropdowns: List[html.Div] = []
    for selector in ["REGION", "ZONE", "FIPNUM", "SET"]:
        elements = list(disjoint_set_df[selector].unique())
        if selector == "FIPNUM":
            elements = sorted(elements, key=int)
        dropdowns.append(
            html.Div(
                children=wcc.SelectWithLabel(
                    label=selector.lower().capitalize(),
                    id={"id": uuid, "tab": tab, "selector": selector, "type": "fipqc"},
                    options=[{"label": i, "value": i} for i in elements],
                    value=elements,
                    multi=True,
                    size=min(15, len(elements)),
                ),
            )
        )
    return html.Div(dropdowns)
