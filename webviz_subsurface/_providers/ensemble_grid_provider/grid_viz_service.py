import dataclasses
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from vtkmodules.util.numpy_support import vtk_to_numpy

# pylint: disable=no-name-in-module,
from vtkmodules.vtkCommonCore import reference, vtkIdList, vtkPoints

# pylint: disable=no-name-in-module,
from vtkmodules.vtkCommonDataModel import (
    vtkCellArray,
    vtkCellLocator,
    vtkExplicitStructuredGrid,
    vtkLine,
    vtkPlane,
    vtkPolyData,
    vtkUnstructuredGrid,
)

# Requires VTK 9.2
from vtkmodules.vtkFiltersCore import (
    vtkAppendPolyData,
    vtkClipPolyData,
    vtkExplicitStructuredGridCrop,
    vtkExplicitStructuredGridToUnstructuredGrid,
    vtkExtractCellsAlongPolyLine,
    vtkPlaneCutter,
    vtkUnstructuredGridToExplicitStructuredGrid,
)
from vtkmodules.vtkFiltersGeometry import vtkExplicitStructuredGridSurfaceFilter

from webviz_subsurface._utils.perf_timer import PerfTimer

# Requires updated xtgeo
from ._xtgeo_to_vtk_explicit_structured_grid import (
    xtgeo_grid_to_vtk_explicit_structured_grid,
)
from .ensemble_grid_provider import EnsembleGridProvider

LOGGER = logging.getLogger(__name__)

_GRID_VIZ_SERVICE_INSTANCE: Optional["GridVizService"] = None


@dataclass
class PropertySpec:
    prop_name: str
    prop_date: Optional[str]


@dataclass
class CellFilter:
    i_min: int
    i_max: int
    j_min: int
    j_max: int
    k_min: int
    k_max: int


@dataclass
class SurfacePolys:
    point_arr: np.ndarray
    poly_arr: np.ndarray


@dataclass
class PropertyScalars:
    value_arr: np.ndarray
    # min_value: float
    # max_value: float


@dataclass
class Ray:
    origin: List[float]
    end: List[float]
    # direction: List[float]


@dataclass
class PickResult:
    cell_index: int
    cell_i: int
    cell_j: int
    cell_k: int
    intersection_point: List[float]
    cell_property_value: Optional[float]


# =============================================================================
class GridWorker:
    # -----------------------------------------------------------------------------
    def __init__(self, full_esgrid: vtkExplicitStructuredGrid) -> None:
        self._full_esgrid = full_esgrid

        self._cached_cell_filter: Optional[CellFilter] = None
        self._cached_original_cell_indices: Optional[np.ndarray] = None

    # -----------------------------------------------------------------------------
    def get_full_esgrid(self) -> vtkExplicitStructuredGrid:
        return self._full_esgrid

    # -----------------------------------------------------------------------------
    def get_cached_original_cell_indices(
        self, cell_filter: Optional[CellFilter]
    ) -> Optional[np.ndarray]:
        if self._cached_original_cell_indices is None:
            return None

        if cell_filter == self._cached_cell_filter:
            return self._cached_original_cell_indices

        return None

    # -----------------------------------------------------------------------------
    def set_cached_original_cell_indices(
        self, cell_filter: Optional[CellFilter], original_cell_indices: np.ndarray
    ) -> None:
        # Make copy of the cell filter
        self._cached_cell_filter = dataclasses.replace(cell_filter)
        self._cached_original_cell_indices = original_cell_indices


