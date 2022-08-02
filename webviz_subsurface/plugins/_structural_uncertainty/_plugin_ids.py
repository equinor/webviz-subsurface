class PluginIds:
    # pylint: disable=too-few-public-methods
    class Stores:
        # pylint: disable=too-few-public-methods

        # intersection controls
        SOURCE = "source"
        STORED_POLYLINE = "stored-polyline"
        X_LINE = "x-line"
        MAP_STORED_XLINE = "map-stored-xline"
        Y_LINE = "y-line"
        MAP_STORED_YLINE = "map-stored-yline"
        STEP_X = "step-x"
        STEP_Y = "step-y"
        WELL = "well"
        SURFACE_ATTR = "surface-attr"
        SURFACE_NAMES = "surface-names"
        SHOW_SURFACES = "show-surfaces"
        UPDATE_INTERSECTION = "update-intersection"
        UNCERTAINTY_TABLE = "uncertainty-table"

        # -settings
        RESOLUTION = "resolution"
        EXTENSION = "extension"
        DEPTH_RANGE = "depth-range"
        Z_RANGE_MIN = "z-range-min"
        Z_RANGE_MAX = "z-range-max"
        TRUNKATE_LOCK = "trunkate-lock"
        KEEP_ZOOM = "keep-zoom"
        INTERSECTION_COLORS = "intersection-colors"

        # map controls

        # -surface A
        SURFACE_ATTRIBUTE_A = "surface-attribute-a"
        SURFACE_NAME_A = "surface-name-a"
        CALCULATION_REAL_A = "calculation-real-a"
        CALCULATE_WELL_INTER_A = "calculate-well-inter-a"
        ENSEMBLE_A = "ensemble-a"

        # -surface B
        SURFACE_ATTRIBUTE_B = "surface-attribute-b"
        SURFACE_NAME_B = "surface-name-b"
        CALCULATION_REAL_B = "calculation-real-b"
        CALCULATE_WELL_INTER_B = "calculate-well-inter-b"
        ENSEMBLE_B = "ensemble-b"

        # -settings
        ENSEMBLES = "ensembles"
        AUTO_COMP_DIFF = "auto-comp-diff"
        COLOR_RANGES = "color-ranges"
        SURFACE_A_MIN = "surface-a-min"
        SURFACE_B_MIN = "surface-b-min"
        SURFACE_A_MAX = "surface-a-max"
        SURFACE_B_MAX = "surface-b-max"
        SYNC_RANGE_ON_MAPS = "sync-range-on-maps"

        # -filter
        REAL_FILTER = "real-filter"
        INITIAL_REALS = "initial-reals"
        REAL_STORE = "real-store"

        # Graphs
        INTERSECTION_DATA = "intersection-data"
        FIRST_CALL = "first-call"
        INIT_INTERSECTION_LAYOUT = "init-intersection-layout"
        INTERSECTION_LAYOUT = "intersection-layout"
        COLOR_PICKER = "color-picker"
        STORED_MANUAL_UPDATE_OPTIONS = "stored-manual-update-options"

    class SharedSettings:
        # pylint: disable=too-few-public-methods
        INTERSECTION_CONTROLS = "intersection-controls"
        MAP_CONTROLS = "map-controls"

    class ViewID:
        # pylint: disable=too-few-public-methods

        INTERSECT_POLYLINE = "intersect-polyline"
        INTERSECT_X_LINE = "intersect-x-line"
        INTERSECT_Y_LINE = "intersect-y-line"
        INTERSECT_WELL = "intersect-well"
