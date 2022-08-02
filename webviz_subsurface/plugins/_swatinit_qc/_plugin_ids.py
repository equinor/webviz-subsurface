class PlugInIDs:
    # pylint: disable=too-few-public-methods
    class Tabs:
        # pylint: disable=too-few-public-methods
        QC_PLOTS = "Water Initializaion QC plots"
        MAX_PC_SCALING = "Capillary pressure scaling"
        OVERVIEW = "Overview and Information"

    class Stores:
        # pylint: disable=too-few-public-methods
        class Shared:
            # pylint: disable=too-few-public-methods
            PICK_VIEW = "pick-view"
            EQLNUM = "eqlnum"

        class Overview:
            # pylint: disable=too-few-public-methods
            BUTTON = "button"

        class Water:
            # pylint: disable=too-few-public-methods
            QC_VIZ = "qc-viz"
            EQLNUM = "eqlnum"
            COLOR_BY = "color_by"
            MAX_POINTS = "max-points"
            QC_FLAG = "qc-flag"
            STANUM = "satnum"

        class Capilary:
            # pylint: disable=too-few-public-methods
            SPLIT_TABLE_BY = "split-table-by"
            MAX_PC_SCALE = "max-pc-scale"

    class SharedSettings:
        # pylint: disable=too-few-public-methods
        PICK_VIEW = "pick-view"
        FILTERS = "filters"

    class QcFlags:
        # pylint: disable=too-few-public-methods
        FINE_EQUIL = "FINE_EQUIL"
        HC_BELOW_FWL = "HC_BELOW_FWL"
        PC_SCALED = "PC_SCALED"
        PPCWMAX = "PPCWMAX"
        SWATINIT_1 = "SWATINIT_1"
        SWL_TRUNC = "SWL_TRUNC"
        UNKNOWN = "UNKNOWN"
        WATER = "WATER"

    class ViewGroups:
        # pylint: disable=too-few-public-methods
        class Overview:
            # pylint: disable=too-few-public-methods
            OVERVIEW_TAB = "overview-tab"
            GROUP_NAME = "overview-group"

        class Water:
            # pylint: disable=too-few-public-methods
            WATER_TAB = "water-tab"
            GROUP_NAME = "group-name"

        class Capilar:
            # pylint: disable=too-few-public-methods
            CAPILAR_TAB = "capilar-tab"
            GROUP_NAEME = "group-name"
