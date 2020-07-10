import xtgeo
import pandas as pd
import numpy as np
from pathlib import Path
from operator import add
from operator import sub
import xml.etree.ElementTree as ET
import math

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
    
    def set_well(self, wellpath):
        if wellpath != None:
            well = xtgeo.Well(Path(wellpath))
            self.fence = well.get_fence_polyline(nextend=100, sampling=5)
            well_df = well.dataframe
            well.create_relative_hlen()
            print(well.wellname)
            zonation_points = get_zone_RHLEN(well_df,well.wellname,self.zonation_data)
            conditional_points = get_conditional_RHLEN(well_df,well.wellname,self.conditional_data)
            zonelog = self.get_zonelog_data2(well,self.zonelogname)
            self.well_attributes = {"well_df":well_df,"zonelog":zonelog,"zonation_points":zonation_points,"conditional_points":conditional_points}

    def get_plotly_well_data(self):
        if self.well_attributes ==None:
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
                    "marker":{"size":5,"color":"black"}
            }]
            data += [{"mode": "markers",
                    "y": self.well_attributes["conditional_points"][1],
                    "x": self.well_attributes["conditional_points"][0],
                    "name": "conditional points",
                    "marker":{"size":5,"color":"rgb(30,144,255)"}
            }]
            return data

    def set_surface_lines(self, surfacepaths):
        for sfc_path in surfacepaths:
            sfc = xtgeo.surface_from_file((sfc_path), fformat="irap_binary")
            sfc_line = sfc.get_randomline(self.fence)
            self.surface_attributes[sfc_path]['surface_line'] = sfc_line
    
    def set_error_lines(self, errorpaths):
        for sfc_path in errorpaths:
            de_surface = xtgeo.surface_from_file(self.surface_attributes[sfc_path]["error_path"], fformat="irap_binary")
            de_line = de_surface.get_randomline(self.fence)
            sfc_line = self.surface_attributes[sfc_path]['surface_line']
            self.surface_attributes[sfc_path]["error_line_add"] = sfc_line[:,1] + de_line[:,1] #Top of envelope
            self.surface_attributes[sfc_path]["error_line_sub"] = sfc_line[:,1] - de_line[:,1] #Bottom of envelope             

    def get_plotly_layout(self,surfacepaths:list):
        layout ={}
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
        if self.well_attributes == None:
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
            x_well, y_well, x_well_max, y_width,x_width = get_intersection_surface_well(self.well_attributes["well_df"],ymin,ymax)
            layout.update({
                "yaxis":{
                    "title":"Depth (m)",
                    "range" : [ymax,y_well-0.15*y_width],
                },
                "xaxis":{
                    "title": "Distance from polyline (m)",
                    "range": [x_well-0.5*x_width,x_well_max+0.5*x_width],
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
            data +=[
                {
                    'x':self.surface_attributes[sfc_path]['surface_line'][:,0],
                    'y':self.surface_attributes[sfc_path]['error_line_sub'],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6, 'dash':'dash'},
                 },
                {
                    'x': self.surface_attributes[sfc_path]['surface_line'][:,0],
                    'y': self.surface_attributes[sfc_path]['error_line_add'],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6,'dash':'dash'},
                    'fill': 'tonexty',
                    'fillcolor': 'rgba(0,0,0,0.2)'
                }
            ]
        return data

    def get_plotly_data(self, surface_paths:list, error_paths:list):
        if len(surface_paths) == 0:
            data = self.get_plotly_well_data()
            return data
        else:
            min, max = self.sfc_line_max_min_depth(surface_paths)
            first_surf_line = self.surface_attributes[surface_paths[0]]['surface_line']
            surface_tuples =[
                (sfc_path, self.surface_attributes[sfc_path]['surface_line'])
                for sfc_path in surface_paths
            ]
            surface_tuples.sort(key=depth_sort, reverse=True)

            data = [ #Create helpline for bottom of plot
                {
                    "x": [first_surf_line[0, 0], first_surf_line[np.shape(first_surf_line)[0] - 1, 0]],
                    "y": [max + 50, max + 50],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6},
                }
            ]

            data +=[
                {
                    'x':self.surface_attributes[sfc_path]['surface_line'][:,0],
                    'y':self.surface_attributes[sfc_path]['surface_line'][:,1],
                    'line': {"color": "rgba(0,0,0,1)", "width": 1},
                    "fill": "tonexty",
                    'fillcolor':self.surface_attributes[sfc_path]["color"]
                }
                for sfc_path, _ in surface_tuples
            ]

            data += self.get_plotly_err_data(surface_paths,error_paths)
            data += self.get_plotly_well_data()
            return data


    def sfc_line_max_min_depth(self, surfacepaths:list):
        maxvalues = np.array([
            np.max(self.surface_attributes[sfc_path]['surface_line'][:,1])
            for sfc_path in surfacepaths
        ])
        minvalues = np.array([
            np.min(self.surface_attributes[sfc_path]['surface_line'][:,1])
            for sfc_path in surfacepaths
        ])
        return np.min(minvalues), np.max(maxvalues)

    def get_zonelog_data(self, well_df, zonelogname="Zonelog", zomin=-999):
        color_list = ["rgb(245,245,245)"]
        for sfc_path in self.surface_attributes:
            color_list.append(self.surface_attributes[sfc_path]["color"])
        well_TVD = well_df["Z_TVDSS"].values.copy()
        well_RHLEN = well_df["R_HLEN"].values.copy()
        zonevals = well_df[zonelogname].values
        zoneplot = []
        start = 0
        zone_transitions = np.where(zonevals[:-1] != zonevals[1:]) #index of zone transitions?
        for transition in zone_transitions:
            try:
                well_TVD = np.insert(well_TVD, transition, well_TVD[transition + 1])
                well_RHLEN = np.insert(well_RHLEN, transition, well_RHLEN[transition + 1])
                zonevals = np.insert(zonevals, transition, zonevals[transition])
            except IndexError:
                pass
        for i in range(1,len(zonevals)):
            if zonevals[i] != zonevals[i-1]:
                end = i-1
                if np.isnan(zonevals[i-1]) == True:
                    color = "rgb(245,245,245)"
                else:
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

        return zoneplot

    def get_zonelog_data2(self, well, zonelogname="Zonelog", zomin=-999):
        tree = ET.parse("/home/elisabeth/GitHub/Datasets/complex_model/model_file.xml")
        root = tree.getroot()
        name = []
        topofzone = []
        well_df = well.dataframe
        well.create_relative_hlen()
        color_list = [None]*len(well.get_logrecord(zonelogname))
        for surface in root.findall("./surfaces/surface"):
            name.append(surface.find("name").text)
            topofzone.append(surface.find("top-of-zone").text)
        for sfc_path in self.surface_attributes:
            index_array = np.where(np.array(name) == np.array(self.surface_attributes[sfc_path]["name"]))
            self.surface_attributes[sfc_path]["topofzone"] = topofzone[int(index_array[0])]
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
        print(well_df.isnull().sum())
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
            if math.isnan(zonevals[i-1]):
                l +=1
            if (np.isnan(zonevals[i]) == False) and (np.isnan(zonevals[i-1])==True):
                end = i-1
                print(end,"end1")
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
                print(end,"end2")
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
                print(end,"end3")
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
        if np.isnan(zonevals[-1]) == False:
            end = len(zonevals)-1
            print(end,"end4")
            color = color_list[int(zonevals[-1])]
            zoneplot.append({
                "x": well_RHLEN[start:end],
                "y": well_TVD[start:end],
                "line": {"width": 4, "color": color},
                "fillcolor": color,
                "marker": {"opacity": 0.5},
                "name": f"Zone: {zonevals[-2]}",
                })
        if np.isnan(zonevals[-1]) == True:
            end = len(zonevals)-1
            print(end,"end5")
            color = "rgb(211,211,211)"
            zoneplot.append({
                "x": np.array(well_RHLEN[-1]),
                "y": np.array(well_TVD[-1]),
                "line": {"width": 4, "color": color},
                "fillcolor": color,
                "marker": {"opacity": 0.5},
                "name": f"Zone: {zonevals[-1]}",
                })
        print(l)
        return zoneplot


def depth_sort(elem):
    return np.min(elem[1][:, 1])

def get_zone_RHLEN(well_df,wellname,zone_path):
    zonation_data = pd.read_csv(zone_path[0])  #"/home/elisabeth/GitHub/Datasets/simple_model/output/log_files/zonation_status.csv")
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
    return np.array([zone_RHLEN,zone_df["TVD"]])

def get_conditional_RHLEN(well_df,wellname,cond_path):
    conditional_data = pd.read_csv(cond_path[0])   #"/home/elisabeth/GitHub/Datasets/simple_model/output/log_files/wellpoints.csv")
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
    return np.array([cond_RHLEN,cond_df["TVD"]])

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
    return x_well, y_well, x_well_max, y_width,x_width
