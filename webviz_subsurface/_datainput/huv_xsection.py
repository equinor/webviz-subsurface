import xtgeo
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from webviz_config.common_cache import CACHE


class HuvXsection:
    def __init__(
            self,
            surface_attributes={},
            zonation_data=None,
            conditional_data=None,
            zonelogname=None,
            well_attributes={},
    ):
        self.surface_attributes = surface_attributes
        self.zonation_data = zonation_data
        self.conditional_data = conditional_data
        self.zonelogname = zonelogname
        self.well_attributes = well_attributes
        self.fig = None
        for sfc_file in self.surface_attributes:
            self.surface_attributes[sfc_file]['surface'] =\
                xtgeo.surface_from_file(sfc_file, fformat='irap_binary')
            self.surface_attributes[sfc_file]['surface_de'] =\
                xtgeo.surface_from_file(self.surface_attributes[sfc_file]['surfacefile_de'], fformat='irap_binary')

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def set_well_attributes(self, wellfiles):
        ''' Set dictionary with well data from all wellfiles
        Args:
            wellfiles: List of wellpaths
        '''
        for wellfile in wellfiles:
            well = xtgeo.Well(Path(wellfile))
            fence = well.get_fence_polyline(nextend=100, sampling=5)
            well_df = well.dataframe
            well.create_relative_hlen()
            zonation_points = get_zone_RHLEN(
                well_df,
                well.wellname,
                self.zonation_data
            )
            conditional_points, cp_sfc_linked = get_conditional_points(
                well_df,
                well.wellname,
                self.conditional_data
            )
            zonelog = self.get_zonelog_data(well, self.zonelogname)
            self.well_attributes[wellfile] = {
                "wellname": well.wellname,
                "wellfile": wellfile,
                "well_df": well_df,
                "zonelog": zonelog,
                "zonation_points": zonation_points,
                "conditional_points": conditional_points,
                "fence": fence,
                "cp_sfc_linked": cp_sfc_linked,
            }

    def get_xsec_well_data(self, well_settings, wellfile):
        ''' Finds data for well to plot in cross section
        Args:
            well_settings: List of checked options from well settings modal button
            wellfile: Filepath to wellfile
        Returns:
            data: List with dictionary containing zonelog, zonation points and conditional points
        '''
        if wellfile is None:
            return []
        else:
            data = [{
                "y": self.well_attributes[wellfile]["well_df"]["Z_TVDSS"],
                "x": self.well_attributes[wellfile]["well_df"]["R_HLEN"],
                "name": "well",
                "line": {"width": 7, "color": "black"},
                "fillcolor": "black",
            }]
            if 'zonelog' in well_settings:
                data += self.well_attributes[wellfile]["zonelog"]
            if 'zonation_points' in well_settings:
                data += [{
                    "mode": "markers",
                    "y": self.well_attributes[wellfile]["zonation_points"][1],
                    "x": self.well_attributes[wellfile]["zonation_points"][0],
                    "name": "Zonation points",
                    "marker": {"size": 5, "color": "rgb(153,50,204)"}
                }]
            if 'conditional_points' in well_settings:
                data += [{
                    "mode": "markers",
                    "y": self.well_attributes[wellfile]["conditional_points"][1],
                    "x": self.well_attributes[wellfile]["conditional_points"][0],
                    "name": "Conditional points",
                    "marker":{"size": 5, "color": "rgb(0,255,255)"}
                }]
            return data

    def set_de_and_surface_lines(self, surfacefiles, de_keys, wellfile, polyline):
        ''' Set surface lines and corresponding depth error lines with fence from wellfile or polyline
        Args:
            surfacefiles: List of filepaths to surfacefiles
            de_keys: List of surfacepaths used as key in surface_attributes to access depth error
            wellfile: Filepath to wellfile
            polyline: Coordinates to polyline drawn in map view.
        '''
        if wellfile is None:
            fence = get_fencespec(polyline)
        else:
            fence = self.well_attributes[wellfile]['fence']
        for sfc_file in surfacefiles:
            sfc_line = self.surface_attributes[sfc_file]['surface'].get_randomline(fence)
            self.surface_attributes[sfc_file]['surface_line'] = sfc_line
            if sfc_file in de_keys:
                de_line = self.surface_attributes[sfc_file]['surface_de'].get_randomline(fence)
                sfc_line = self.surface_attributes[sfc_file]['surface_line']
                self.surface_attributes[sfc_file]["de_line"] = de_line

    def get_error_table(self, wellfile):
        '''Finds depth error where index in surface line and conditional point x value is closest
        Difference in x value dependant on sampling rate of surface lines
        Args:
            Wellpath: Filepath to wellfiles
        Returns:
            Dataframe used for table in depth error tab'''
        data = {
            'Number': [],
            'Well': [],
            'Surface': [],
            'TVD (m)': [],
            'TVD uncertainty (m)': [],
            'Conditional point RHLEN (m)': [],
            'Surface line RHLEN (m)': [],
            '|\u0394RHLEN| (m)': [],
        }
        for i, sfc_file in enumerate(self.surface_attributes):
            for sfc_name in self.well_attributes[wellfile]['cp_sfc_linked']:
                path_str = str(sfc_file)
                if sfc_name == path_str[-len(sfc_name)-4:-4]:
                    for j in range(len(self.well_attributes[wellfile]['cp_sfc_linked'][sfc_name])):
                        cp_x = self.well_attributes[wellfile]['cp_sfc_linked'][sfc_name][j]
                        sfc_line = np.asarray(self.surface_attributes[sfc_file]['surface_line'][:, 0])
                        idx_diff_min = (np.abs(sfc_line - cp_x)).argmin()
                        error = self.surface_attributes[sfc_file]["de_line"][:, 1][idx_diff_min]
                        sfc_line_x = self.surface_attributes[sfc_file]['surface_line'][:, 0][idx_diff_min]
                        sfc_line_y = self.surface_attributes[sfc_file]['surface_line'][:, 1][idx_diff_min]
                        data['Number'].append(i+1)
                        data['Well'].append(self.well_attributes[wellfile]['wellname'])
                        data['Surface'].append(self.surface_attributes[sfc_file]['name'])
                        data['TVD (m)'].append("%0.2f" % sfc_line_y)
                        data['TVD uncertainty (m)'].append("%0.2f" % error)
                        data['Conditional point RHLEN (m)'].append("%0.2f" % cp_x)
                        data['Surface line RHLEN (m)'].append("%0.2f" % sfc_line_x)
                        data['|\u0394RHLEN| (m)'].append("%0.2f" % abs(sfc_line_x-cp_x))
        return pd.DataFrame(data)

    def get_xsec_layout(self, surfacefiles, wellfile):
        ''' Scale cross section figure to fit well trajectory, well and surface intersection or polyline
        Args:
            surfacefiles: List of filepaths to surfacefiles
            wellfile: Filepath to wellfile
        Returns:
            layout: Dictionary with layout data
        '''
        layout = {
            "yaxis": {
                "title": "Depth (m)",
                "titlefont": {"size": 20},
                "tickfont": {"size": 16}
            },
            "xaxis": {
                "title": "Distance from polyline",
                "titlefont": {"size": 18},
                "tickfont": {"size": 16}
            },
            "plot_bgcolor": 'rgb(233,233,233)',
            "showlegend": False,
            "height": 810,
            "margin": {"t": 0, "l": 100},
        }
        if len(surfacefiles) == 0:
            layout.update({
                "yaxis": {"autorange": "reversed"}
            })

        elif wellfile is None:
            ymin, ymax = self.sfc_lines_min_max_TVD(surfacefiles)
            layout.update({
                "yaxis": {"range": [ymax, ymin]}
            })

        else:
            y_min, y_max = self.sfc_lines_min_max_TVD(surfacefiles)
            x_min, x_max = get_range_from_well(self.well_attributes[wellfile]["well_df"], y_min)
            y_range = np.abs(y_max-y_min)
            x_range = np.abs(x_max - x_min)
            layout.update({
                "yaxis": {"range": [y_max+0.15*y_range, y_min-0.15*y_range]},
                "xaxis": {"range": [x_min-0.5*x_range, x_max+0.5*x_range]},
            })
        return layout

    def get_xsec_de_data(self, surfacefiles, de_keys):
        ''' Get cross section data for depth error
        Args:
            surfacefiles: List of filepaths to surfacefiles
            de_keys: List of surfacepaths used as key in surface_attributes to access depth error
        Returns:
            data: Dictionary with depth error data
        '''
        common_files = [surfacefile_de for surfacefile_de in de_keys if surfacefile_de in surfacefiles]
        data = []
        for sfc_file in common_files:
            data += [
                {
                    'x': self.surface_attributes[sfc_file]['surface_line'][:, 0],
                    'y': self.surface_attributes[sfc_file]['surface_line'][:, 1] - self.surface_attributes[sfc_file]['de_line'][:, 1],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6, 'dash': 'dash'},
                    'hoverinfo': 'skip'
                 },
                {
                    'x': self.surface_attributes[sfc_file]['surface_line'][:, 0],
                    'y': self.surface_attributes[sfc_file]['surface_line'][:, 1] + self.surface_attributes[sfc_file]['de_line'][:, 1],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6, 'dash': 'dash'},
                    'fill': 'tonexty',
                    'fillcolor': 'rgba(0,0,0,0.2)',
                    'hoverinfo': 'skip'
                }
            ]
        return data

    def get_xsec_sfc_data(self, surfacefiles):
        ''' Get cross section data for surfaces
        Args:
            surfacefiles: List of filepaths to surfacefiles
        Returns:
            data: List containing dictionary with surface data or empty list if no surfacefiles
        '''
        if len(surfacefiles) == 0:
            data = []
        else:
            _, _max = self.sfc_lines_min_max_TVD(surfacefiles)
            first_sfc_line = self.surface_attributes[surfacefiles[0]]['surface_line']
            surface_tuples = [
                (sfc_file, self.surface_attributes[sfc_file]['order'])
                for sfc_file in surfacefiles
            ]
            surface_tuples.sort(key=stratigraphic_sort, reverse=True)

            data = [  # Create helpline for bottom of plot
                {
                    "x": [first_sfc_line[0, 0], first_sfc_line[np.shape(first_sfc_line)[0] - 1, 0]],
                    "y": [_max + 200, _max + 200],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6},
                }
            ]

            data += [
                {
                    'x': self.surface_attributes[sfc_file]['surface_line'][:, 0],
                    'y': self.surface_attributes[sfc_file]['surface_line'][:, 1],
                    'line': {"color": "rgba(0,0,0,1)", "width": 1},
                    "fill": "tonexty",
                    'fillcolor': self.surface_attributes[sfc_file]["color"],
                    'name': self.surface_attributes[sfc_file]['name'],
                    'text': self.get_hover_text(sfc_file),
                    'hovertemplate': '<b>Depth:<b> %{y:.2f} <br>' + '<b>Depth error:<b> %{text}'
                }
                for sfc_file, _ in surface_tuples
            ]
        return data

    def sfc_lines_min_max_TVD(self, surfacefiles):
        ''' Find max and min TVD values of all surfaces
        Args:
            surfacefiles: List of filepaths to surfacefiles
        Returns:
            data: Numpy array containing max and min TVD values of all surfacefiles
        '''
        maxvalues = np.array([
            np.max(self.surface_attributes[sfc_file]['surface_line'][:, 1])
            for sfc_file in surfacefiles
        ])
        minvalues = np.array([
            np.min(self.surface_attributes[sfc_file]['surface_line'][:, 1])
            for sfc_file in surfacefiles
        ])
        return np.min(minvalues), np.max(maxvalues)

    def get_hover_text(self, sfc_file):
        ''' Hover text for cross section graph to display depth error relative to surface line
        Args:
            sfc_file: Filepath to surfacefile
        Returns:
             Numpy array of TVD values from depth error surface line
        '''
        return np.around(self.surface_attributes[sfc_file]['de_line'][:, 1], 2)

    def set_xsec_fig(self, surfacefiles, de_keys, well_settings, wellfile):
        ''' Set cross section plotly figure with data from wells, surfaces and depth error
        Args:
            surfacefiles: List of filepaths to surfacefiles
            de_keys: List of surfacepaths used as key in surface_attributes to access depth error
            well_settings: List of checked options from well settings modal button
            wellfile: Filepath to wellfile
        '''
        layout = self.get_xsec_layout(surfacefiles, wellfile)
        data = \
            self.get_xsec_sfc_data(surfacefiles) + \
            self.get_xsec_de_data(surfacefiles, de_keys) + \
            self.get_xsec_well_data(well_settings, wellfile)
        self.fig = go.Figure(dict({'data': data, 'layout': layout}))

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_zonelog_data(self, well, zonelogname="Zonelog", zomin=-999):
        ''' Find zonelogs where well trajectory intersects surfaces and assigns color.
        Args:
            well: XTGeo well from filepath to wellfile
        Returns:
            data: List containing dictionary with zonelog data
        '''
        well_df = well.dataframe
        well.create_relative_hlen()
        color_list = [None]*len(well.get_logrecord(zonelogname))
        for sfc_file in self.surface_attributes:
            for i in range(len(color_list)):
                if well.get_logrecord_codename(zonelogname, i) == "dummy":
                    color_list[i] = "rgb(211,211,211)"
                if well.get_logrecord_codename(zonelogname, i) == self.surface_attributes[sfc_file]["topofzone"]:
                    self.surface_attributes[sfc_file]["zone_number"] = i
                    color_list[i] = self.surface_attributes[sfc_file]["color"]
        well_TVD = well_df["Z_TVDSS"].values.copy()
        well_RHLEN = well_df["R_HLEN"].values.copy()
        zonevals = well_df[zonelogname].values
        zoneplot = []
        start = 0
        zone_transitions = np.where(zonevals[:-1] != zonevals[1:])  # Index of zone transitions?
        for transition in zone_transitions:
            try:
                well_TVD = np.insert(well_TVD, transition, well_TVD[transition + 1])
                well_RHLEN = np.insert(well_RHLEN, transition, well_RHLEN[transition + 1])
                zonevals = np.insert(zonevals, transition, zonevals[transition])
            except IndexError:
                pass
        for i in range(1, len(zonevals)):
            if (np.isnan(zonevals[i]) == False) and (np.isnan(zonevals[i-1]) == True):
                end = i-1
                color = "rgb(211,211,211)"
                zoneplot.append({
                    "x": well_RHLEN[start:end],
                    "y": well_TVD[start:end],
                    "line": {"width": 4, "color": color},
                    "name": f"Zone: {zonevals[i-1]}",
                    })
                start = end+1
            if (np.isnan(zonevals[i]) == True) and (np.isnan(zonevals[i-1]) == False):
                end = i-1
                color = color_list[int(zonevals[i-1])]
                zoneplot.append({
                    "x": well_RHLEN[start:end],
                    "y": well_TVD[start:end],
                    "line": {"width": 4, "color": color},
                    "name": f"Zone: {zonevals[i-1]}",
                    })
                start = end+1
            if (zonevals[i] != zonevals[i-1]) and (np.isnan(zonevals[i]) == False) and (np.isnan(zonevals[i-1]) == False):
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
        if np.isnan(zonevals[-1]):
            color = "rgb(211,211,211)"
            zoneplot.append({
                "mode": "markers",
                "x": np.array([well_RHLEN[-2], well_RHLEN[-1]]),
                "y": np.array([well_TVD[-2], well_TVD[-1]]),
                "marker": {"size": 3, "color": color},
                "name": f"Zone: {zonevals[-1]}",
                })
        return zoneplot


