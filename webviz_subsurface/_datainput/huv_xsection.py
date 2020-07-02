import xtgeo
import numpy as np
from pathlib import Path


class HuvXsection:
    def __init__(
            self,
            surface_attributes: dict = None,
            fence = None
    ):
        self.fence = fence
        self.surface_attributes = surface_attributes

    def create_surface_lines(self, surfacepaths):
        for sfc_path in surfacepaths:
            sfc = xtgeo.surface_from_file(Path(sfc_path), fformat="irap_binary")
            sfc_line = sfc.get_randomline(self.fence)
            self.surface_attributes[Path(sfc_path)]['surface_line'] = sfc_line

    def create_error_lines(self, errorpaths):
        for sfc_path in self.surface_attributes:
            err = xtgeo.surface_from_file(self.surface_attributes[Path(sfc_path)]["error_path"], fformat="irap_binary")
            err_line = err.get_randomline(self.fence)
            self.surface_attributes[Path(sfc_path)]["error_line"] = err_line

    @property
    def plotly_layout(self):
        layout ={}
        layout.update({
            "yaxis":{
                "title":"Depth (m)",
                "autorange":"reversed",
            },
            "xaxis": {
                "title": "Distance from polyline",
            },
            "plot_bgcolor":'rgb(233,233,233)',
            "showlegend":False,
            "height": 830,
        })
        return layout

    def get_plotly_sfc_data(self, surface_paths: list):
        min, max = self.surfline_max_min_depth(surface_paths)
        first_surf_line = self.surface_attributes[Path(surface_paths[0])]['surface_line']
        surface_tuples =[
            (sfc_path ,self.surface_attributes[Path(sfc_path)]['surface_line'])
            for sfc_path in surface_paths
        ]
        surface_tuples.sort(key=depth_sort, reverse=True)
        data = [ #Create helpline for bottom of plot
            {
                "type": "line",
                "x": [first_surf_line[0, 0], first_surf_line[np.shape(first_surf_line)[0] - 1, 0]],
                "y": [max + 50, max + 50],
                "line": {"color": "rgba(0,0,0,1)", "width": 0.6},
            }
        ]

        data +=[
            {
                'x':self.surface_attributes[Path(sfc_path)]['surface_line'][:,0],
                'y':self.surface_attributes[Path(sfc_path)]['surface_line'][:,1],
                'line': {"color": "rgba(0,0,0,1)", "width": 0.6},
                "fill": "tonexty",
                'fillcolor':self.surface_attributes[Path(sfc_path)]["color"]
            }
            for sfc_path, _ in surface_tuples
        ]
        return data


    def surfline_max_min_depth(self, surfacepaths:list):
        maxvalues = np.array([
            np.max(self.surface_attributes[Path(sfc_path)]['surface_line'][:,1])
            for sfc_path in surfacepaths
        ])
        minvalues = np.array([
            np.min(self.surface_attributes[Path(sfc_path)]['surface_line'][:,1])
            for sfc_path in surfacepaths
        ])
        return np.min(minvalues), np.max(maxvalues)


def depth_sort(elem):
    return np.min(elem[1][:, 1])
