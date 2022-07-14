class PluginIds:
 
    # pylint: disable=too-few-public-methods
    class Stores:
        GRAPH_DATA_HAS_CHANGED_TRIGGER = (
        "graph_data_has_changed_trigger"  # NOTE: To force re-render of graph
    )
        ENSEMBLES_DROPDOWN = "ensembles_dropdown"
        ENSEMBLES_DROPDOWN_OPTIONS = "ensembles_dropdown-options"
        VECTOR_SELECTOR = "vector_selector"

        VECTOR_CALCULATOR = "vector_calculator"
        VECTOR_CALCULATOR_DIALOG = "vector_calculator_dialog"
        VECTOR_CALCULATOR_OPEN_BUTTON = "vector_calculator_open_button"
        VECTOR_CALCULATOR_EXPRESSIONS = "vector_calculator_expressions"
        VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG = (
            "vector_calculator_expressions_open_dialog"
        )

        DELTA_ENSEMBLE_A_DROPDOWN = "delta_ensemble_A_dropdown"
        DELTA_ENSEMBLE_B_DROPDOWN = "delta_ensemble_B_dropdown"
        DELTA_ENSEMBLE_CREATE_BUTTON = "delta_ensemble_create_button"
        CREATED_DELTA_ENSEMBLES = "created_delta_ensemble_names"
        CREATED_DELTA_ENSEMBLE_NAMES_TABLE = "created_delta_ensemble_names_table"
        CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN = (
            "created_delta_ensemble_names_table_column"
        )

        RELATIVE_DATE_DROPDOWN = "relative_date_dropdown"

        VISUALIZATION_RADIO_ITEMS = "visualization_radio_items"

        PLOT_FANCHART_OPTIONS_CHECKLIST = "plot_fanchart_options_checklist"
        PLOT_STATISTICS_OPTIONS_CHECKLIST = "plot_statistics_options_checklist"
        PLOT_TRACE_OPTIONS_CHECKLIST = "plot_trace_options_checklist"

        SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS = "subplot_owner_options_radio_items"

        RESAMPLING_FREQUENCY_DROPDOWN = "resampling_frequency_dropdown"

        REALIZATIONS_FILTER_OPTION = "realizations_filter_option"
        REALIZATIONS_FILTER_SELECTOR = "realizations_filter_selector"
        REALIZATIONS_FILTER_SLIDER = "realizations_filter_slider"
        REALIZATIONS_FILTER_SPAN = "realizations_filter_span"
        STATISTICS_FROM_RADIO_ITEMS = "statistics_from_radio_items"

        TOUR_STEP_MAIN_LAYOUT = "tour_step_main_layout"
        TOUR_STEP_SETTINGS_LAYOUT = "tour_step_settings_layout"
        TOUR_STEP_GROUP_BY = "tour_step_group_by"
        TOUR_STEP_DELTA_ENSEMBLE = "tour_step_delta_ensemble"
        TOUR_STEP_OPTIONS = "tour_step_options"

    # pylint: disable=too-few-public-methods
    class SharedSettings:
        SIMULATIONTIMESERIESSETTINGS = "simulation-time-series-settings"


    # pylint: disable=too-few-public-methods
    class SimulationTimeSeries:
        GROUP_NAME = "simulation-time-series"
        VIEW_NAME = "simulation-time-series-view"