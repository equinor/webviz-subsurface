import dataclasses
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import xtgeo
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkCommonCore import reference, vtkIdList, vtkPoints
from vtkmodules.vtkCommonDataModel import (
    vtkCellArray,
    vtkCellLocator,
    vtkExplicitStructuredGrid,
    vtkGenericCell,
    vtkLine,
    vtkPlane,
    vtkPolyData,
    vtkStaticCellLocator,
    vtkUnstructuredGrid,
)
from vtkmodules.vtkFiltersCore import (
    vtkAppendPolyData,
    vtkExplicitStructuredGridCrop,
    vtkExplicitStructuredGridToUnstructuredGrid,
    vtkPlaneCutter,
    vtkClipPolyData,
    vtkUnstructuredGridToExplicitStructuredGrid,
)
from vtkmodules.vtkFiltersGeneral import vtkBoxClipDataSet
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

        grid = worker.get_full_esgrid()

        if cell_filter:
            grid = _calc_cropped_grid(grid, cell_filter)

        polydata = _calc_grid_surface(grid)

        # !!!!!!
        # Need to watch out here, think these may go out of scope!
        points_np = vtk_to_numpy(polydata.GetPoints().GetData()).ravel()
        polys_np = vtk_to_numpy(polydata.GetPolys().GetData())
        original_cell_indices_np = vtk_to_numpy(
            polydata.GetCellData().GetAbstractArray("vtkOriginalCellIds")
        )

        surface_polys = SurfacePolys(point_arr=points_np, poly_arr=polys_np)

        property_scalars: Optional[PropertyScalars] = None
        if property_spec:
            raw_cell_vals = _load_property_values(provider, realization, property_spec)
            if raw_cell_vals is not None:
                mapped_cell_vals = raw_cell_vals[original_cell_indices_np]
                property_scalars = PropertyScalars(value_arr=mapped_cell_vals)

        worker.set_cached_original_cell_indices(cell_filter, original_cell_indices_np)

        LOGGER.debug(
            f"Got grid surface in {timer.elapsed_s():.2f}s "
            f"(provider_id={provider_id}, real={realization}, "
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

        raw_cell_vals = _load_property_values(provider, realization, property_spec)
        if raw_cell_vals is None:
            LOGGER.warning(
                f"No cell values found for "
                f"prop=({property_spec.prop_name}, {property_spec.prop_name})"
            )
            return None

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

        mapped_cell_vals = raw_cell_vals[original_cell_indices_np]

        LOGGER.debug(
            f"Got property values in {timer.elapsed_s():.2f}s "
            f"(provider_id={provider_id}, real={realization}, "
            f"{_property_spec_dbg_str(property_spec)}, "
            f"{_cell_filter_dbg_str(cell_filter)})"
        )

        return PropertyScalars(value_arr=mapped_cell_vals)

    # -----------------------------------------------------------------------------
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

        bounds = esgrid.GetBounds()
        min_z = bounds[4]
        max_z = bounds[5]

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
            x0 = polyline_xy[2 * i]
            y0 = polyline_xy[2 * i + 1]
            x1 = polyline_xy[2 * (i + 1)]
            y1 = polyline_xy[2 * (i + 1) + 1]
            fwd_vec = np.array([x1 - x0, y1 - y0, 0.0])
            fwd_vec /= np.linalg.norm(fwd_vec)
            right_vec = np.array([fwd_vec[1], -fwd_vec[0], 0])

            # box_clip_alg.SetBoxClip(x0, x1, y0, y1, min_z, max_z)
            # box_clip_alg.Update()
            # clipped_ugrid = box_clip_alg.GetOutputDataObject(0)

            # polyline_bounds = _calc_polyline_bounds([x0, y0, x1, y1])
            # polyline_bounds.extend([min_z, max_z])
            # cell_ids = vtkIdList()
            # cell_locator.FindCellsWithinBounds(polyline_bounds, cell_ids)
            # print(f"{cell_ids.GetNumberOfIds()}  {polyline_bounds=}")

            plane = vtkPlane()
            plane.SetOrigin([x0, y0, 0])
            plane.SetNormal(right_vec)

            plane_0 = vtkPlane()
            plane_0.SetOrigin([x0, y0, 0])
            plane_0.SetNormal(fwd_vec)

            plane_1 = vtkPlane()
            plane_1.SetOrigin([x1, y1, 0])
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
            f"setup={et_setup_s:.2f}s, cut={et_cut_s:.2f}s, clip={et_clip_s:.2f}s, combine={et_combine_s:.2f}s, "
            f"(provider_id={provider_id}, real={realization})"
        )

        return surface_polys, property_scalars

        """
        dbg_point_arr = []
        dbg_conn_arr = []
        for i in range(0, num_points_in_polyline):
            x = polyline_xy[2 * i]
            y = polyline_xy[2 * i + 1]
            dbg_point_arr.extend([x, y, min_z])
            dbg_point_arr.extend([x, y, max_z])
            if i > 0:
                base = 2 * (i - 1)
                dbg_conn_arr.extend([4, base, base + 2, base + 3, base + 1])

        for i in range(0, int(len(dbg_point_arr) / 3)):
            print(
                f"{i}: {dbg_point_arr[3*i]}, {dbg_point_arr[3*i + 1]}, {dbg_point_arr[3*i + 2]}"
            )

        point_arr_np = np.array(dbg_point_arr).reshape(-1, 3)
        conn_arr_np = np.array(dbg_conn_arr)
        surface_polys = SurfacePolys(point_arr=point_arr_np, poly_arr=conn_arr_np)

        return surface_polys, None
        """

    # -----------------------------------------------------------------------------
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

        cell_id, isect_pt = _raypick_in_grid(grid, ray)
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

        worker_key = f"P{provider_id}__R{realization}"
        worker = self._key_to_worker_dict.get(worker_key)
        if worker:
            return worker

        provider = self._id_to_provider_dict.get(provider_id)
        if not provider:
            raise ValueError("Could not find provider")

        xtg_grid = provider.get_3dgrid(realization=realization)
        vtk_esg = xtgeo_grid_to_vtk_explicit_structured_grid(xtg_grid)

        worker = GridWorker(vtk_esg)
        self._key_to_worker_dict[worker_key] = worker

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
    t_ref = reference(0.0)
    isect_pt = [0.0, 0.0, 0.0]
    pcoords = [0.0, 0.0, 0.0]
    sub_id_ref = reference(0)
    cell_id_ref = reference(0)
    cell = vtkGenericCell()

    # From doc for vtkCell it seems that isect_pt will be the actual intersection point
    # while pcoords is in parametric coordinates
    anyHits = locator.IntersectWithLine(
        ray.origin,
        ray.end,
        tolerance,
        t_ref,
        isect_pt,
        pcoords,
        sub_id_ref,
        cell_id_ref,
        cell,
    )

    if not anyHits:
        return None

    return cell_id_ref.get(), isect_pt


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
    if property_spec.prop_date:
        prop_values = provider.get_dynamic_property_values(
            property_spec.prop_name, property_spec.prop_date, realization
        )
    else:
        prop_values = provider.get_static_property_values(
            property_spec.prop_name, realization
        )

    return prop_values


