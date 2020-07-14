import xtgeo
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from webviz_config.common_cache import CACHE

class HuvXsection:
    def __init__(
            self,
            surface_attributes: dict = None,
            zonation_data = None,
            conditional_data = None,
            zonelogname = None,
            fence = None,
            well_attributes = None,
    ):
        self.fence = fence
        self.surface_attributes = surface_attributes
        self.zonation_data = zonation_data
        self.conditional_data = conditional_data
        self.zonelogname = zonelogname
        self.well_attributes = well_attributes
        self.fig = None
        for sfc_path in self.surface_attributes:
            self.surface_attributes[sfc_path]['surface'] =\
                xtgeo.surface_from_file(sfc_path, fformat='irap_binary')
            self.surface_attributes[sfc_path]['error_surface'] =\
                xtgeo.surface_from_file(self.surface_attributes[sfc_path]['error_path'], fformat='irap_binary')


    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def set_well(self, wellpath):
        if not wellpath is None:
            well = xtgeo.Well(Path(wellpath))
            self.fence = well.get_fence_polyline(nextend=100, sampling=5)
            well_df = well.dataframe
            well.create_relative_hlen()
            zonation_points = get_zone_RHLEN(well_df, well.wellname, self.zonation_data)
            conditional_points = get_conditional_RHLEN(well_df, well.wellname, self.conditional_data)
            zonelog = self.get_zonelog_data(well, self.zonelogname)
            self.well_attributes = {
                "wellpath": wellpath,
                "well_df": well_df, "zonelog":zonelog,
                "zonation_points": zonation_points,
                "conditional_points": conditional_points
            }

    def get_plotly_well_data(self):
        if self.well_attributes is None:
            return []
        else:
            data = [{
            "y": self.well_attributes["well_df"]["Z_TVDSS"],
            "x": self.well_attributes["well_df"]["R_HLEN"],
            "name": "well",
            "line": {"width": 7, "color": "black"},
            "fillcolor": "black",
            }]
            data += self.well_attributes["zonelog"]
            data += [{"mode": "markers",
                    "y": self.well_attributes["zonation_points"][1],
                    "x": self.well_attributes["zonation_points"][0],
                    "name": "zonation points",
                    "marker":{"size":5, "color":"black"}
            }]
            data += [{"mode": "markers",
                    "y": self.well_attributes["conditional_points"][1],
                    "x": self.well_attributes["conditional_points"][0],
                    "name": "conditional points",
                    "marker":{"size":5, "color":"rgb(30,144,255)"}
            }]
            return data

    def set_error_and_surface_lines(self, surface_paths, error_paths):
        for sfc_path in surface_paths:
            sfc_line = self.surface_attributes[sfc_path]['surface'].get_randomline(self.fence)
            self.surface_attributes[sfc_path]['surface_line'] = sfc_line
            if sfc_path in error_paths:
                de_line = self.surface_attributes[sfc_path]['error_surface'].get_randomline(self.fence)
                sfc_line = self.surface_attributes[sfc_path]['surface_line']
                self.surface_attributes[sfc_path]["error_line"] = de_line


    def get_plotly_layout(self, surfacepaths):
        layout = {}
        if len(surfacepaths) == 0:
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
        if self.well_attributes is None:
            ymin, ymax = self.sfc_line_max_min_depth(surfacepaths)
            layout.update({
                "yaxis":{
                    "title":"Depth (m)",
                    "range":[ymax, ymin],
                },
                "xaxis": {
                    "title": "Distance from polyline (m)",
                },
                "plot_bgcolor":'rgb(233,233,233)',
                "showlegend":False,
                "height": 830,
            })
            return layout
        else:
            ymin, ymax = self.sfc_line_max_min_depth(surfacepaths)
            x_well, y_well, x_well_max, y_width, x_width = get_intersection_surface_well(self.well_attributes["well_df"],ymin,ymax)
            layout.update({
                "yaxis":{
                    "title":"Depth (m)",
                    "range" : [ymax+0.15*y_width,y_well-0.15*y_width],
                },
                "xaxis":{
                    "title": "Distance from polyline (m)",
                    "range": [x_well-0.5*x_width, x_well_max+0.5*x_width],
                },
                "plot_bgcolor":'rgb(233,233,233)',
                "showlegend":False,
                "height": 830,
            })
            return layout


    def get_plotly_err_data(self, surface_paths, error_paths):
        common_paths = [error_path for error_path in error_paths if error_path in surface_paths]
        data = []
        for sfc_path in common_paths:
            data += [
                {
                    'x':self.surface_attributes[sfc_path]['surface_line'][:, 0],
                    'y': self.surface_attributes[sfc_path]['surface_line'][:, 1] - self.surface_attributes[sfc_path]['error_line'][:,1],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6, 'dash':'dash'},
                    'hoverinfo':'skip'
                 },
                {
                    'x': self.surface_attributes[sfc_path]['surface_line'][:, 0],
                    'y': self.surface_attributes[sfc_path]['surface_line'][:, 1] + self.surface_attributes[sfc_path]['error_line'][:,1],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6, 'dash':'dash'},
                    'fill': 'tonexty',
                    'fillcolor': 'rgba(0,0,0,0.2)',
                    'hoverinfo': 'skip'
                }
            ]
        return data

    def get_plotly_data(self, surface_paths, error_paths):
        if len(surface_paths) == 0:
            data = self.get_plotly_well_data()
            return data
        else:
            _min, _max = self.sfc_line_max_min_depth(surface_paths)
            first_surf_line = self.surface_attributes[surface_paths[0]]['surface_line']
            surface_tuples = [
                (sfc_path, self.surface_attributes[sfc_path]['order'])
                for sfc_path in surface_paths
            ]
            surface_tuples.sort(key=stratigraphic_sort, reverse=True)

            data = [ #Create helpline for bottom of plot
                {
                    "x": [first_surf_line[0, 0], first_surf_line[np.shape(first_surf_line)[0] - 1, 0]],
                    "y": [_max + 200, _max + 200],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6},
                }
            ]

            data += [
                {
                    'x':self.surface_attributes[sfc_path]['surface_line'][:, 0],
                    'y':self.surface_attributes[sfc_path]['surface_line'][:, 1],
                    'line': {"color": "rgba(0,0,0,1)", "width": 1},
                    "fill": "tonexty",
                    'fillcolor':self.surface_attributes[sfc_path]["color"],
                    'name':self.surface_attributes[sfc_path]['name'],
                    'text': self.get_hover_text(sfc_path),
                    'hovertemplate': '<b>Depth:<b> %{y:.2f} <br>' + '<b>Depth error:<b> %{text}'
                }
                for sfc_path, _ in surface_tuples
            ]

            data += self.get_plotly_err_data(surface_paths, error_paths)
            data += self.get_plotly_well_data()
            return data

    def sfc_line_max_min_depth(self, surfacepaths):
        maxvalues = np.array([
            np.max(self.surface_attributes[sfc_path]['surface_line'][:, 1])
            for sfc_path in surfacepaths
        ])
        minvalues = np.array([
            np.min(self.surface_attributes[sfc_path]['surface_line'][:, 1])
            for sfc_path in surfacepaths
        ])
        return np.min(minvalues), np.max(maxvalues)

    def get_hover_text(self, sfc_path):
        return np.around(self.surface_attributes[sfc_path]['error_line'][:,1], 2)

    def set_plotly_fig(self, surfacepaths, error_paths):
        layout = self.get_plotly_layout(surfacepaths)
        data = self.get_plotly_data(surfacepaths, error_paths)
        self.fig = go.Figure(dict({'data':data,'layout':layout}))

    def set_image(self, figure): #Requires Orca
        #figure.write_image("C:/Users/Ruben/Documents/VSCode/xsec.png")
        #figure.write_image("./xsec.png")
        return None

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_zonelog_data(self, well, zonelogname="Zonelog", zomin=-999):
        well_df = well.dataframe
        well.create_relative_hlen()
        color_list = [None]*len(well.get_logrecord(zonelogname))
        for sfc_path in self.surface_attributes:
            for i in range(len(color_list)):
                if well.get_logrecord_codename(zonelogname,i) == "dummy":
                    color_list[i] = "rgb(245,245,245)"
                if well.get_logrecord_codename(zonelogname,i) == self.surface_attributes[sfc_path]["topofzone"]:
                    self.surface_attributes[sfc_path]["zone_number"] = i
                    color_list[i] = self.surface_attributes[sfc_path]["color"]
        well_TVD = well_df["Z_TVDSS"].values.copy()
        well_RHLEN = well_df["R_HLEN"].values.copy()
        zonevals = well_df[zonelogname].values
        zoneplot = []
        start = 0
        l = 0
        zone_transitions = np.where(zonevals[:-1] != zonevals[1:]) #index of zone transitions?
        for transition in zone_transitions:
            try:
                well_TVD = np.insert(well_TVD, transition, well_TVD[transition + 1])
                well_RHLEN = np.insert(well_RHLEN, transition, well_RHLEN[transition + 1])
                zonevals = np.insert(zonevals, transition, zonevals[transition])
            except IndexError:
                pass
        for i in range(1,len(zonevals)):
            if (np.isnan(zonevals[i]) == False) and (np.isnan(zonevals[i-1])==True):
                end = i-1
                color = "rgb(211,211,211)"
                zoneplot.append({
                    "x": well_RHLEN[start:end],
                    "y": well_TVD[start:end],
                    "line": {"width": 4, "color": color},
                    "fillcolor": color,
                    "marker": {"opacity": 0.5},
                    "name": f"Zone: {zonevals[i-1]}",
                    })
                start = end+1
            if (np.isnan(zonevals[i]) == True) and (np.isnan(zonevals[i-1])==False):
                end = i-1
                color = color_list[int(zonevals[i-1])]
                zoneplot.append({
                    "x": well_RHLEN[start:end],
                    "y": well_TVD[start:end],
                    "line": {"width": 4, "color": color},
                    "fillcolor": color,
                    "marker": {"opacity": 0.5},
                    "name": f"Zone: {zonevals[i-1]}",
                    })
                start = end+1
            if (zonevals[i] != zonevals[i-1]) and (np.isnan(zonevals[i])==False) and (np.isnan(zonevals[i-1])==False):
                end = i-1
                color = color_list[int(zonevals[i-1])]
                zoneplot.append({
                    "x": well_RHLEN[start:end],
                    "y": well_TVD[start:end],
                    "line": {"width": 4, "color": color},
                    "fillcolor": color,
                    "marker": {"opacity": 0.5},
                    "name": f"Zone: {zonevals[i-1]}",
                    })
                start = end+1
        if not np.isnan(zonevals[-1]):
            end = len(zonevals)-1
            color = color_list[int(zonevals[-1])]
            zoneplot.append({
                "x": well_RHLEN[start:end],
                "y": well_TVD[start:end],
                "line": {"width": 4, "color": color},
                "fillcolor": color,
                "marker": {"opacity": 0.5},
                "name": f"Zone: {zonevals[-2]}",
                })
        if np.isnan(zonevals[-1]):
            color = "rgb(211,211,211)"
            zoneplot.append({
                "x": np.array(well_RHLEN[-1]),
                "y": np.array(well_TVD[-1]),
                "line": {"width": 4, "color": color},
                "fillcolor": color,
                "marker": {"opacity": 0.5},
                "name": f"Zone: {zonevals[-1]}",
                })
        return zoneplot


