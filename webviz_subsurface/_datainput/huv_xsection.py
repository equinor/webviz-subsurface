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
            well_attributes = {},
    ):
        self.surface_attributes = surface_attributes
        self.zonation_data = zonation_data
        self.conditional_data = conditional_data
        self.zonelogname = zonelogname
        self.well_attributes = well_attributes
        self.fig = None

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def set_well_attributes(self, wellpaths):
        for wellpath in wellpaths:
            well = xtgeo.Well(Path(wellpath))
            fence = well.get_fence_polyline(nextend=100, sampling=5)
            well_df = well.dataframe
            well.create_relative_hlen()
            zonation_points = get_zone_RHLEN(well_df, well.wellname, self.zonation_data)
            conditional_points = get_conditional_points(well_df, well.wellname, self.conditional_data)
            zonelog = self.get_zonelog_data(well, self.zonelogname)
            self.well_attributes[wellpath] = {
                "well": well,
                "zonelog": zonelog,
                "zonation_points": zonation_points,
                "conditional_points": conditional_points,
                "fence": fence,
            }

    def get_plotly_well_data(self, well_settings, wellpath):
        if wellpath is None:
            return []
        else:
            data = [{
            "y": self.well_attributes[wellpath]['well'].dataframe["Z_TVDSS"],
            "x": self.well_attributes[wellpath]['well'].dataframe["R_HLEN"],
            "name": "well",
            "line": {"width": 7, "color": "black"},
            "fillcolor": "black",
            }]
            if 'zonelog' in well_settings:
                data += self.well_attributes[wellpath]["zonelog"]
            if 'zonation_points' in well_settings:
                data += [{"mode": "markers",
                        "y": self.well_attributes[wellpath]["zonation_points"][1],
                        "x": self.well_attributes[wellpath]["zonation_points"][0],
                        "name": "Zonation points",
                        "marker":{"size":5, "color":"rgb(153,50,204)"}
                }]
            if 'conditional_points' in well_settings:
                data += [{"mode": "markers",
                        "y": self.well_attributes[wellpath]["conditional_points"][1],
                        "x": self.well_attributes[wellpath]["conditional_points"][0],
                        "name": "Conditional points",
                        "marker":{"size":5, "color":"rgb(0,255,255)"}
                }]
            return data

    def set_error_and_surface_lines(self, surface_paths, error_paths, wellpath, polyline):
        if wellpath is None:
            fence = get_fencespec(polyline)
        else:
            fence = self.well_attributes[wellpath]['fence']
        for sfc_path in surface_paths:
            sfc_line = self.surface_attributes[sfc_path]['surface'].get_randomline(fence)
            self.surface_attributes[sfc_path]['surface_line'] = sfc_line
            if sfc_path in error_paths:
                de_line = self.surface_attributes[sfc_path]['error_surface'].get_randomline(fence)
                self.surface_attributes[sfc_path]["error_line"] = de_line

    def get_plotly_layout(self, surfacepaths, wellpath):
        layout = {}
        if len(surfacepaths) == 0:
            layout.update({
                "yaxis":{
                    "title": "Depth (m)",
                    "autorange": "reversed",
                    "titlefont": {"size": 20},
                    "tickfont": {"size":16},
                },
                "xaxis": {
                    "title": "Distance from polyline",
                    "titlefont": {"size": 18},
                    "tickfont": {"size":16},
                },
                "plot_bgcolor": 'rgb(233,233,233)',
                "showlegend": False,
                "height": 810,
                "margin": {"t": 0, "l": 100},
            })
            return layout
            
        elif wellpath is None:
            ymin, ymax = self.sfc_line_max_min_depth(surfacepaths)
            layout.update({
                "yaxis":{
                    "title": "Depth (m)",
                    "range": [ymax, ymin],
                    "titlefont": {"size": 20},
                    "tickfont": {"size":16},
                },
                "xaxis": {
                    "title": "Distance from polyline (m)",
                    "titlefont": {"size": 18},
                    "tickfont": {"size":16},
                },
                "plot_bgcolor": 'rgb(233,233,233)',
                "showlegend": False,
                "height": 810,
                "margin": {"t": 0, "l": 100},
            })
            return layout
        else:
            y_min, y_max = self.sfc_line_max_min_depth(surfacepaths)
            x_min, x_max= get_range_from_well(self.well_attributes[wellpath]['well'].dataframe ,y_min)
            y_range = np.abs(y_max-y_min)
            x_range = np.abs(x_max - x_min)
            layout.update({
                "yaxis":{
                    "title":"Depth (m)",
                    "range" : [y_max+0.15*y_range,y_min-0.15*y_range],
                    "titlefont": {"size": 18},
                    "tickfont": {"size":16},
                },
                "xaxis":{
                    "title": "Distance from polyline (m)",
                    "range": [x_min-0.5*x_range, x_max+0.5*x_range],
                    "titlefont": {"size": 20},
                    "tickfont": {"size":16},
                },
                "plot_bgcolor": 'rgb(233,233,233)',
                "showlegend": False,
                "height": 810,
                "margin": {"t": 0, "l": 100},
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


    def get_plotly_sfc_data(self, surface_paths):
        if len(surface_paths) == 0:
            return []
        else:
            _, _max = self.sfc_line_max_min_depth(surface_paths)
            first_surf_line = self.surface_attributes[surface_paths[0]]['surface_line']
            surface_tuples = [
                (sfc_path, self.surface_attributes[sfc_path]['order'])
                for sfc_path in surface_paths
            ]
            surface_tuples.sort(key=stratigraphic_sort, reverse=True)

            data = [  # Create helpline for bottom of plot
                {
                    "x": [first_surf_line[0, 0], first_surf_line[np.shape(first_surf_line)[0] - 1, 0]],
                    "y": [_max + 200, _max + 200],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6},
                    'mode': 'lines'
                }
            ]

            data += [
                {
                    'x': self.surface_attributes[sfc_path]['surface_line'][:, 0],
                    'y': self.surface_attributes[sfc_path]['surface_line'][:, 1],
                    'line': {"color": "rgba(0,0,0,1)", "width": 1},
                    "fill": "tonexty",
                    'fillcolor': self.surface_attributes[sfc_path]["color"],
                    'name': self.surface_attributes[sfc_path]['name'],
                    'text': self.get_hover_text(sfc_path),
                    'hovertemplate': '<b>Depth:<b> %{y:.2f} <br>' + '<b>Depth error:<b> %{text}'
                }
                for sfc_path, _ in surface_tuples
            ]
            return data

          
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

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def set_plotly_fig(self, surfacepaths, error_paths, well_settings, wellpath):
        layout = self.get_plotly_layout(surfacepaths, wellpath)
        data = \
            self.get_plotly_sfc_data(surfacepaths) + \
            self.get_plotly_err_data(surfacepaths, error_paths) + \
            self.get_plotly_well_data(well_settings, wellpath)
        self.fig = go.Figure(dict({'data':data,'layout':layout}))

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_intersection_dataframe(self, wellpath):
        data = {'Surface name': [], 'TVD': [], 'Depth uncertainty': [], 'Direction': []}
        for sfc_path in self.surface_attributes:
            surface_picks = self.well_attributes[wellpath]['well'].get_surface_picks(self.surface_attributes[sfc_path]['surface'])
            if surface_picks is not None:
                surface_picks_df = surface_picks.dataframe
                for _, row in surface_picks_df.iterrows():
                    depth_uncertainty = self.surface_attributes[sfc_path]['error_surface'].get_value_from_xy(point=(row['X_UTME'], row['Y_UTMN']))
                    data['Surface name'].append(self.surface_attributes[sfc_path]['name'])
                    data['TVD'].append(row['Z_TVDSS'])
                    data['Depth uncertainty'].append(depth_uncertainty)
                    data['Direction'].append(row['DIRECTION'])
        df = pd.DataFrame(data=data)
        return df.round(2)



    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_zonelog_data(self, well, zonelogname="Zonelog", zomin=-999):
        well_df = well.dataframe
        well.create_relative_hlen()
        color_list = [None]*len(well.get_logrecord(zonelogname))
        for sfc_path in self.surface_attributes:
            for i in range(len(color_list)):
                if well.get_logrecord_codename(zonelogname,i) == "dummy":
                    color_list[i] = "rgb(211,211,211)"
                elif well.get_logrecord_codename(zonelogname,i) == self.surface_attributes[sfc_path]["topofzone"]:
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
            if (not np.isnan(zonevals[i])) and (np.isnan(zonevals[i-1])):
                end = i-1
                color = "rgb(211,211,211)"
                zoneplot.append({
                    "x": well_RHLEN[start:end],
                    "y": well_TVD[start:end],
                    "line": {"width": 4, "color": color},
                    "name": f"Zone: {zonevals[i-1]}",
                    })
                start = end+1
            elif (np.isnan(zonevals[i])) and (not np.isnan(zonevals[i-1])):
                end = i-1
                color = color_list[int(zonevals[i-1])]
                zoneplot.append({
                    "x": well_RHLEN[start:end],
                    "y": well_TVD[start:end],
                    "line": {"width": 4, "color": color},
                    "name": f"Zone: {zonevals[i-1]}",
                    })
                start = end+1
            elif (zonevals[i] != zonevals[i-1]) and (not np.isnan(zonevals[i])) and (not np.isnan(zonevals[i-1])):
                end = i-1
                color = color_list[int(zonevals[i-1])]
                zoneplot.append({
                    "x": well_RHLEN[start:end],
                    "y": well_TVD[start:end],
                    "line": {"width": 4, "color": color},
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
                "name": f"Zone: {zonevals[-2]}",
                })
        else:
            color = "rgb(211,211,211)"
            zoneplot.append({
                "mode": "markers",
                "x": np.array([well_RHLEN[-2],well_RHLEN[-1]]),
                "y": np.array([well_TVD[-2],well_TVD[-1]]),
                "marker": {"size": 3, "color": color},
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
def get_conditional_points(well_df, wellname, wellpoints_path):
    ''' Finds conditional points where surface and well intersect.
    Args: 
        well_df: Well dataframe from XTgeo
        wellname: Name of well
        cond_path: Filepath to wellpoints.csv
    Returns:
        Numpy array of relative horizontal length (RHLEN) and vertical (TVD) length
        Dictionary of conditional points linked to surfaces since surfaces might have more than one conditional point
    '''
    wellpoint_data = pd.read_csv(wellpoints_path)
    wellpoint_df = wellpoint_data[wellpoint_data["Well"] == wellname]
    wellpoint_df_xval = wellpoint_df["x"].values.copy()
    wellpoint_df_yval = wellpoint_df["y"].values.copy()
    wellpoint_df_surfaces = wellpoint_df["Surface"].values.copy()
    cond_RHLEN = np.zeros(len(wellpoint_df_xval))

    for i in range(len(wellpoint_df_xval)):
        well_df["XLEN"] = well_df["X_UTME"]-wellpoint_df_xval[i]
        well_df["YLEN"] = well_df["Y_UTMN"]-wellpoint_df_yval[i]
        well_df["SDIFF"] = np.sqrt(well_df.XLEN**2 + well_df.YLEN**2)
        index_array = np.where(well_df.SDIFF == well_df.SDIFF.min())
        cond_RHLEN[i] = well_df["R_HLEN"].values[index_array[0]][0]
    return np.array([cond_RHLEN, wellpoint_df["TVD"]])

@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_range_from_well(well_df, ymin):
    x_well_max = np.max(well_df["R_HLEN"])
    x_well_min= 0
    for i in range(len(well_df["Z_TVDSS"])):
        if well_df["Z_TVDSS"][i] >= ymin:
            x_well_min= well_df["R_HLEN"][i]
            break
    return x_well_min, x_well_max

@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_fencespec(coords):
    """Create a XTGeo fence spec from polyline coordinates"""
    poly = xtgeo.Polygons()
    poly.dataframe = pd.DataFrame(
        [
            {
                "X_UTME": c[1],
                "Y_UTMN": c[0],
                "Z_TVDSS": 0,
                "POLY_ID": 1,
                "NAME": "polyline",
            }
            for c in coords
        ]
    )
    return poly.get_fence(asnumpy=True)