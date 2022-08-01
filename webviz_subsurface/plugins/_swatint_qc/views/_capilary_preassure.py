class TabMaxPcInfoLayout:
    def __init__(self, get_uuid: Callable, datamodel: SwatinitQcDataModel) -> None:
        self.datamodel = datamodel
        self.get_uuid = get_uuid

    def main_layout(
        self, dframe: pd.DataFrame, selectors: list, map_figure: go.Figure
    ) -> html.Div:
        return html.Div(
            children=[
                wcc.Header(
                    "Maximum capillary pressure scaling", style=LayoutStyle.HEADER
                ),
                wcc.FlexBox(
                    style={"margin-top": "10px", "height": "40vh"},
                    children=[
                        wcc.FlexColumn(
                            dcc.Markdown(pc_columns_description()),
                            flex=7,
                            style={"margin-right": "40px"},
                        ),
                        wcc.FlexColumn(
                            FullScreen(
                                wcc.Graph(
                                    style={"height": "100%", "min-height": "35vh"},
                                    figure=map_figure,
                                )
                            ),
                            flex=3,
                        ),
                    ],
                ),
                self.create_max_pc_table(dframe, text_columns=selectors),
            ]
        )

    @property
    def selections_layout(self) -> html.Div:
        return html.Div(
            children=[
                wcc.Selectors(
                    label="Selections",
                    children=[
                        html.Div(
                            wcc.RadioItems(
                                label="Split table by:",
                                id=self.get_uuid(LayoutElements.GROUPBY_EQLNUM),
                                options=[
                                    {"label": "SATNUM", "value": "SATNUM"},
                                    {"label": "SATNUM and EQLNUM", "value": "both"},
                                ],
                                value="SATNUM",
                            ),
                            style={"margin-bottom": "10px"},
                        ),
                        self.scaling_threshold,
                    ],
                ),
                wcc.Selectors(
                    label="Filters",
                    children=[
                        wcc.SelectWithLabel(
                            label="EQLNUM",
                            id=self.get_uuid(LayoutElements.TABLE_EQLNUM_SELECTOR),
                            options=[
                                {"label": ens, "value": ens}
                                for ens in self.datamodel.eqlnums
                            ],
                            value=self.datamodel.eqlnums,
                            size=min(8, len(self.datamodel.eqlnums)),
                            multi=True,
                        ),
                        range_filters(
                            self.get_uuid(LayoutElements.FILTERS_CONTINOUS_MAX_PC),
                            self.datamodel,
                        ),
                    ],
                ),
            ]
        )

    def create_max_pc_table(
        self, dframe: pd.DataFrame, text_columns: list
    ) -> dash_table:
        return DashTable(
            data=dframe.to_dict("records"),
            columns=[
                {
                    "name": i,
                    "id": i,
                    "type": "numeric" if i not in text_columns else "text",
                    "format": {"specifier": ".4~r"} if i not in text_columns else {},
                }
                for i in dframe.columns
            ],
            height="48vh",
            sort_action="native",
            fixed_rows={"headers": True},
            style_cell={
                "minWidth": LayoutStyle.TABLE_CELL_WIDTH,
                "maxWidth": LayoutStyle.TABLE_CELL_WIDTH,
                "width": LayoutStyle.TABLE_CELL_WIDTH,
            },
            style_data_conditional=[
                {
                    "if": {
                        "filter_query": f"{{{self.datamodel.COLNAME_THRESHOLD}}} > 0",
                    },
                    **LayoutStyle.TABLE_HIGHLIGHT,
                },
            ],
        )

    @property
    def scaling_threshold(self) -> html.Div:
        return html.Div(
            style={"margin-top": "10px"},
            children=[
                wcc.Label("Maximum PC_SCALING threshold"),
                html.Div(
                    dcc.Input(
                        id=self.get_uuid(LayoutElements.HIGHLIGHT_ABOVE),
                        type="number",
                        persistence=True,
                        persistence_type="session",
                    )
                ),
            ],
        )


# pylint: disable=anomalous-backslash-in-string
def pc_columns_description() -> str:  # tekst i figuren på siste side
    return f"""
> **Column descriptions**
> - **PCOW_MAX**  - Maximum capillary pressure from the input SWOF/SWFN tables
> - **PC_SCALING**  - Maximum capillary pressure scaling applied
> - **PPCW**  - Maximum capillary pressure after scaling
> - **{SwatinitQcDataModel.COLNAME_THRESHOLD}**  - Column showing how many percent of the pc-scaled dataset that match the user-selected threshold
*PPCW = PCOW_MAX \* PC_SCALING*
A threshold for the maximum capillary scaling can be set in the menu.
The table will show how many percent of the dataset that exceeds this value, and cells above the threshold will be shown in the map ➡️
"""