def stratigraphic_sort(elem):
    ''' Sort surface lines in stratigraphic order'''
    return elem[1]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_zone_RHLEN(well_df, wellname, zone_path):
    ''' Finds zonation points along well trajectory
    Args:
        well_df: Dataframe of XTgeo well from filepath to wellfile
        wellname: Name of well
        zone_path: Filepath to zonation_status.csv
    Returns:
        Numpy array with zone relative horizontal length and TVD
    '''
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
    ''' Finds conditional points where surfaces and well intersect
    Args:
        well_df: Dataframe with well from XTGeo
        wellname: Name of well
        wellpoints_path: Filepath to wellpoints.csv
    Returns:
        Numpy array of relative horizontal length and TVD
        Dictionary of conditional points linked to surfaces since surfaces might have more than one conditional point
    '''
    wellpoint_data = pd.read_csv(wellpoints_path)
    wellpoint_df = wellpoint_data[wellpoint_data["Well"] == wellname]
    wellpoint_df_xval = wellpoint_df["x"].values.copy()
    wellpoint_df_yval = wellpoint_df["y"].values.copy()
    wellpoint_df_surfaces = wellpoint_df["Surface"].values.copy()
    cond_RHLEN = np.zeros(len(wellpoint_df_xval))
    cond_sfc = {}  # No longer in use, remove, also in surface_attributes

    for i in range(len(wellpoint_df_xval)):
        well_df["XLEN"] = well_df["X_UTME"]-wellpoint_df_xval[i]
        well_df["YLEN"] = well_df["Y_UTMN"]-wellpoint_df_yval[i]
        well_df["SDIFF"] = np.sqrt(well_df.XLEN**2 + well_df.YLEN**2)
        index_array = np.where(well_df.SDIFF == well_df.SDIFF.min())
        cond_RHLEN[i] = well_df["R_HLEN"].values[index_array[0]][0]

        key = wellpoint_df_surfaces[i]
        RHLEN = cond_RHLEN[i]
        if key not in cond_sfc:
            cond_sfc[key] = [RHLEN]
        else:
            cond_sfc[key].append(RHLEN)
    return np.array([cond_RHLEN, wellpoint_df["TVD"]]), cond_sfc


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_range_from_well(well_df, ymin):
    ''' Finds min and max x values of well trajectory used in layout of cross section graph
    Args:
        well_df: Dataframe with well from XTgeo
    Returns:
        x_well_min: Float
        x_well_max: Float
    '''
    x_well_max = np.max(well_df["R_HLEN"])
    x_well_min = 0
    for i in range(len(well_df["Z_TVDSS"])):
        if well_df["Z_TVDSS"][i] >= ymin:
            x_well_min = well_df["R_HLEN"][i]
            break
    return x_well_min, x_well_max


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_fencespec(polyline):
    """ Create a XTGeo fence spec from polyline coordinates
    Args:
        polyline: Polyline drawn in map view
    Returns:
        XTGeo fence of polyline
    """
    poly = xtgeo.Polygons()
    poly.dataframe = pd.DataFrame(
        [
            {
                "X_UTME": coordinates[1],
                "Y_UTMN": coordinates[0],
                "Z_TVDSS": 0,
                "POLY_ID": 1,
                "NAME": "polyline",
            }
            for coordinates in polyline
        ]
    )
    return poly.get_fence(asnumpy=True)