# =============================================================================
class GridVizService:
    # -----------------------------------------------------------------------------
    def __init__(self) -> None:
        self._id_to_provider_dict: Dict[str, EnsembleGridProvider] = {}
        self._key_to_worker_dict: Dict[str, GridWorker] = {}

    # -----------------------------------------------------------------------------
    @staticmethod
    def instance() -> "GridVizService":
        # pylint: disable=global-statement,
        global _GRID_VIZ_SERVICE_INSTANCE
        if not _GRID_VIZ_SERVICE_INSTANCE:
            LOGGER.debug("Initializing GridVizService instance")
            _GRID_VIZ_SERVICE_INSTANCE = GridVizService()

        return _GRID_VIZ_SERVICE_INSTANCE

    # -----------------------------------------------------------------------------
    def register_provider(self, provider: EnsembleGridProvider) -> None:
        provider_id = provider.provider_id()
        LOGGER.debug(f"Adding grid provider with id={provider_id}")

        existing_provider = self._id_to_provider_dict.get(provider_id)
        if existing_provider:
            # Issue a warning if there already is a provider registered with the same
            # id AND if the actual provider instance is different.
            # This wil happen until the provider factory gets caching.
            if existing_provider is not provider:
                LOGGER.warning(
                    f"Provider with id={provider_id} ignored, the id is already present"
                )
                return

        self._id_to_provider_dict[provider_id] = provider

    # -----------------------------------------------------------------------------
    # pylint: disable=too-many-locals,
    def get_surface(
        self,
        provider_id: str,
        realization: int,
        property_spec: Optional[PropertySpec],
        cell_filter: Optional[CellFilter],
    ) -> Tuple[SurfacePolys, Optional[PropertyScalars]]:

        LOGGER.debug(
            f"Getting grid surface... "
            f"(provider_id={provider_id}, real={realization}, "
            f"{_property_spec_dbg_str(property_spec)}, "
            f"{_cell_filter_dbg_str(cell_filter)})"
        )
        timer = PerfTimer()

        provider = self._id_to_provider_dict.get(provider_id)
        if not provider:
            raise ValueError("Could not find provider")

        worker = self._get_or_create_grid_worker(provider_id, realization)
        if not worker:
            raise ValueError("Could not get grid worker")
        et_get_grid_worker_ms = timer.lap_ms()

        grid = worker.get_full_esgrid()

        if cell_filter:
            grid = _calc_cropped_grid(grid, cell_filter)
        et_crop_grid_ms = timer.lap_ms()

        polydata = _calc_grid_surface(grid)

        # !!!!!!
        # Need to watch out here, think these may go out of scope!
        points_np = vtk_to_numpy(polydata.GetPoints().GetData()).ravel()
        polys_np = vtk_to_numpy(polydata.GetPolys().GetData())
        original_cell_indices_np = vtk_to_numpy(
            polydata.GetCellData().GetAbstractArray("vtkOriginalCellIds")
        )

        surface_polys = SurfacePolys(point_arr=points_np, poly_arr=polys_np)
        et_calc_surf_ms = timer.lap_ms()

        property_scalars: Optional[PropertyScalars] = None
        if property_spec:
            raw_cell_vals = _load_property_values(provider, realization, property_spec)
            if raw_cell_vals is not None:
                mapped_cell_vals = raw_cell_vals[original_cell_indices_np]
                property_scalars = PropertyScalars(value_arr=mapped_cell_vals)
        et_read_and_map_scalars_ms = timer.lap_ms()

        worker.set_cached_original_cell_indices(cell_filter, original_cell_indices_np)

        LOGGER.debug(
            f"Got grid surface in {timer.elapsed_s():.2f}s "
            f"(get_grid_worker={et_get_grid_worker_ms}ms, "
            f"crop_grid={et_crop_grid_ms}ms, "
            f"calc_surf={et_calc_surf_ms}ms, "
            f"read_and_map_scalars={et_read_and_map_scalars_ms}ms, "
            f"provider_id={provider_id}, real={realization}, "
            f"{_property_spec_dbg_str(property_spec)}, "
            f"{_cell_filter_dbg_str(cell_filter)})"
        )

        return surface_polys, property_scalars

    # -----------------------------------------------------------------------------
    def get_mapped_property_values(
        self,
        provider_id: str,
        realization: int,
        property_spec: PropertySpec,
        cell_filter: Optional[CellFilter],
    ) -> Optional[PropertyScalars]:

        LOGGER.debug(
            f"Getting property values... "
            f"(provider_id={provider_id}, real={realization}, "
            f"{_property_spec_dbg_str(property_spec)}, "
            f"{_cell_filter_dbg_str(cell_filter)})"
        )
        timer = PerfTimer()

        provider = self._id_to_provider_dict.get(provider_id)
        if not provider:
            raise ValueError("Could not find provider")

        worker = self._get_or_create_grid_worker(provider_id, realization)
        if not worker:
            raise ValueError("Could not get grid worker")
        et_get_grid_worker_ms = timer.lap_ms()

        original_cell_indices_np = worker.get_cached_original_cell_indices(cell_filter)
        if original_cell_indices_np is None:
            # Must first generate the grid to get the original cell indices
            grid = worker.get_full_esgrid()
            if cell_filter:
                grid = _calc_cropped_grid(grid, cell_filter)

            polydata = _calc_grid_surface(grid)
            original_cell_indices_np = vtk_to_numpy(
                polydata.GetCellData().GetAbstractArray("vtkOriginalCellIds")
            )
            worker.set_cached_original_cell_indices(
                cell_filter, original_cell_indices_np
            )
        et_get_mapping_indices_ms = timer.lap_ms()

        raw_cell_vals = _load_property_values(provider, realization, property_spec)
        if raw_cell_vals is None:
            LOGGER.warning(
                f"No cell values found for "
                f"prop=({property_spec.prop_name}, {property_spec.prop_name})"
            )
            return None

        mapped_cell_vals = raw_cell_vals[original_cell_indices_np]
        et_read_and_map_scalars_ms = timer.lap_ms()

        LOGGER.debug(
            f"Got property values in {timer.elapsed_s():.2f}s "
            f"(get_grid_worker={et_get_grid_worker_ms}ms, "
            f"get_mapping_indices={et_get_mapping_indices_ms}ms, "
            f"read_and_map_scalars={et_read_and_map_scalars_ms}ms, "
            f"provider_id={provider_id}, real={realization}, "
            f"{_property_spec_dbg_str(property_spec)}, "
            f"{_cell_filter_dbg_str(cell_filter)})"
        )

        return PropertyScalars(value_arr=mapped_cell_vals)

    # -----------------------------------------------------------------------------
    # pylint: disable=too-many-locals,too-many-statements
    def cut_along_polyline(
        self,
        provider_id: str,
        realization: int,
        polyline_xy: List[float],
        property_spec: Optional[PropertySpec],
    ) -> Tuple[SurfacePolys, Optional[PropertyScalars]]:

        LOGGER.debug(
            f"Cutting along polyline... "
            f"(provider_id={provider_id}, real={realization})"
        )
        timer = PerfTimer()

        provider = self._id_to_provider_dict.get(provider_id)
        if not provider:
            raise ValueError("Could not find provider")

        worker = self._get_or_create_grid_worker(provider_id, realization)
        if not worker:
            raise ValueError("Could not get grid worker")

        esgrid = worker.get_full_esgrid()

        num_points_in_polyline = int(len(polyline_xy) / 2)

        ugrid = _vtk_esg_to_ug(esgrid)

        # !!!!!!!!!!!!!!
        # Requires VTK 9.2-ish
        # ugrid = _extract_intersected_ugrid(ugrid, polyline_xy, 10.0)

        cutter_alg = vtkPlaneCutter()
        cutter_alg.SetInputDataObject(ugrid)

        # cell_locator = vtkStaticCellLocator()
        # cell_locator.SetDataSet(esgrid)
        # cell_locator.BuildLocator()

        # box_clip_alg = vtkBoxClipDataSet()
        # box_clip_alg.SetInputDataObject(ugrid)

        append_alg = vtkAppendPolyData()
        et_setup_s = timer.lap_s()

        et_cut_s = 0.0
        et_clip_s = 0.0

        for i in range(0, num_points_in_polyline - 1):
            x_0 = polyline_xy[2 * i]
            y_0 = polyline_xy[2 * i + 1]
            x_1 = polyline_xy[2 * (i + 1)]
            y_1 = polyline_xy[2 * (i + 1) + 1]
            fwd_vec = np.array([x_1 - x_0, y_1 - y_0, 0.0])
            fwd_vec /= np.linalg.norm(fwd_vec)
            right_vec = np.array([fwd_vec[1], -fwd_vec[0], 0])

            # box_clip_alg.SetBoxClip(x_0, x_1, y_0, y_1, min_z, max_z)
            # box_clip_alg.Update()
            # clipped_ugrid = box_clip_alg.GetOutputDataObject(0)

            # polyline_bounds = _calc_polyline_bounds([x_0, y_0, x_1, y_1])
            # polyline_bounds.extend([min_z, max_z])
            # cell_ids = vtkIdList()
            # cell_locator.FindCellsWithinBounds(polyline_bounds, cell_ids)
            # print(f"{cell_ids.GetNumberOfIds()}  {polyline_bounds=}")

            plane = vtkPlane()
            plane.SetOrigin([x_0, y_0, 0])
            plane.SetNormal(right_vec)

            plane_0 = vtkPlane()
            plane_0.SetOrigin([x_0, y_0, 0])
            plane_0.SetNormal(fwd_vec)

            plane_1 = vtkPlane()
            plane_1.SetOrigin([x_1, y_1, 0])
            plane_1.SetNormal(-fwd_vec)

            cutter_alg.SetPlane(plane)
            cutter_alg.Update()

            cut_surface_polydata = cutter_alg.GetOutput()
            # print(f"{type(cut_surface_polydata)=}")
            et_cut_s += timer.lap_s()

            # Used vtkPolyDataPlaneClipper earlier, but it seems that it doesn't
            # maintain the original cell IDs that we need for the result mapping.
            # May want to check up on any performance degradation!
            clipper_0 = vtkClipPolyData()
            clipper_0.SetInputDataObject(cut_surface_polydata)
            clipper_0.SetClipFunction(plane_0)
            clipper_0.Update()
            clipped_polydata = clipper_0.GetOutput()

            clipper_1 = vtkClipPolyData()
            clipper_1.SetInputDataObject(clipped_polydata)
            clipper_1.SetClipFunction(plane_1)
            clipper_1.Update()
            clipped_polydata = clipper_1.GetOutput()

            append_alg.AddInputData(clipped_polydata)

            et_clip_s += timer.lap_s()

        append_alg.Update()
        comb_polydata = append_alg.GetOutput()
        et_combine_s = timer.lap_s()

        points_np = vtk_to_numpy(comb_polydata.GetPoints().GetData()).ravel()
        polys_np = vtk_to_numpy(comb_polydata.GetPolys().GetData())

        surface_polys = SurfacePolys(point_arr=points_np, poly_arr=polys_np)

        property_scalars: Optional[PropertyScalars] = None
        if property_spec:
            raw_cell_vals = _load_property_values(provider, realization, property_spec)
            if raw_cell_vals is not None:
                original_cell_indices_np = vtk_to_numpy(
                    comb_polydata.GetCellData().GetAbstractArray("vtkOriginalCellIds")
                )
                mapped_cell_vals = raw_cell_vals[original_cell_indices_np]
                property_scalars = PropertyScalars(value_arr=mapped_cell_vals)

        LOGGER.debug(
            f"Cutting along polyline done in {timer.elapsed_s():.2f}s "
            f"setup={et_setup_s:.2f}s, cut={et_cut_s:.2f}s, clip={et_clip_s:.2f}s "
            f"combine={et_combine_s:.2f}s, "
            f"(provider_id={provider_id}, real={realization})"
        )

        return surface_polys, property_scalars

    # -----------------------------------------------------------------------------
    # pylint: disable=too-many-locals,
    def ray_pick(
        self,
        provider_id: str,
        realization: int,
        ray: Ray,
        property_spec: Optional[PropertySpec],
        cell_filter: Optional[CellFilter],
    ) -> Optional[PickResult]:

        LOGGER.debug(
            f"Doing ray pick: "
            f"ray.origin={ray.origin}, ray.end={ray.end}, "
            f"(provider_id={provider_id}, real={realization}, "
            f"{_property_spec_dbg_str(property_spec)}, "
            f"{_cell_filter_dbg_str(cell_filter)})"
        )
        timer = PerfTimer()

        provider = self._id_to_provider_dict.get(provider_id)
        if not provider:
            raise ValueError("Could not find provider")

        worker = self._get_or_create_grid_worker(provider_id, realization)
        if not worker:
            raise ValueError("Could not get grid worker")

        grid = worker.get_full_esgrid()
        if cell_filter:
            grid = _calc_cropped_grid(grid, cell_filter)
        et_crop_s = timer.lap_s()

        cell_id, isect_pt = _raypick_in_grid(grid, ray)  # type:ignore
        et_pick_s = timer.lap_s()
        if cell_id is None:
            return None

        original_cell_id = cell_id
        if cell_filter:
            # If a cell filter is present, assume picking was done against cropped grid
            original_cell_id = (
                grid.GetCellData()
                .GetAbstractArray("vtkOriginalCellIds")
                .GetValue(cell_id)
            )

        i_ref = reference(0)
        j_ref = reference(0)
        k_ref = reference(0)
        grid.ComputeCellStructuredCoords(cell_id, i_ref, j_ref, k_ref, True)

        cell_property_val: Optional[float] = None
        if property_spec:
            raw_cell_vals = _load_property_values(provider, realization, property_spec)
            if raw_cell_vals is not None:
                cell_property_val = raw_cell_vals[original_cell_id]
        et_props_s = timer.lap_s()

        LOGGER.debug(
            f"Did ray pick in {timer.elapsed_s():.2f}s ("
            f"crop={et_crop_s:.2f}s, pick={et_pick_s:.2f}s, props={et_props_s:.2f}s, "
            f"provider_id={provider_id}, real={realization}, "
            f"{_property_spec_dbg_str(property_spec)}, "
            f"{_cell_filter_dbg_str(cell_filter)})"
        )

        return PickResult(
            cell_index=original_cell_id,
            cell_i=i_ref.get(),
            cell_j=j_ref.get(),
            cell_k=k_ref.get(),
            intersection_point=isect_pt,
            cell_property_value=cell_property_val,
        )

    # -----------------------------------------------------------------------------
    def _get_or_create_grid_worker(
        self, provider_id: str, realization: int
    ) -> Optional[GridWorker]:

        timer = PerfTimer()

        worker_key = f"P{provider_id}__R{realization}"
        worker = self._key_to_worker_dict.get(worker_key)
        if worker:
            LOGGER.debug("_get_or_create_grid_worker() returning cached data")
            return worker

        provider = self._id_to_provider_dict.get(provider_id)
        if not provider:
            raise ValueError("Could not find provider")

        LOGGER.debug("_get_or_create_grid_worker() data not in cache, loading...")

        xtg_grid = provider.get_3dgrid(realization=realization)
        et_xtgeo_grid_from_provider_grid_ms = timer.lap_ms()

        cell_count = xtg_grid.ncol * xtg_grid.nrow * xtg_grid.nlay
        LOGGER.debug(f"_get_or_create_grid_worker() grid cell count: {cell_count}")

        vtk_esg = xtgeo_grid_to_vtk_explicit_structured_grid(xtg_grid)
        et_create_vtk_esg_ms = timer.lap_ms()

        worker = GridWorker(vtk_esg)
        self._key_to_worker_dict[worker_key] = worker

        LOGGER.debug(
            f"_get_or_create_grid_worker() loaded data in {timer.elapsed_s():.2f}s "
            f"(xtgeo_grid_from_provider_grid={et_xtgeo_grid_from_provider_grid_ms}ms, "
            f"create_vtk_esg={et_create_vtk_esg_ms}ms)"
        )

        return worker


