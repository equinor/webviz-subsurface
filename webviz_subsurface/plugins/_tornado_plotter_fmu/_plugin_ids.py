# pylint: disable=too-few-public-methods
class PluginIDs:
    class Stores:
        class PlotPicker:
            BARS_OR_TABLE = "bars-table"

        class Selectors:
            RESPONSE = "response"

        class ViewSetttings:
            REFERENCE = "reference"
            SCALE = "scale"
            SENSITIVITIES = "sensitivities"
            RESET = "reset"
            PLOT_OPTIONS = "plot-options"
            LABEL = "label"

        class DataStores:
            TORNADO_DATA = "tornado-data"
            CLICK_DATA = "click-data"
            HIGH_LOW = "high-low"
            CLIENT_HIGH_PIXELS = "client-height-pixels"

    class SharedSettings:
        PLOTPICKER = "plotpicker"
        SELECTORS = "selectors"
        FILTERS = "filters"
        VIEW_SETTINGS = "view-settings"

    class TornadoViewGroup:
        TORNADO_PLOT_VIEW = "tornado-plot-view"
        TORNADO_TABLE_VIEW = "tornado-table-view"

    class PlugIn:
        PLUGIN_ID = "plugin-id"
