# pylint: disable=too-few-public-methods
class PluginIDs:
    class Stores:
        class DataStores:
            TORNADO_DATA = "tornado-data"
            CLICK_DATA = "click-data"
            HIGH_LOW = "high-low"
            CLIENT_HIGH_PIXELS = "client-height-pixels"
            REFERENCE = " reference"
            RESPONSE = "response"

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
