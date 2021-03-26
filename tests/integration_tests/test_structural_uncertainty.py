import json

import dash_html_components as html
from dash.dependencies import Input, Output, State
from webviz_config.themes import default_theme
from webviz_config import WebvizSettings

# pylint: disable=no-name-in-module
from webviz_config.plugins import (
    StructuralUncertainty,
)

# pylint: enable=no-name-in-module


def stringify_object_id(uuid) -> str:
    """Object ids must be sorted and converted to
    css strings to be recognized as dom elements"""
    sorted_uuid_obj = json.loads(
        json.dumps(
            uuid,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    string = ["{"]
    for idx, (key, value) in enumerate(sorted_uuid_obj.items()):
        string.append(f'\\"{key}\\"\\:\\"{value}\\"\\')
        if idx == len(sorted_uuid_obj) - 1:
            string.append("}")
        else:
            string.append(",")
    return ("").join(string)


def test_default_configuration(dash_duo, app, testdata_folder) -> None:
    webviz_settings = WebvizSettings(
        shared_settings={
            "scratch_ensembles": {
                "iter-0": str(
                    testdata_folder / "reek_history_match/realization-*/iter-0"
                )
            }
        },
        theme=default_theme,
    )
    plugin = StructuralUncertainty(
        app,
        webviz_settings,
        ensembles=["iter-0"],
        surface_attributes=["ds_extracted_horizons"],
        surface_name_filter=[
            "topupperreek",
            "topmidreek",
            "toplowerreek",
            "baselowerreek",
        ],
        wellfolder=testdata_folder / "observed_data" / "wells",
    )

    app.layout = plugin.layout
    dash_duo.start_server(app)

    intersection_data_id = plugin.uuid("intersection-data")
    modal_id = plugin.uuid("modal")
    # Check some initialization
    # Check dropdowns
    for element, return_val in zip(
        ["well", "surface_attribute"], ["OP_1", "ds_extracted_horizons"]
    ):
        uuid = stringify_object_id(
            uuid={"element": element, "id": intersection_data_id}
        )
        assert dash_duo.wait_for_element(f"#\\{uuid} .Select-value").text == return_val

    # Check Selects
    for element, return_val in zip(
        ["surface_names"],
        [["topupperreek", "topmidreek", "toplowerreek", "baselowerreek"]],
    ):
        uuid = stringify_object_id(
            uuid={"element": element, "id": intersection_data_id}
        )
        assert (
            dash_duo.wait_for_element(f"#\\{uuid} select").text.splitlines()
            == return_val
        )

    # Check Calculation checkbox
    uuid = stringify_object_id(
        uuid={"element": "calculation", "id": intersection_data_id}
    )
    calculation_element = dash_duo.driver.find_elements_by_css_selector(
        f"#\\{uuid} > label > input"
    )
    assert len(calculation_element) == len(
        ["Min", "Max", "Mean", "Realizations", "Uncertainty envelope"]
    )
    for checkbox, selected in zip(
        calculation_element,
        ["true", "true", "true", None, None],
    ):
        assert checkbox.get_attribute("selected") == selected

    # Check realizations
    real_filter_btn_uuid = stringify_object_id(
        {
            "id": modal_id,
            "modal_id": "realization-filter",
            "element": "button-open",
        }
    )
    real_uuid = stringify_object_id(
        uuid={"element": "realizations", "id": intersection_data_id}
    )

    ### Open realization filter and check realizations
    dash_duo.wait_for_element_by_id(real_filter_btn_uuid).click()
    real_selector = dash_duo.wait_for_element_by_id(real_uuid)
    assert real_selector.text.splitlines() == [
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
    ]

    assert dash_duo.get_logs() == [], "browser console should contain no error"


def test_full_configuration(dash_duo, app, testdata_folder) -> None:
    webviz_settings = WebvizSettings(
        shared_settings={
            "scratch_ensembles": {
                "iter-0": str(
                    testdata_folder / "reek_history_match/realization-*/iter-0"
                ),
                "iter-1": str(
                    testdata_folder / "reek_history_match/realization-*/iter-1"
                ),
                "iter-2": str(
                    testdata_folder / "reek_history_match/realization-*/iter-2"
                ),
                "iter-3": str(
                    testdata_folder / "reek_history_match/realization-*/iter-3"
                ),
            }
        },
        theme=default_theme,
    )
    plugin = StructuralUncertainty(
        app,
        webviz_settings,
        ensembles=["iter-0", "iter-1", "iter-2", "iter-3"],
        surface_attributes=["ds_extracted_horizons"],
        surface_name_filter=[
            "topupperreek",
            "topmidreek",
            "toplowerreek",
            "baselowerreek",
        ],
        wellfolder=testdata_folder / "observed_data" / "wells",
        zonelog="Zonelog",
        initial_settings={
            "intersection_data": {
                "surface_names": ["topupperreek", "topmidreek", "baselowerreek"],
                "surface_attribute": "ds_extracted_horizons",
                "ensembles": [
                    "iter-0",
                    "iter-1",
                ],
                "calculation": ["Mean", "Min", "Max"],
                # - Uncertainty envelope
                "well": "OP_6",
                "realizations": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                "colors": {
                    "topupperreek": {"iter-0": "#2C82C9", "iter-1": "#2CC990"},
                    "topmidreek": {
                        "iter-0": "#512E34",
                        "iter-1": "#7D93C1",
                    },
                    "baselowerreek": {
                        "iter-0": "#EEE657",
                        "iter-1": "#FC6042",
                    },
                },
            },
            "intersection_layout": {
                "yaxis": {
                    "range": [1700, 1550],
                    "title": "True vertical depth [m]",
                },
                "xaxis": {"title": "Lateral distance [m]"},
            },
        },
    )

    app.layout = plugin.layout

    # Injecting a div that will be updated when the plot data stores are
    # changed. Since the plot data are stored in LocalStorage and Selenium
    # has no functionality to wait for LocalStorage to equal some value we
    # instead populate this injected div with some data before we check the content
    # of Localstorage.
    @app.callback(
        Output(plugin.uuid("layout"), "children"),
        Input(plugin.uuid("intersection-graph-layout"), "data"),
        State(plugin.uuid("layout"), "children"),
    )
    def _add_or_update_div(data, children):
        plot_is_updated = html.Div(
            id=plugin.uuid("plot_is_updated"), children=data.get("title")
        )
        if len(children) == 6:
            children[5] = plot_is_updated
        else:
            children.append(plot_is_updated)

        return children

    dash_duo.start_server(app)

    intersection_data_id = plugin.uuid("intersection-data")

    # Check some initialization
    # Check dropdowns
    for element, return_val in zip(
        ["well", "surface_attribute"], ["OP_6", "ds_extracted_horizons"]
    ):
        uuid = stringify_object_id(
            uuid={"element": element, "id": intersection_data_id}
        )
        assert dash_duo.wait_for_text_to_equal(f"#\\{uuid} .Select-value", return_val)

    # Wait for the callbacks to execute
    dash_duo.wait_for_text_to_equal(
        f'#{plugin.uuid("plot_is_updated")}', "Intersection along well: OP_6"
    )

    # Check that graph data is stored
    graph_data = dash_duo.get_session_storage(plugin.uuid("intersection-graph-data"))
    assert len(graph_data) == 22
    graph_layout = dash_duo.get_session_storage(
        plugin.uuid("intersection-graph-layout")
    )
    assert isinstance(graph_layout, dict)
    assert graph_layout.get("title") == "Intersection along well: OP_6"

    ### Change well and check graph
    well_uuid = stringify_object_id(
        uuid={"element": "well", "id": intersection_data_id}
    )

    apply_btn = dash_duo.wait_for_element_by_id(
        plugin.uuid("apply-intersection-data-selections")
    )
    well_dropdown = dash_duo.wait_for_element_by_id(well_uuid)
    dash_duo.select_dcc_dropdown(well_dropdown, value="OP_1")
    apply_btn.click()

    # dash_duo.wait_for_text_to_equal(
    #     f'#{plugin.uuid("plot_is_updated")}',
    #     "Intersection along well: OP_6",
    #     timeout=100,
    # )
    graph_layout = dash_duo.get_session_storage(
        plugin.uuid("intersection-graph-layout")
    )
    # assert graph_layout.get("title") == "Intersection along well: OP_1"
    assert dash_duo.get_logs() == [], "browser console should contain no error"