# -----------------------------------------------------------------------------
def _calc_cropped_grid(
    esgrid: vtkExplicitStructuredGrid, cell_filter: CellFilter
) -> vtkExplicitStructuredGrid:
    crop_filter = vtkExplicitStructuredGridCrop()
    crop_filter.SetInputData(esgrid)

    # In VTK dimensions correspond to points
    crop_filter.SetOutputWholeExtent(
        cell_filter.i_min,
        cell_filter.i_max + 1,
        cell_filter.j_min,
        cell_filter.j_max + 1,
        cell_filter.k_min,
        cell_filter.k_max + 1,
    )
    crop_filter.Update()
    cropped_grid = crop_filter.GetOutput()
    return cropped_grid


# -----------------------------------------------------------------------------
def _raypick_in_grid(
    esgrid: vtkExplicitStructuredGrid, ray: Ray
) -> Optional[Tuple[int, List[float]]]:
    """Do a ray pick against the specified grid.
    Returns None if nothing was hit, otherwise returns the cellId (cell index) of the cell
    that was hit and the intersection point
    """

    locator = vtkCellLocator()
    locator.SetDataSet(esgrid)
    locator.BuildLocator()

    tolerance = 0.0
    vtk_isect_points = vtkPoints()
    vtk_cell_ids_list = vtkIdList()

    # Initially we used another vtkGenericCell.IntersectWithLine() overload here that
    # only returned the best hit. However it seems that as of 9.2.0rc2, that function is
    # broken since it seemingly doesn't return the closest hit.
    # For now we try and use another overload that returns all hits, sorted by distance.
    # There is also an overload without the tol argument, but it doesn't seem to work.
    any_hits = locator.IntersectWithLine(
        ray.origin, ray.end, tolerance, vtk_isect_points, vtk_cell_ids_list
    )
    # print(f"{any_hits=}")
    # print(f"{vtk_isect_points.GetPoint(0)}")
    # print(f"{vtk_cell_ids_list.GetId(0)}")

    if any_hits != 1:
        return None

    num_points = vtk_isect_points.GetNumberOfPoints()
    num_ids = vtk_cell_ids_list.GetNumberOfIds()
    if num_points == 0 or num_ids == 0:
        raise ValueError("Raypick got a hit, but no points or Ids were returned")

    isect_pt = list(vtk_isect_points.GetPoint(0))
    cell_id = vtk_cell_ids_list.GetId(0)

    return cell_id, isect_pt


