import xtgeo
import numpy as np
from pathlib import Path


class HuvXsection:
    def __init__(
            self,
            surface_attributes: dict = None
    ):
        self.surface_attributes = surface_attributes

    def create_surface_lines(self, fence, surfacepaths):
        for sfc_path in surfacepaths:
            sfc = xtgeo.surface_from_file(sfc_path, fformat="irap_binary")
            sfc_line = sfc.get_randomline(fence)
            self.surface_attributes[sfc_path]['surface_line'] = sfc_line

    def create_error_lines(self, fence, errorpaths):
        for sfc_path in self.surface_attributes:
            err = xtgeo.surface_from_file(self.surface_attributes[sfc_path]["error_path"], fformat="irap_binary")
            err_line = err.get_randomline(fence)
            self.surface_attributes[sfc_path]["error_line"] = err_line

    @property
    def plotly_layout(self):
        layout = {
            "yaxis": {
                "title": "Depth (m)",
                "autorange": "reversed",
                #"range" : [max_depth,y_well-0.15*y_width]
            },
            "xaxis": {
                "title": "Distance from polyline",
                #"range": [x_well-0.5*x_width,xmax+0.5*x_width],
            },
            "plot_bgcolor":'rgb(233,233,233)',
            "showlegend":False,
            "height": 830,
        }

    def get_plotly_sfc_data(self, surface_paths: list):
        min, max = self.surfline_max_min_depth(surface_paths)
        first_surf_line = self.surface_attributes[surface_paths[0]]['surface_line']
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
                'x':self.surface_attributes[sfc_path]['surface_line'][:,0],
                'y':self.surface_attributes[sfc_path]['surface_line'][:,1],
                'line': {"color": "rgba(0,0,0,1)", "width": 0.6},
                "fill": "tonexty",
                'fillcolor':self.surface_attributes[sfc_path]["color"]
            }
            for sfc_path in surface_paths
        ]
        return data


    def surfline_max_min_depth(self, surfacepaths:list):
        maxvalues = np.array([
            np.max(self.surface_attributes[sfc_path]['surface_line'][:,1])
            for sfc_path in surfacepaths
        ])
        minvalues = np.array([
            np.min(self.surface_attributes[sfc_path]['surface_line'][:,1])
            for sfc_path in surfacepaths
        ])
        return np.min(minvalues), np.max(maxvalues)

path_topUpperReek = Path(r"C:\Users\ivarb\OneDrive\Documents\webViz\Datasets\simple_model\output\surfaces\d_TopUpperReek.rxb")
path_baseLowerReek = Path(r"C:\Users\ivarb\OneDrive\Documents\webViz\Datasets\simple_model\output\surfaces\d_BaseLowerReek.rxb")
path_baseLowerReek_de = Path(r"C:\Users\ivarb\OneDrive\Documents\webViz\Datasets\simple_model\output\surfaces\de_BaseLowerReek.rxb")
path_topUpperReek_de = Path(r"C:\Users\ivarb\OneDrive\Documents\webViz\Datasets\simple_model\output\surfaces\de_TopUpperReek.rxb")
surface_attributes = {path_baseLowerReek:{"color":"darkgrey","error_path":path_baseLowerReek_de}, path_topUpperReek:{"color":"red", "error_path":path_topUpperReek_de}}

OP1_path =  Path(r"C:\Users\ivarb\OneDrive\Documents\webViz\Datasets\simple_model\input\welldata\OP_1.txt")
OP1 = xtgeo.well_from_file(OP1_path)
fence = OP1.get_fence_polyline()

xsec = HuvXsection(surface_attributes) #oppretter xsec objekt
xsec.create_surface_lines(fence, [path_topUpperReek, path_baseLowerReek]) #legge til data
plotly_data = xsec.get_plotly_sfc_data([path_topUpperReek])
print(plotly_data)
