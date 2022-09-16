from webviz_config.utils import StrEnum


class PluginIds:
    # pylint: disable=too-few-public-methods
    class Stores:
        # pylint: disable=too-few-public-methods
        class PlotPicker(StrEnum):
            BARS_OR_TABLE = "bars-table"

        class Selectors(StrEnum):
            RESPONSE = "response"

        class ViewSetttings(StrEnum):
            REFERENCE = "reference"
            SCALE = "scale"
            SENSITIVITIES = "sensitivities"
            RESET = "reset"
            PLOT_OPTIONS = "plot-options"
            LABEL = "label"

        class DataStores(StrEnum):
            TORNADO_DATA = "tornado-data"
            CLICK_DATA = "click-data"
            HIGH_LOW = "high-low"
            CLIENT_HIGH_PIXELS = "client-height-pixels"

    class SharedSettings(StrEnum):
        PLOTPICKER = "plotpicker"
        SELECTORS = "selectors"
        FILTERS = "filters"
        VIEW_SETTINGS = "view-settings"

    class TornadoViewGroup(StrEnum):
        TORNADO_PLOT_VIEW = "tornado-plot-view"
        TORNADO_TABLE_VIEW = "tornado-table-view"

    class Plugin(StrEnum):
        PLUGIN_ID = "plugin-id"
