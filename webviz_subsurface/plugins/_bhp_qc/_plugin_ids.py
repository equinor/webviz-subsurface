from webviz_config.utils import StrEnum


class PluginIds:  # pylint: disable=too-few-public-methods
    class Stores(StrEnum):
        SELECTED_ENSEMBLE = "selected-ensemble"
        SELECTED_WELLS = "selected-wells"
        SELECTED_MAX_NUMBER_OF_WELLS = "selected-max-number-of-wells"
        SELECTED_SORT_BY = "selected-sort-by"
        SELECTED_ASCENDING_DESCENDING = "selected-ascending-descending"
        SELECTED_STATISTICS = "selected-statistics"

    class SharedSettings(StrEnum):
        FILTER = "filter"
        VIEW_SETTINGS = "view-settings"

    class BhpId(StrEnum):
        LINE_CHART = "line-chart"
        FAN_CHART = "fan-chart"
        BAR_CHART = "bar-chart"