# -----------------------------------------------------------------------------
def _vtk_esg_to_ug(vtk_esgrid: vtkExplicitStructuredGrid) -> vtkUnstructuredGrid:
    convertFilter = vtkExplicitStructuredGridToUnstructuredGrid()
    convertFilter.SetInputData(vtk_esgrid)
    convertFilter.Update()
    vtk_ugrid = convertFilter.GetOutput()

    return vtk_ugrid


# -----------------------------------------------------------------------------
def _vtk_ug_to_esg(vtk_ugrid: vtkUnstructuredGrid) -> vtkExplicitStructuredGrid:
    convertFilter = vtkUnstructuredGridToExplicitStructuredGrid()
    convertFilter.SetInputData(vtk_ugrid)
    convertFilter.SetInputArrayToProcess(0, 0, 0, 1, "BLOCK_I")
    convertFilter.SetInputArrayToProcess(1, 0, 0, 1, "BLOCK_J")
    convertFilter.SetInputArrayToProcess(2, 0, 0, 1, "BLOCK_K")
    convertFilter.Update()
    vtk_esgrid = convertFilter.GetOutput()

    return vtk_esgrid


# -----------------------------------------------------------------------------
def _calc_polyline_bounds(polyline_xy: List[float]) -> List[float]:
    num_points = int(len(polyline_xy) / 2)
    if num_points < 1:
        return None

    min_x = min(polyline_xy[0::2])
    max_x = max(polyline_xy[0::2])
    min_y = min(polyline_xy[1::2])
    max_y = max(polyline_xy[1::2])

    return [min_x, max_x, min_y, max_y]


# -----------------------------------------------------------------------------
def _extract_intersected_ugrid(
    ugrid: vtkUnstructuredGrid, polyline_xy_in: List[float], max_point_dist: float
) -> vtkUnstructuredGrid:

    # Requires VTK 9.2
    from vtkmodules.vtkFiltersCore import vtkExtractCellsAlongPolyLine

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

    polyData = vtkPolyData()
    polyData.SetPoints(points)
    polyData.SetLines(lines)

    et_build_s = timer.lap_s()

    extractor = vtkExtractCellsAlongPolyLine()
    extractor.SetInputData(0, ugrid)
    extractor.SetInputData(1, polyData)
    extractor.Update()

    ret_grid = extractor.GetOutput(0)

    et_extract_s = timer.lap_s()

    LOGGER.debug(
        f"extraction with {num_points_in_polyline} points took {timer.elapsed_s():.2f}s "
        f"(resample={et_resample_s:.2f}s, build={et_build_s:.2f}s, extract={et_extract_s:.2f}s)"
    )

    return ret_grid


# -----------------------------------------------------------------------------
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
            n = int(length / max_point_dist)
            delta_t = 1.0 / (n + 1)
            for j in range(0, n):
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
