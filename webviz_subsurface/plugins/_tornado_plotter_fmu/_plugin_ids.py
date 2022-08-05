# pylint: disable=too-few-public-methods
class PlugInIDs:
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

    class TornardoPlotGroup:
        TORNADO_PLOT = "tornado-plot"
        GROUPNAME = "tornardo-plot-group"

    class PlugIn:
        PLUGIN_ID = "plugin-id"
