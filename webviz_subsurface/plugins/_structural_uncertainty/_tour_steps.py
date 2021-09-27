from typing import Callable, Dict, List


def generate_tour_steps(get_uuid: Callable) -> List[Dict]:
    """Returns a list of reactour steps"""
    return [
        {
            "id": f"{get_uuid('layout')}",
            "content": ("Dashboard to analyze structural uncertainty from FMU results"),
        },
        {
            "id": f"{get_uuid('intersection-graph')}",
            "content": (
                "Intersection view displaying realizations or statistics of ensemble "
                "surfaces along a well trajectory or polyline. "
                "Zonation logs, if available, are represented as markers at each "
                "zone transition."
            ),
        },
        {
            "id": f"{get_uuid('intersection-source-wrapper')}",
            "content": (
                "Source of the intersection. Digitized polyline "
                "from a map or from a well trajectory (If wells are available)."
            ),
        },
        {
            "id": f"{get_uuid('all-maps-wrapper')}",
            "content": (
                "Map view displaying individiual surfaces. The left and center view "
                "are selecteable, while the right view displays the difference (left-center)."
                "Well markers for the displayed surface can be calculated on-the-fly and can "
                "be interacted with to update the intersection view."
            ),
        },
        {
            "id": f"{get_uuid('map-wrapper')} .leaflet-draw-draw-polyline",
            "content": (
                "Activate to draw a polyline on the map that will be displayed "
                "in the intersection view."
            ),
        },
        {
            "id": f"{get_uuid('intersection-data-wrapper')}",
            "content": ("Data used to populate the intersection view"),
        },
        {
            "id": f"{get_uuid('apply-intersection-data-selections')}",
            "content": (
                "Applies current changes " "and updates the intersection graph"
            ),
        },
        {
            "id": f"{get_uuid('surface-settings-wrapper')}",
            "content": (
                "Opens a panel for selecting data to display in " "the map views"
            ),
        },
        {
            "id": f"{get_uuid('realization-filter-wrapper')}",
            "content": (
                "Opens a panel to a global realization filter "
                "Statistics and available realizations in both "
                "the intersection view and the map views will "
                "use this filter."
            ),
        },
        {
            "id": f"{get_uuid('uncertainty-table-display-button')}",
            "content": (
                "Opens a panel to calculate surface intersection statistics "
                "for the active well (Not in use when no wells are available"
            ),
        },
    ]
