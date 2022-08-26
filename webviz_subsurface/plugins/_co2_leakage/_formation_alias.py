from typing import List, Set

from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import \
    WellPickTableColumns


def surface_name_aliases(surface_provider, prop):
    return [
        s.lower()
        for s in surface_provider.surface_names_for_attribute(prop)
    ]


def lookup_surface_alias(alias_groups: List[Set[str]], alias, surface_provider, prop):
    return lookup_formation_alias(
        alias_groups,
        alias,
        surface_provider.surface_names_for_attribute(prop),
    )


def lookup_fault_polygon_alias(alias_groups: List[Set[str]], alias, polygon_provider, fault_polygon_attribute):
    return lookup_formation_alias(
        alias_groups,
        alias,
        polygon_provider.fault_polygons_names_for_attribute(fault_polygon_attribute),
    )


def lookup_well_pick_alias(alias_groups: List[Set[str]], alias, well_pick_provider):
    if well_pick_provider is None:
        return None
    return lookup_formation_alias(
        alias_groups,
        alias,
        well_pick_provider.dframe[WellPickTableColumns.HORIZON].unique()
    )


def lookup_formation_alias(alias_groups: List[Set[str]], alias, names):
    matches = [s for s in names if s.lower() == alias]
    if len(matches) == 0:
        for g in alias_groups:
            if alias not in g:
                continue
            for a in g - {alias}:
                match = lookup_formation_alias([], a, names)
                if match is not None:
                    return match
        return None
    if len(matches) == 0:
        return None
    return matches[0]
