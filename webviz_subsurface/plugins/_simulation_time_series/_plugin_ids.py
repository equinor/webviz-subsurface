class PluginIds:

    # pylint: disable=too-few-public-methods
    class Stores:
        SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS = "subplot_owner_options_radio_items"
        ENSEMBLES_DROPDOWN = "ensembles_dropdown"
        RELATIVE_DATE_DROPDOWN = "relative_date_dropdown"
        RESAMPLING_FREQUENCY_DROPDOWN = "resampling_frequency_dropdown"
        CREATED_DELTA_ENSEMBLES = "created_delta_ensemble_names"
        ENSEMBLES_DROPDOWN_OPTIONS = "ensembles_dropdown-options"
        VECTOR_SELECTOR = "vector_selector"
        GRAPH_DATA_HAS_CHANGED_TRIGGER = (
            "graph_data_has_changed_trigger"  # NOTE: To force re-render of graph
        )
        VECTOR_CALCULATOR_EXPRESSIONS = "vector_calculator_expressions"
        VISUALIZATION_RADIO_ITEMS = "visualization_radio_items"
        PLOT_FANCHART_OPTIONS_CHECKLIST = "plot_fanchart_options_checklist"
        PLOT_STATISTICS_OPTIONS_CHECKLIST = "plot_statistics_options_checklist"
        PLOT_TRACE_OPTIONS_CHECKLIST = "plot_trace_options_checklist"
        REALIZATIONS_FILTER_SELECTOR = "realizations_filter_selector"
        STATISTICS_FROM_RADIO_ITEMS = "statistics_from_radio_items"
        REALIZATIONS_FILTER_SELECTOR_ID = "realizations_filter_selector_id"

    # pylint: disable=too-few-public-methods
    class SharedSettings:
        GROUP_BY = "group_by"
        RESAMPLING_FREQUENCY = "resampling-frequency"
        ENSEMBLES = "ensembles"
        TIME_SERIES = "time-series"
        VISUALIZATION = "visualization"
        FILTER_REALIZATION = "filter-realization"

    # pylint: disable=too-few-public-methods
    class SimulationTimeSeries:
        GROUP_NAME = "simulation-time-series"
        VIEW_NAME = "simulation-time-series-view"

    # pylint: disable=too-few-public-methods
    class TourStepIds:
        DELTA_ENSEMBLE = "delta-ensemble"
        OPTIONS = "options"
