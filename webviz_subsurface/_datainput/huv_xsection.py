import xtgeo
import numpy as np
from pathlib import Path


class HuvXsection:
    def __init__(
            self,
            surface_attributes: dict = None,
            fence = None,
            well_attributes = None
    ):
        self.fence = fence
        self.surface_attributes = surface_attributes
        self.well_attributes = well_attributes
    
    def create_well(self, wellpath):
        if not wellpath==None:
            well = xtgeo.Well(Path(wellpath))
            well_fence = well.get_fence_polyline(nextend=100, sampling=5)
            self.fence = well_fence
            well_df = well.dataframe
            well.create_relative_hlen()
            self.well_attributes = {"well_df":well_df}

    def get_plotly_well_data(self):
        if self.well_attributes ==None:
            return []
        else:
            data = [{"type": "line",
            "y": self.well_attributes["well_df"]["Z_TVDSS"],
            "x": self.well_attributes["well_df"]["R_HLEN"],
            "name": "well"}]
            return data
                
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

    def get_plotly_layout(self,surfac_paths):
        layout ={}
        y_min, y_max = self.surfline_max_min_depth(surfac_paths)
        if self.well_attributes == None:

            layout.update({
                "yaxis":{
                    "title":"Depth (m)",
                    "range":[y_max,y_min],
                },
                "xaxis": {
                    "title": "Distance from polyline",
                },
                "plot_bgcolor":'rgb(233,233,233)',
                "showlegend":False,
                "height": 830,
            })
        else:
                 x_min, y_min, x_max = find_where_it_crosses_well(y_min, y_max, self.well_attributes['well_df'])
        x_range = np.abs(x_max - x_min)
        y_range = np.abs(y_max - y_min)
        layout.update({
            "yaxis": {
                "title": "Depth (m)",
                "range": [y_max + 0.15 * y_range, y_min - 0.15 * y_range],
            },
            "xaxis": {
                "title": "Distance from polyline",
                'range': [x_min - 0.15 * x_range, x_max + 0.15 * y_range]
            },
            "plot_bgcolor": 'rgb(233,233,233)',
            "showlegend": False,
            "height": 830,
        })

        return layout

    def get_plotly_data(self, surface_paths:list):
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

        data+= self.get_plotly_well_data()
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

def find_where_it_crosses_well(ymin,ymax,df):
    y_well = df["Z_TVDSS"]
    x_well = df["R_HLEN"]
    x_well_max = np.max(x_well)
    X_point_y = 0
    X_point_x = 0
    for i in range(len(y_well)):
        if y_well[i] >= ymin:
            X_point_y = y_well[i]
            X_point_x = x_well[i]
            break
    return X_point_x, X_point_y, x_well_max