# -----------------------------------------------------------------------------
def _calc_grid_surface(esgrid: vtkExplicitStructuredGrid) -> vtkPolyData:
    surf_filter = vtkExplicitStructuredGridSurfaceFilter()
    surf_filter.SetInputData(esgrid)
    surf_filter.PassThroughCellIdsOn()
    surf_filter.Update()

    polydata: vtkPolyData = surf_filter.GetOutput()
    return polydata


# -----------------------------------------------------------------------------
def _load_property_values(
    provider: EnsembleGridProvider, realization: int, property_spec: PropertySpec
) -> Optional[np.ndarray]:
    timer = PerfTimer()

    if property_spec.prop_date:
        prop_values = provider.get_dynamic_property_values(
            property_spec.prop_name, property_spec.prop_date, realization
        )
    else:
        prop_values = provider.get_static_property_values(
            property_spec.prop_name, realization
        )

    LOGGER.debug(
        f"_load_property_values() took {timer.elapsed_s():.2f}s "
        f"({_property_spec_dbg_str(property_spec)})"
    )

    return prop_values


# -----------------------------------------------------------------------------
def _vtk_esg_to_ug(vtk_esgrid: vtkExplicitStructuredGrid) -> vtkUnstructuredGrid:
    convert_filter = vtkExplicitStructuredGridToUnstructuredGrid()
    convert_filter.SetInputData(vtk_esgrid)
    convert_filter.Update()
    vtk_ugrid = convert_filter.GetOutput()

    return vtk_ugrid


