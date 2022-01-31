import numpy as np
import pandas as pd
import plotly.graph_objects as go
import xtgeo
from webviz_config.common_cache import CACHE


class HuvXsection:
    def __init__(
        self,
        surface_attributes=dict,
        zonation_status_file=None,
        well_points_file=None,
        zonelogname=None,
        well_attributes=dict,
    ):
        self.surface_attributes = surface_attributes
        self.zonation_status_file = zonation_status_file
        self.well_points_file = well_points_file
        self.zonelogname = zonelogname
        self.well_attributes = well_attributes
        self.planned_attributes = {}
        self.fig = None

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_xsec_well_data(self, well_settings, well, is_planned=False):
        """Finds data for well to plot in cross section
        Args:
            well_settings: List of checked options from well settings modal button
            well: xtgeo well
            is_planned: boolean, if False well meta-data like zonelog is not added
        Returns:
            data: List with dictionary containing well, zonelog, zonation points
                  and conditional points
        """
        if well is None:
            return []
        data = [
            {
                "y": well.dataframe["Z_TVDSS"],
                "x": well.dataframe["R_HLEN"],
                "name": "well",
                "line": {"width": 7, "color": "black"},
                "fillcolor": "black",
            }
        ]
        if not is_planned:
            well_df = well.dataframe
            if "zonelog" in well_settings:
                data += self.get_zonelog_data(well, well_df, self.zonelogname)
            if "zonation_points" in well_settings:
                zonation_points = get_zonation_points(
                    well_df, well.wellname, self.zonation_status_file
                )
                data += [
                    {
                        "mode": "markers",
                        "y": zonation_points[1],
                        "x": zonation_points[0],
                        "name": "Zonation points",
                        "marker": {"size": 5, "color": "rgb(153,50,204)"},
                    }
                ]
            if "conditional_points" in well_settings:
                conditional_points = get_conditional_points(
                    well_df, well.wellname, self.well_points_file
                )
                data += [
                    {
                        "mode": "markers",
                        "y": conditional_points[1],
                        "x": conditional_points[0],
                        "name": "Conditional points",
                        "marker": {"size": 5, "color": "rgb(0,255,255)"},
                    }
                ]
        return data

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def set_de_and_surface_lines(self, surfacefiles, de_keys, well, polyline):
        """Surface lines and corresponding depth error lines with fence from wellfile or polyline
        Args:
            surfacefiles: List of filepaths to surfacefiles
            de_keys: List of surfacepaths used as key in surface_attributes to access depth error
            well: xtgeo well
            polyline: Coordinates to polyline drawn in map view.
        """
        if well is None:
            fence = get_fencespec(polyline)
        else:
            fence = well.get_fence_polyline(nextend=100, sampling=5)
        for sfc_file in surfacefiles:
            self.surface_attributes[sfc_file]["surface_line"] = self.surface_attributes[
                sfc_file
            ]["surface"].get_randomline(fence)
            if sfc_file in de_keys:
                de_line = self.surface_attributes[sfc_file][
                    "surface_de"
                ].get_randomline(fence)
                self.surface_attributes[sfc_file]["de_line"] = de_line

    def get_xsec_layout(self, surfacefiles, well):
        """Scale cross section figure to well trajectory, well and surface intersection or polyline
        Args:
            surfacefiles: List of filepaths to surfacefiles
            well: xtgeo well
        Returns:
            layout: Dictionary with layout data
        """
        layout = {
            "yaxis": {
                "title": "True vertical depth [m]",
                "titlefont": {"size": 20},
                "tickfont": {"size": 16},
            },
            "xaxis": {
                "title": "Lateral length [m]",
                "titlefont": {"size": 18},
                "tickfont": {"size": 16},
            },
            "plot_bgcolor": "rgb(233,233,233)",
            "showlegend": False,
            "height": 830,
            "margin": {"t": 0, "l": 100},
        }
        if len(surfacefiles) == 0:
            layout["yaxis"].update({"autorange": "reversed"})

        elif well is None:
            ymin, ymax = self.sfc_lines_min_max_tvd(surfacefiles)
            layout["yaxis"].update({"range": [ymax, ymin]})

        else:
            y_min, y_max = self.sfc_lines_min_max_tvd(surfacefiles)
            x_min, x_max = get_range_from_well(well.dataframe, y_min)
            y_range = np.abs(y_max - y_min)
            x_range = np.abs(x_max - x_min)
            if y_range / x_range > 1:
                x_range = y_range + 10
            layout["yaxis"].update(
                {"range": [y_max + 0.15 * y_range, y_min - 0.15 * y_range]}
            )
            layout["xaxis"].update(
                {"range": [x_min - 0.35 * x_range, x_max + 0.35 * x_range]}
            )
        return layout

    def get_xsec_de_data(self, surfacefiles, de_keys):
        """Get cross section data for depth error
        Args:
            surfacefiles: List of filepaths to surfacefiles
            de_keys: List of surfacepaths used as key in surface_attributes to access depth error
        Returns:
            data: Dictionary with depth error data
        """
        common_files = [
            surfacefile_de
            for surfacefile_de in de_keys
            if surfacefile_de in surfacefiles
        ]
        data = []
        for sfc_file in common_files:
            data += [
                {
                    "x": self.surface_attributes[sfc_file]["surface_line"][:, 0],
                    "y": self.surface_attributes[sfc_file]["surface_line"][:, 1]
                    - self.surface_attributes[sfc_file]["de_line"][:, 1],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6, "dash": "dash"},
                    "hoverinfo": "skip",
                    "mode": "lines",
                },
                {
                    "x": self.surface_attributes[sfc_file]["surface_line"][:, 0],
                    "y": self.surface_attributes[sfc_file]["surface_line"][:, 1]
                    + self.surface_attributes[sfc_file]["de_line"][:, 1],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6, "dash": "dash"},
                    "fill": "tonexty",
                    "fillcolor": "rgba(0,0,0,0.2)",
                    "hoverinfo": "skip",
                    "mode": "lines",
                },
            ]
        return data

    def get_xsec_sfc_data(self, surfacefiles):
        """Get cross section data for surfaces
        Args:
            surfacefiles: List of filepaths to surfacefiles
        Returns:
            data: List containing dictionary with surface data or empty list if no surfacefiles
        """
        if len(surfacefiles) == 0:
            data = []
        else:
            _, _max = self.sfc_lines_min_max_tvd(surfacefiles)
            first_sfc_line = self.surface_attributes[surfacefiles[0]]["surface_line"]
            surface_tuples = [
                (sfc_file, self.surface_attributes[sfc_file]["order"])
                for sfc_file in surfacefiles
            ]
            surface_tuples.sort(key=stratigraphic_sort, reverse=True)

            data = [  # Create helpline for bottom of plot
                {
                    "x": [
                        first_sfc_line[0, 0],
                        first_sfc_line[np.shape(first_sfc_line)[0] - 1, 0],
                    ],
                    "y": [_max + 200, _max + 200],
                    "line": {"color": "rgba(0,0,0,1)", "width": 0.6},
                    "mode": "lines",
                }
            ]

            data += [
                {
                    "x": self.surface_attributes[sfc_file]["surface_line"][:, 0],
                    "y": self.surface_attributes[sfc_file]["surface_line"][:, 1],
                    "line": {"color": "rgba(0,0,0,1)", "width": 1},
                    "fill": "tonexty",
                    "fillcolor": self.surface_attributes[sfc_file]["color"],
                    "name": self.surface_attributes[sfc_file]["name"],
                    "text": self.get_hover_text(sfc_file),
                    "mode": "lines",
                    "hovertemplate": "<b>TVD:<b> %{y:.2f} <br>"
                    + "<b>TVD SD:<b> %{text}",
                }
                for sfc_file, _ in surface_tuples
            ]
        return data

    def sfc_lines_min_max_tvd(self, surfacefiles):
        """Find max and min TVD values of all surfaces
        Args:
            surfacefiles: List of filepaths to surfacefiles
        Returns:
            data: Numpy array containing max and min TVD values of all surfacefiles
        """
        maxvalues = np.array(
            [
                np.max(self.surface_attributes[sfc_file]["surface_line"][:, 1])
                for sfc_file in surfacefiles
            ]
        )
        minvalues = np.array(
            [
                np.min(self.surface_attributes[sfc_file]["surface_line"][:, 1])
                for sfc_file in surfacefiles
            ]
        )
        return np.min(minvalues), np.max(maxvalues)

    def get_hover_text(self, sfc_file):
        """Hover text for cross section graph to display depth error relative to surface line
        Args:
            sfc_file: Filepath to surfacefile
        Returns:
             Numpy array of TVD values from depth error surface line
        """
        return np.around(self.surface_attributes[sfc_file]["de_line"][:, 1], 2)

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def set_xsec_fig(
        self, surfacefiles, de_keys, well_settings, well, is_planned=False
    ):
        """Set cross section plotly figure with data from wells, surfaces and depth error
        Args:
            surfacefiles: List of filepaths to surfacefiles
            de_keys: List of surfacepaths used as key in surface_attributes to access depth error
            well_settings: List of checked options from well settings modal button
            well: xtgeo well
            is_planned: boolean, if False well meta-data like zonelog is not added to plot
        """
        layout = self.get_xsec_layout(surfacefiles, well)
        data = (
            self.get_xsec_sfc_data(surfacefiles)
            + self.get_xsec_de_data(surfacefiles, de_keys)
            + self.get_xsec_well_data(well_settings, well, is_planned)
        )
        self.fig = go.Figure(dict({"data": data, "layout": layout}))

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_intersection_dataframe(self, well):
        """Get intersection between surfaces and well with XTGeo
        Args:
            well: xtgeo well
        Returns:
            df: Dataframe with surfacename, TVD, depth uncertainty and direction
        """
        data = {
            "Surface name": [],
            "TVD [m]": [],
            "TVD SD [m]": [],
            "Direction": [],
        }
        for sfc_path in self.surface_attributes:
            sfc = self.surface_attributes[sfc_path]["surface"]
            err = self.surface_attributes[sfc_path]["surface_de"]
            with np.errstate(invalid="ignore"):
                surface_picks = well.get_surface_picks(sfc)
                # get_surface_picks raises warning when MD column is missing in well
            if surface_picks is not None:
                surface_picks_df = surface_picks.dataframe
                for _, row in surface_picks_df.iterrows():
                    surface_name = self.surface_attributes[sfc_path]["name"]
                    depth_uncertainty = err.get_value_from_xy(
                        point=(row["X_UTME"], row["Y_UTMN"])
                    )
                    data["Surface name"].append(surface_name)
                    data["TVD [m]"].append(f"{row['Z_TVDSS']:.2f}")
                    data["TVD SD [m]"].append(f"{depth_uncertainty:.2f}")
                    data["Direction"].append(row["DIRECTION"])
        return pd.DataFrame(data=data)

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    # pylint: disable=too-many-locals
    def get_zonelog_data(self, well, well_df, zonelogname="Zonelog"):
        """Find zonelogs where well trajectory intersects surfaces and assigns color.
        Args:
            well: XTGeo well from filepath to wellfile
            well_df: Dataframe of well
            zonelogname: Name of zonelog
        Returns:
            data: List containing dictionary with zonelog data
        """
        color_list = [None] * len(well.get_logrecord(zonelogname))
        for sfc_file in self.surface_attributes:
            for i, _ in enumerate(color_list):
                if well.get_logrecord_codename(zonelogname, i) == "dummy":
                    color_list[i] = "rgb(211,211,211)"
                if (
                    well.get_logrecord_codename(zonelogname, i)
                    == self.surface_attributes[sfc_file]["topofzone"]
                ):
                    self.surface_attributes[sfc_file]["zone_number"] = i
                    color_list[i] = self.surface_attributes[sfc_file]["color"]
        well_tvd = well_df["Z_TVDSS"].values.copy()
        well_rhlen = well_df["R_HLEN"].values.copy()
        zonevals = well_df[zonelogname].values
        zoneplot = []
        start = 0
        zone_transitions = np.where(zonevals[:-1] != zonevals[1:])
        for transition in zone_transitions:
            try:
                well_tvd = np.insert(well_tvd, transition, well_tvd[transition + 1])
                well_rhlen = np.insert(
                    well_rhlen, transition, well_rhlen[transition + 1]
                )
                zonevals = np.insert(zonevals, transition, zonevals[transition])
            except IndexError:
                pass
        for i in range(1, len(zonevals)):
            if (not np.isnan(zonevals[i])) and (np.isnan(zonevals[i - 1])):
                end = i - 1
                color = "rgb(211,211,211)"
                zoneplot.append(
                    {
                        "x": well_rhlen[start:end],
                        "y": well_tvd[start:end],
                        "line": {"width": 4, "color": color},
                        "name": f"Zone: {zonevals[i-1]}",
                    }
                )
                start = end + 1
            elif (np.isnan(zonevals[i])) and (not np.isnan(zonevals[i - 1])):
                end = i - 1
                color = color_list[int(zonevals[i - 1])]
                zoneplot.append(
                    {
                        "x": well_rhlen[start:end],
                        "y": well_tvd[start:end],
                        "line": {"width": 4, "color": color},
                        "name": f"Zone: {zonevals[i-1]}",
                    }
                )
                start = end + 1
            elif (
                (zonevals[i] != zonevals[i - 1])
                and (not np.isnan(zonevals[i]))
                and (not np.isnan(zonevals[i - 1]))
            ):
                end = i - 1
                color = color_list[int(zonevals[i - 1])]
                zoneplot.append(
                    {
                        "x": well_rhlen[start:end],
                        "y": well_tvd[start:end],
                        "line": {"width": 4, "color": color},
                        "name": f"Zone: {zonevals[i-1]}",
                    }
                )
                start = end + 1
        if not np.isnan(zonevals[-1]):
            end = len(zonevals) - 1
            color = color_list[int(zonevals[-1])]
            zoneplot.append(
                {
                    "x": well_rhlen[start:end],
                    "y": well_tvd[start:end],
                    "line": {"width": 4, "color": color},
                    "name": f"Zone: {zonevals[-2]}",
                }
            )
        else:
            color = "rgb(211,211,211)"
            zoneplot.append(
                {
                    "mode": "markers",
                    "x": np.array([well_rhlen[-2], well_rhlen[-1]]),
                    "y": np.array([well_tvd[-2], well_tvd[-1]]),
                    "marker": {"size": 3, "color": color},
                    "name": f"Zone: {zonevals[-1]}",
                }
            )
        return zoneplot


