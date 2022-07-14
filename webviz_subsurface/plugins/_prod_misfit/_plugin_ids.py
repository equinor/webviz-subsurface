class PluginIds:
    # pylint: disable=too-few-public-methods
    class Stores:
        # pylint: disable=too-few-public-methods
        SELECTED_ENSEMBLES = "selected-ensembles"
        SELECTED_DATES = "selected-dates"
        SELECTED_PHASE = "selected-phase"
        SELECTED_WELLS = "selected-wells"
        SELECTED_COMBINE_WELLS_COLLECTION = "selected-combine-wells-collection"
        SELECTED_WELL_COLLECTIONS = "selected-well-collections"
        SELECTED_REALIZATIONS = "selected-realizations"

        SELECTED_FIG_LAYOUT_HEIGHT = "selected-fig-layout-height"

    class SharedSettings:
        # pylint: disable=too-few-public-methods
        FILTER = "filter"

    class MisfitViews:
        # pylint: disable=too-few-public-methods
        GROUP_NAME = "Misfit analysis"

        PRODUCTION_MISFIT_PER_REAL = "production-misfit-per-real"
        WELL_PRODUCTION_COVERAGE = "well-production-coverage"
        WELL_PRODUCTION_HEATMAP = "well-production-heatmap"