# -----------------------------------------------------------------------------
def _vtk_ug_to_esg(vtk_ugrid: vtkUnstructuredGrid) -> vtkExplicitStructuredGrid:
    convert_filter = vtkUnstructuredGridToExplicitStructuredGrid()
    convert_filter.SetInputData(vtk_ugrid)
    convert_filter.SetInputArrayToProcess(0, 0, 0, 1, "BLOCK_I")
    convert_filter.SetInputArrayToProcess(1, 0, 0, 1, "BLOCK_J")
    convert_filter.SetInputArrayToProcess(2, 0, 0, 1, "BLOCK_K")
    convert_filter.Update()
    vtk_esgrid = convert_filter.GetOutput()

    return vtk_esgrid


# -----------------------------------------------------------------------------
def _calc_polyline_bounds(polyline_xy: List[float]) -> Optional[List[float]]:
    num_points = int(len(polyline_xy) / 2)
    if num_points < 1:
        return None

    min_x = min(polyline_xy[0::2])
    max_x = max(polyline_xy[0::2])
    min_y = min(polyline_xy[1::2])
    max_y = max(polyline_xy[1::2])

    return [min_x, max_x, min_y, max_y]


# -----------------------------------------------------------------------------
# pylint: disable=too-many-locals,
def _extract_intersected_ugrid(
    ugrid: vtkUnstructuredGrid, polyline_xy_in: List[float], max_point_dist: float
) -> vtkUnstructuredGrid:

    timer = PerfTimer()

    polyline_xy = _resample_polyline(polyline_xy_in, max_point_dist)
    et_resample_s = timer.lap_s()

    num_points_in_polyline = int(len(polyline_xy) / 2)
    if num_points_in_polyline < 1:
        return ugrid

    bounds = ugrid.GetBounds()
    min_z = bounds[4]
    max_z = bounds[5]

    points = vtkPoints()
    lines = vtkCellArray()

    for i in range(0, num_points_in_polyline):
        x = polyline_xy[2 * i]
        y = polyline_xy[2 * i + 1]

        points.InsertNextPoint([x, y, min_z])
        points.InsertNextPoint([x, y, max_z])

        line = vtkLine()
        line.GetPointIds().SetId(0, 2 * i)
        line.GetPointIds().SetId(1, 2 * i + 1)

        lines.InsertNextCell(line)

    poly_data = vtkPolyData()
    poly_data.SetPoints(points)
    poly_data.SetLines(lines)

    et_build_s = timer.lap_s()

    extractor = vtkExtractCellsAlongPolyLine()
    extractor.SetInputData(0, ugrid)
    extractor.SetInputData(1, poly_data)
    extractor.Update()

    ret_grid = extractor.GetOutput(0)

    et_extract_s = timer.lap_s()

    LOGGER.debug(
        f"extraction with {num_points_in_polyline} points took {timer.elapsed_s():.2f}s "
        f"(resample={et_resample_s:.2f}s, build={et_build_s:.2f}s, extract={et_extract_s:.2f}s)"
    )

    return ret_grid


