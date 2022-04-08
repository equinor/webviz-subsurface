import pytest

from vtkmodules.vtkCommonDataModel import vtkCellLocator
from vtkmodules.vtkCommonCore import vtkIdList
import pyvista as pv

from webviz_subsurface.plugins._eclipse_grid_viewer._explicit_structured_grid_accessor import (
    ExplicitStructuredGridAccessor,
)
from ._utils import create_explicit_structured_grid


ES_GRID_ACCESSOR = ExplicitStructuredGridAccessor(
    create_explicit_structured_grid(5, 4, 3, 20.0, 10.0, 5.0)
)

CROP_FIRST_CELL = [0, 0], [0, 0], [0, 0]
EXPECTED_FIRST_CELL_ORIGINAL_INDEX = [0]
CROP_LAST_CELL = [5, 5], [4, 4], [3, 3]
EXPECTED_LAST_CELL_ORIGINAL_INDEX = [59]
CROP_BOX = [2, 3], [2, 3], [1, 2]
EXPECTED_CROP_BOX_ORIGINAL_INDEX = [32, 33, 37, 38, 52, 53, 57, 58]


@pytest.mark.parametrize(
    "crop_range, expected_cells",
    [
        (CROP_FIRST_CELL, EXPECTED_FIRST_CELL_ORIGINAL_INDEX),
        (CROP_LAST_CELL, EXPECTED_LAST_CELL_ORIGINAL_INDEX),
        (CROP_BOX, EXPECTED_CROP_BOX_ORIGINAL_INDEX),
    ],
)
def test_crop(crop_range, expected_cells) -> None:
    cropped_grid = ES_GRID_ACCESSOR.crop(*crop_range)
    assert isinstance(cropped_grid, pv.ExplicitStructuredGrid)
    assert "vtkOriginalCellIds" in cropped_grid.array_names
    assert set(cropped_grid["vtkOriginalCellIds"]) == set(expected_cells)
    _polys, _points, indices = ES_GRID_ACCESSOR.extract_skin(cropped_grid)
    assert set(indices) == set(expected_cells)


RAY_FROM_TOP = [
    [50, 15, 15],
    [50, 15, -5],
]
RAY_FROM_BOTTOM = [
    [50, 15, -5],
    [50, 15, 20],
]
RAY_FROM_I = [[50, -7, 13], [50, 45, 13]]
RAY_FROM_J = [[-12, 5, 13], [110, 5, 13]]


@pytest.mark.parametrize(
    "ray, expected_cell_id_and_ijk",
    [
        (RAY_FROM_TOP, (47, [2, 1, 2])),
        (RAY_FROM_BOTTOM, (7, [2, 1, 0])),
        (RAY_FROM_I, (42, [2, 0, 2])),
        (RAY_FROM_J, (40, [0, 0, 2])),
    ],
)
def test_find_closest_cell_to_ray(ray, expected_cell_id_and_ijk) -> None:
    cell_ijk = ES_GRID_ACCESSOR.find_closest_cell_to_ray(ES_GRID_ACCESSOR.es_grid, ray)
    assert cell_ijk == expected_cell_id_and_ijk


@pytest.mark.parametrize(
    "ray, expected_cell_id_and_ijk",
    [
        (RAY_FROM_TOP, (27, [2, 1, 1])),
        (RAY_FROM_BOTTOM, (7, [2, 1, 0])),
        (RAY_FROM_I, (52, [2, 2, 2])),
        (RAY_FROM_J, (43, [3, 0, 2])),
    ],
)
def test_find_closest_cell_to_ray_with_blanked_cells(
    ray, expected_cell_id_and_ijk
) -> None:
    grid = ES_GRID_ACCESSOR.es_grid.copy()

    cellLocator = vtkCellLocator()
    cellLocator.SetDataSet(grid)
    cellLocator.BuildLocator()
    cellIds = vtkIdList()
    cellLocator.FindCellsAlongLine((6.0, 6.0, 12.0), (67.0, 12.0, 12.0), 0.001, cellIds)
    for i in range(cellIds.GetNumberOfIds()):
        id = cellIds.GetId(i)
        grid.BlankCell(id)

    cell_ijk = ES_GRID_ACCESSOR.find_closest_cell_to_ray(grid, ray)
    assert cell_ijk == expected_cell_id_and_ijk
