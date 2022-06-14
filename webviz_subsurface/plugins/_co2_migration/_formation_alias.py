from typing import List, Set

from webviz_subsurface.plugins._co2_migration._utils import FAULT_POLYGON_ATTRIBUTE
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import \
    WellPickTableColumns


def compile_alias_list(formation_aliases: List[Set[str]], *formation_lists):
    # Identify which formation names can be looked up in all lists
    complete = {
        s for s in formation_lists[0]
        if all(
            lookup_formation_alias(formation_aliases, s, other) is not None
            for other in formation_lists[1:]
        )
    }
    remainder = set.union(*(set(f) for f in formation_lists)) - complete
    options = [{"label": v.title(), "value": v} for v in sorted(list(complete))]
    options += [{"label": "Incomplete data", "value": "", "disabled": True}]
    options += [{"label": v.title(), "value": v} for v in sorted(list(remainder))]
    return options


def surface_name_aliases(surface_provider, prop):
    return [
        s.lower()
        for s in surface_provider.surface_names_for_attribute(prop)
    ]


def fault_polygon_aliases(polygon_provider):
    return [
        p.lower()
        for p in polygon_provider.fault_polygons_names_for_attribute(FAULT_POLYGON_ATTRIBUTE)
    ]


def well_pick_names_aliases(well_pick_provider):
    if well_pick_provider is None:
        return []
    return [
        p.lower()
        for p in well_pick_provider.dframe[WellPickTableColumns.HORIZON].unique()
    ]


def lookup_surface_alias(alias_groups: List[Set[str]], alias, surface_provider, prop):
    return lookup_formation_alias(
        alias_groups,
        alias,
        surface_provider.surface_names_for_attribute(prop),
    )


def lookup_fault_polygon_alias(alias_groups: List[Set[str]], alias, polygon_provider):
    return lookup_formation_alias(
        alias_groups,
        alias,
        polygon_provider.fault_polygons_names_for_attribute(FAULT_POLYGON_ATTRIBUTE),
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