# -----------------------------------------------------------------------------
# pylint: disable=too-many-locals,
def _resample_polyline(polyline_xy: List[float], max_point_dist: float) -> List[float]:
    num_points = int(len(polyline_xy) / 2)
    if num_points < 2:
        return polyline_xy

    ret_polyline = []

    prev_x = polyline_xy[0]
    prev_y = polyline_xy[1]
    ret_polyline.extend([prev_x, prev_y])

    for i in range(1, num_points):
        x = polyline_xy[2 * i]
        y = polyline_xy[2 * i + 1]

        fwd = [x - prev_x, y - prev_y]
        length = np.linalg.norm(fwd)
        if length > max_point_dist:
            n_length = int(length / max_point_dist)
            delta_t = 1.0 / (n_length + 1)
            for j in range(0, n_length):
                pt_x = prev_x + fwd[0] * (j + 1) * delta_t
                pt_y = prev_y + fwd[1] * (j + 1) * delta_t
                ret_polyline.extend([pt_x, pt_y])

        ret_polyline.extend([x, y])
        prev_x = x
        prev_y = y

    return ret_polyline


# -----------------------------------------------------------------------------
def _property_spec_dbg_str(property_spec: Optional[PropertySpec]) -> str:
    if not property_spec:
        return "prop=None"

    return f"prop=({property_spec.prop_name}, {property_spec.prop_date})"


# -----------------------------------------------------------------------------
def _cell_filter_dbg_str(cell_filter: Optional[CellFilter]) -> str:
    if not cell_filter:
        return "IJK=None"

    return (
        f"I=[{cell_filter.i_min},{cell_filter.i_max}] "
        f"J=[{cell_filter.j_min},{cell_filter.j_max}] "
        f"K=[{cell_filter.k_min},{cell_filter.k_max}]"
    )