def stratigraphic_sort(elem):
    return elem[1]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_zone_RHLEN(well_df,wellname,zone_path):
    zonation_data = pd.read_csv(zone_path)
    zone_df = zonation_data[zonation_data["Well"] == wellname]
    zone_df_xval = zone_df["x"].values.copy()
    zone_df_yval = zone_df["y"].values.copy()
    zone_RHLEN = np.zeros(len(zone_df_xval))
    for i in range(len(zone_df_xval)):
        well_df["XLEN"] = well_df["X_UTME"]-zone_df_xval[i]
        well_df["YLEN"] = well_df["Y_UTMN"]-zone_df_yval[i]
        well_df["SDIFF"] = np.sqrt(well_df.XLEN**2 + well_df.YLEN**2)
        index_array = np.where(well_df.SDIFF == well_df.SDIFF.min())
        zone_RHLEN[i] = well_df["R_HLEN"].values[index_array[0]][0]
    return np.array([zone_RHLEN, zone_df["TVD"]])


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_conditional_RHLEN(well_df, wellname, cond_path):
    conditional_data = pd.read_csv(cond_path)
    cond_df = conditional_data[conditional_data["Well"] == wellname]
    cond_df_xval = cond_df["x"].values.copy()
    cond_df_yval = cond_df["y"].values.copy()
    cond_RHLEN = np.zeros(len(cond_df_xval))
    for i in range(len(cond_df_xval)):
        well_df["XLEN"] = well_df["X_UTME"]-cond_df_xval[i]
        well_df["YLEN"] = well_df["Y_UTMN"]-cond_df_yval[i]
        well_df["SDIFF"] = np.sqrt(well_df.XLEN**2 + well_df.YLEN**2)
        index_array = np.where(well_df.SDIFF == well_df.SDIFF.min())
        cond_RHLEN[i] = well_df["R_HLEN"].values[index_array[0]][0]
    return np.array([cond_RHLEN, cond_df["TVD"]])


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_intersection_surface_well(well_df, ymin, ymax):
    x_well_max = np.max(well_df["R_HLEN"])
    x_well = 0
    y_well = 0
    for i in range(len(well_df["Z_TVDSS"])):
        if well_df["Z_TVDSS"][i] >= ymin:
            y_well = well_df["Z_TVDSS"][i]
            x_well = well_df["R_HLEN"][i]
            break
    y_width = np.abs(ymax-y_well)
    x_width = np.abs(x_well_max-x_well)
    return x_well, y_well, x_well_max, y_width, x_width
