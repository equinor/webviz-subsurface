# pylint: disable=too-few-public-methods
class PlugInIDs:
    class Tabs:
        QC_PLOTS = "Water Initializaion QC plots"
        MAX_PC_SCALING = "Capillary pressure scaling"
        OVERVIEW = "Overview and Information"

    class Stores:
        class Shared:
            PICK_VIEW = "pick-view"

        class Overview:
            BUTTON = "button"

        class Water:
            QC_VIZ = "qc-viz"
            EQLNUM = "eqlnum"
            COLOR_BY = "color_by"
            MAX_POINTS = "max-points"
            QC_FLAG = "qc-flag"
            SATNUM = "satnum"

        class Capilary:
            SPLIT_TABLE_BY = "split-table-by"
            MAX_PC_SCALE = "max-pc-scale"
            EQLNUM = "eqlnum"

    class SharedSettings:
        PICK_VIEW = "pick-view"
        FILTERS = "filters"

    class SettingsGroups:
        WATER_SEELECTORS = "water-selectors"
        WATER_FILTERS = "water-filters"
        CAPILAR_SELECTORS = "capilar-selectors"
        CAPILAR_FILTERS = "capilar-filters"

    class QcFlags:
        FINE_EQUIL = "FINE_EQUIL"
        HC_BELOW_FWL = "HC_BELOW_FWL"
        PC_SCALED = "PC_SCALED"
        PPCWMAX = "PPCWMAX"
        SWATINIT_1 = "SWATINIT_1"
        SWL_TRUNC = "SWL_TRUNC"
        UNKNOWN = "UNKNOWN"
        WATER = "WATER"

    class SwatinitViews:
        GROUP_NAME = "swatinit-group"

        OVERVIEW = "overview"
        WATER = "water"
        CAPILAR = "capilar"