def stratigraphic_sort(elem):
    """Sort surface lines in stratigraphic order"""
    return elem[1]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_zonation_points(well_df, wellname, zonation_status_file):
    """Finds zonation points along well trajectory
    Args:
        well_df: Dataframe of XTgeo well from filepath to wellfile
        wellname: Name of well
        zonation_status_file: Filepath to zonation_status.csv
    Returns:
        Numpy array with zone relative horizontal length and TVD
    """
    zonation_status_data = pd.read_csv(zonation_status_file)
    zone_df = zonation_status_data[zonation_status_data["Well"] == wellname]
    zone_df_xval = zone_df["x"].values.copy()
    zone_df_yval = zone_df["y"].values.copy()
    zone_rhlen = np.zeros(len(zone_df_xval))
    for i, _ in enumerate(zone_df_xval):
        well_df["XLEN"] = well_df["X_UTME"] - zone_df_xval[i]
        well_df["YLEN"] = well_df["Y_UTMN"] - zone_df_yval[i]
        well_df["SDIFF"] = np.sqrt(well_df.XLEN**2 + well_df.YLEN**2)
        index_array = np.where(well_df.SDIFF == well_df.SDIFF.min())
        zone_rhlen[i] = well_df["R_HLEN"].values[index_array[0]][0]
    return np.array([zone_rhlen, zone_df["TVD"]])


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_conditional_points(well_df, wellname, well_points_file):
    """Finds conditional points where surfaces and well intersect
    Args:
        well_df: Dataframe with well from XTGeo
        wellname: Name of well
        well_points_file: Filepath to wellpoints.csv
    Returns:
        Numpy array of relative horizontal length and TVD
    """
    wellpoint_data = pd.read_csv(well_points_file)
    wellpoint_df = wellpoint_data[wellpoint_data["Well"] == wellname]
    wellpoint_df_xval = wellpoint_df["x"].values.copy()
    wellpoint_df_yval = wellpoint_df["y"].values.copy()
    cond_rhlen = np.zeros(len(wellpoint_df_xval))
    for i, _ in enumerate(wellpoint_df_xval):
        well_df["XLEN"] = well_df["X_UTME"] - wellpoint_df_xval[i]
        well_df["YLEN"] = well_df["Y_UTMN"] - wellpoint_df_yval[i]
        well_df["SDIFF"] = np.sqrt(well_df.XLEN**2 + well_df.YLEN**2)
        index_array = np.where(well_df.SDIFF == well_df.SDIFF.min())
        cond_rhlen[i] = well_df["R_HLEN"].values[index_array[0]][0]
    return np.array([cond_rhlen, wellpoint_df["TVD"]])


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_range_from_well(well_df, ymin):
    """Finds min and max x values of well trajectory used in layout of cross section graph
    Args:
        well_df: Dataframe with well from XTgeo
    Returns:
        x_well_min: Float
        x_well_max: Float
    """
    x_well_max = np.max(well_df["R_HLEN"])
    x_well_min = 0
    for i in range(len(well_df["Z_TVDSS"])):
        if well_df["Z_TVDSS"][i] >= ymin:
            x_well_min = well_df["R_HLEN"][i]
            break
    return x_well_min, x_well_max


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_fencespec(polyline):
    """Create a XTGeo fence spec from polyline coordinates
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
