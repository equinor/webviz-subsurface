class PlugInIDs:
    # pylint: disable=too-few-public-methods
    class Stores:
        class BothPlots:
            # pylint: disable=too-few-public-methods
            ENSEMBLE = "ensemble-both"

        class Horizontal:
            # pylint: disable=too-few-public-methods
            PARAMETER = "parameter-horizontal"
            ENSEMBLE = "ensemble-horizontal"

        class Vertical:
            # pylint: disable=too-few-public-methods
            PARAMETER = "parameter-vertical"
            ENSEMBLE = "ensemble-vertical"

        class Options:
            # pylint: disable=too-few-public-methods
            COLOR_BY = "color-by"
            SHOW_SCATTER = "show-scatter"
        
        class Data:
            # pylint: disable=too-few-public-methods
            CLICK_DATA = "click-data"

    class SharedSettings:
        # pylint: disable=too-few-public-methods
        BOTHPLOTS = "both-plots"
        HORIZONTAL = "horiontal"
        VERTICAL = "vertical"
        OPTIONS = "options"

    class ParaCorrGroups:
        # pylint: disable=too-few-public-methods
        GROUPNAME = "parameter-correlation-group"
        PARACORR = "paracorr"