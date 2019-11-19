"""Module for fast XSection plots of wells/surfaces etc, using matplotlib."""

from __future__ import print_function

from collections import OrderedDict

import numpy.ma as ma
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage.filters import gaussian_filter

from xtgeo.common import XTGeoDialog
from xtgeo.xyz import Polygons

# from .baseplot import BasePlot

xtg = XTGeoDialog()
logger = xtg.functionlogger(__name__)


class XSection:
    """Class for plotting a cross-section of a well.

    Args:
        zmin (float): Upper level of the plot (top Y axis).
        zmax (float): Lower level of the plot (bottom Y axis).
        well (Well): XTGeo well object.
        surfaces (list): List of XTGeo RegularSurface objects
        surfacenames (list): List of surface names (str) for legend
        cube (Cube): A XTGeo Cube instance
        grid (Grid): A XTGeo Grid instance
        gridproperty (GridProperty): A XTGeo GridProperty instance
        colormap (str): Name of colormap, e.g. 'Set1'. Default is 'xtgeo'
        outline (obj): XTGeo Polygons object

    """

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        zmin=0,
        zmax=9999,
        well=None,
        surfaces=None,
        sampling=20,
        nextend=5,
        colormap=None,
        zonelogshift=0,
        surfacenames=None,
        cube=None,
        grid=None,
        gridproperty=None,
        outline=None,
    ):

        self._data = []
        self._zmin = zmin
        self._zmax = zmax
        self._well = well
        self._nextend = nextend
        self._sampling = sampling
        self._surfaces = surfaces
        self._surfacenames = surfacenames
        self._cube = cube
        self._grid = grid
        self._gridproperty = gridproperty
        self._zonelogshift = zonelogshift

        self._fence = None

    @property
    def data(self):
        return self._data

    @property
    def layout(self):
        return {
            "height": 800,
            "xaxis": {"showgrid": False, "zeroline": False},
            "yaxis": {"range":[1900, 1500],"showgrid": False, "zeroline": False,},
        }
    @property
    def fence(self):
        """Set or get the fence spesification"""
        if self._fence is None:
            if self._well is not None:
                wfence = self._well.get_fence_polyline(
                    sampling=self._sampling, nextend=self._nextend, tvdmin=self._zmin
                )
                self._fence = wfence

                if wfence is False:
                    self._fence = None
            else:
                raise ValueError("Input well is None")  # should be more flexible
        return self._fence

    def plot_well(
        self,
        zonelogname="ZONELOG",
        facieslogname=None,
        perflogname=None,
        wellcrossings=None,
    ):
        """Input an XTGeo Well object and plot it."""
        wo = self._well

        # reduce the well data by Pandas operations
        dfr = wo.dataframe
        wo.dataframe = dfr[dfr["Z_TVDSS"] > self._zmin]

        # Create a relative XYLENGTH vector (0.0 where well starts)
        wo.create_relative_hlen()

        dfr = wo.dataframe
        if dfr.empty:
            self._showok = False
            return

        # get the well trajectory (numpies) as copy
        zv = dfr["Z_TVDSS"].values.copy()
        hv = dfr["R_HLEN"].values.copy()

        # plot the perflog, if any, first
        if perflogname:
            self._plot_well_perflog(dfr, zv, hv, perflogname)

        self._plot_well_traj(zv, hv)
        if zonelogname:     
            self._plot_well_zlog(dfr, zv, hv, zonelogname)


        # plot the facies, if any, behind the trajectory; ie. first or second
        if facieslogname:
            self._plot_well_faclog(dfr, zv, hv, facieslogname)

        if wellcrossings is not None and wellcrossings.empty:
            wellcrossings = None

        if wellcrossings is not None:
            self._plot_well_crossings(dfr, wellcrossings)

    def _plot_well_traj(self, zv, hv):
        """Plot the trajectory as a black line"""

        zv_copy = ma.masked_where(zv < self._zmin, zv)
        hv_copy = ma.masked_where(zv < self._zmin, hv)

        self._data.append({"x": hv_copy, "y": zv_copy, 'marker':{'color':'black'}})

        # ax.plot(hv_copy, zv_copy, linewidth=6, c="black")

    def _plot_well_zlog(self, df, zv, hv, zonelogname):
        """Plot the zone log as colored segments."""

        if zonelogname not in df.columns:
            return

        zo = df[zonelogname].values
        zomin = 0
        zomax = 0

        try:
            zomin = int(df[zonelogname].min())
            zomax = int(df[zonelogname].max())
        except ValueError:
            self._showok = False
            return

        # logger.info("ZONELOG min - max is %s - %s", zomin, zomax)
        zshift = 0
        if self._zonelogshift != 0:
            zshift = self._zonelogshift

        # let the part with ZONELOG have a colour
        # ctable = self.get_colormap_as_table()

        for zone in range(zomin, zomax + 1):

            # the minus one since zone no 1 use color entry no 0
            # if (zone + zshift - 1) < 0:
            #     color = (0.9, 0.9, 0.9)
            # else:
            #     color = ctable[zone + zshift - 1]

            zv_copy = ma.masked_where(zo != zone, zv)
            hv_copy = ma.masked_where(zo != zone, hv)
            # print(list(zv_copy))
            # logger.debug("Zone is %s, color no is %s", zone, zone + zshift - 1)
            self._data.append({"x": hv_copy, "y": zv_copy, "line":{'width':10},'marker':{'opacity':0.5},'connectgaps':True})
            # ax.plot(hv_copy, zv_copy, linewidth=4, c=color, solid_capstyle="butt")

    def _plot_well_faclog(self, df, zv, hv, facieslogname, facieslist=None):
        """Plot the facies log as colored segments.

        Args:
            df (dataframe): The Well dataframe.
            ax (axes): The ax plot object.
            zv (ndarray): The numpy Z TVD array.
            hv (ndarray): The numpy Length  array.
            facieslogname (str): name of the facies log.
            facieslist (list): List of values to be plotted as facies
        """

        if facieslogname not in df.columns:
            return

        # cmap = self.colormap_facies
        # ctable = self.get_any_colormap_as_table(cmap)
        # idx = self.colormap_facies_dict

        frecord = self._well.get_logrecord(facieslogname)
        frecord = {val: fname for val, fname in frecord.items() if val >= 0}

        if facieslist is None:
            facieslist = list(frecord.keys())

        fa = df[facieslogname].values

        for fcc in frecord:

            # if isinstance(idx[fcc], str):
            # color = idx[fcc]
            # else:
            # color = ctable[idx[fcc]]

            zv_copy = ma.masked_where(fa != fcc, zv)
            hv_copy = ma.masked_where(fa != fcc, hv)

            # _myline, = ax.plot(
            # hv_copy,
            # zv_copy,
            # linewidth=9,
            # c=color,
            # label=frecord[fcc],
            # solid_capstyle="butt",
            # )
            self._data.append({"x": hv_copy, "y": zv_copy, "line":{'width':5},'connectgaps':True})

        # self._drawlegend(ax, bba, title="Facies")

    def _plot_well_perflog(self, df, zv, hv, perflogname, perflist=None):
        """Plot the perforation log as colored segments.

        Args:
            df (dataframe): The Well dataframe.
            ax (axes): The ax plot object.
            zv (ndarray): The numpy Z TVD array.
            hv (ndarray): The numpy Length  array.
            perflogname (str): name of the perforation log.
            perflist (list): List of values to be plotted as PERF
        """

        if perflogname not in df.columns:
            return

        # cmap = self.colormap_perf
        # ctable = self.get_any_colormap_as_table(cmap)

        # precord = self._well.get_logrecord(perflogname)
        # precord = {val: pname for val, pname in precord.items() if val >= 0}

        idx = self.colormap_perf_dict

        if perflist is None:
            perflist = list(precord.keys())

        prf = df[perflogname].values

        # let the part with ZONELOG have a colour
        for perf in perflist:

            # if isinstance(idx[perf], str):
            #     color = idx[perf]
            # else:
            #     color = ctable[idx[perf]]

            zv_copy = ma.masked_where(perf != prf, zv)
            hv_copy = ma.masked_where(perf != prf, hv)

            # ax.plot(
            #     hv_copy,
            #     zv_copy,
            #     linewidth=15,
            #     c=color,
            #     label=precord[perf],
            #     solid_capstyle="butt",
            # )
            self._data.append({"x": hv_copy, "y": zv_copy})
        # self._drawlegend(ax, bba, title="Perforations")

    @staticmethod
    def _plot_well_crossings(dfr, wcross):
        pass
        """Plot well crossing based on dataframe (wcross)

        The well crossing coordinates are identified for this well,
        and then it is looking for the closest coordinate. Given this
        coordinate, a position is chosen.

        The pandas dataframe wcross shall have the following columns:

        * Name of crossing wells named CWELL
        * Coordinate X named X_UTME
        * Coordinate Y named Y_UTMN
        * Coordinate Z named Z_TVDSS

        Args:
            dfr: Well dataframe
            ax: current axis
            wcross: A pandas dataframe with precomputed well crossings
        """

        # placings = {
        #     0: (40, 40),
        #     1: (40, -20),
        #     2: (-30, 30),
        #     3: (30, 20),
        #     4: (-40, 30),
        #     5: (-20, 40),
        # }

        # for index, row in wcross.iterrows():
        #     xcoord = row.X_UTME
        #     ycoord = row.Y_UTMN

        #     dfrc = dfr.copy()

        #     dfrc["DLEN"] = pow(
        #         pow(dfrc.X_UTME - xcoord, 2) + pow(dfrc.Y_UTMN - ycoord, 2), 0.5
        #     )

        #     minindx = dfrc.DLEN.idxmin()

        #     ax.scatter(
        #         dfrc.R_HLEN[minindx],
        #         row.Z_TVDSS,
        #         marker="o",
        #         color="black",
        #         s=70,
        #         zorder=100,
        #     )
        #     ax.scatter(
        #         dfrc.R_HLEN[minindx],
        #         row.Z_TVDSS,
        #         marker="o",
        #         color="orange",
        #         s=38,
        #         zorder=102,
        #     )

        #     modulo = index % 5

        #     ax.annotate(
        #         row.CWELL,
        #         size=6,
        #         xy=(dfrc.R_HLEN[minindx], row.Z_TVDSS),
        #         xytext=placings[modulo],
        #         textcoords="offset points",
        #         arrowprops=dict(
        #             arrowstyle="->", connectionstyle="angle3,angleA=0,angleB=90"
        #         ),
        #         color="black",
        #     )

    # def _drawlegend(self, ax, bba, title=None):

    #     leg = ax.legend(
    #         loc="upper left",
    #         bbox_to_anchor=bba,
    #         prop={"size": self._legendsize},
    #         title=title,
    #         handlelength=2,
    #     )

    #     for myleg in leg.get_lines():
    #         myleg.set_linewidth(5)

    # def _currentax(self, axisname="main"):
    #     """Keep track of current axis; is needed as one new legend need one
    #     new axis.
    #     """
    #     # for multiple legends, bba is dynamic
    #     bbapos = {
    #         "main": (1.22, 1.12, 1, 0),
    #         "contacts": (1.01, 1.12),
    #         "second": (1.22, 0.50),
    #         "facies": (1.01, 1.00),
    #         "perf": (1.22, 0.45),
    #     }

    #     ax1 = self._ax1

    #     if axisname != "main":
    #         ax1[axisname] = self._ax1["main"].twinx()

    #         # invert min,max to invert the Y axis
    #         ax1[axisname].set_ylim([self._zmax, self._zmin])

    #         ax1[axisname].set_yticklabels([])
    #         ax1[axisname].tick_params(axis="y", direction="in")

    #     ax = self._ax1[axisname]

    #     bba = bbapos.get(axisname, (1.22, 0.5))

    #     return ax, bba

    def plot_cube(
        self,
        cube=None,
        colormap="seismic",
        vmin=None,
        vmax=None,
        alpha=0.7,
        interpolation="gaussian",
        sampling="nearest",
    ):
        """Plot a cube backdrop.

        Args:
            colormap (ColorMap): Name of color map (default 'seismic')
            vmin (float): Minimum value in plot.
            vmax (float); Maximum value in plot
            alpha (float): Alpah blending number beween 0 and 1.
            interpolation (str): Interpolation for plotting, cf. matplotlib
                documentation on this. Also gaussianN is allowed, where
                N = 1..9.
            sampling (str): 'nearest' (default) or 'trilinear' (more precise)

        Raises:
            ValueError: No cube is loaded

        """
        if cube:
            self._cube = cube
        if self._cube is None:
            raise ValueError("Ask for plot cube, but noe cube is loaded")

        # ax, _bba = self._currentax(axisname="main")

        zinc = self._cube.zinc / 2.0

        zvv = self._cube.get_randomline(
            self.fence,
            zmin=self._zmin,
            zmax=self._zmax,
            zincrement=zinc,
            sampling=sampling,
        )

        xmin, xmax, ymin, ymax, arr = zvv
        x_inc = (xmax - xmin) / arr.shape[1]
        y_inc = (ymax - ymin) / arr.shape[0]
        # if vmin is not None or vmax is not None:
        #     arr = np.clip(arr, vmin, vmax)

        # if self._colormap_cube is None:
        #     if colormap is None:
        #         colormap = "seismic"
        #     self._colormap_cube = self.define_any_colormap(colormap)

        # if "gaussian" in interpolation:  # allow gaussian3 etc
        #     nnv = interpolation[-1]
        #     try:
        #         nnv = int(nnv)
        #         arr = gaussian_filter(arr, nnv)
        #         interpolation = "none"
        #     except ValueError:
        #         interpolation = "gaussian"

        self._data.append(            {
                "type": "heatmap",
                # "text": text if text else None,
                "z": arr,
                "x0": xmin,
                "xmax": xmax,
                "dx": x_inc,
                "y0": ymin,
                "ymax": ymax,
                "dy": y_inc,
                "zsmooth": "best",
                # "showscale": showscale,
                # "colorscale": colors,
                # "zmin": zmin,
                # "zmax": zmax,
            })



    def plot_grid3d(self, colormap="rainbow", vmin=None, vmax=None, alpha=0.7):
        """Plot a sampled grid with gridproperty backdrop.

        Args:
            colormap (ColorMap): Name of color map (default 'rainbow')
            vmin (float): Minimum value in plot.
            vmax (float); Maximum value in plot
            alpha (float): Alpha blending number beween 0 and 1.

        Raises:
            ValueError: No grid or gridproperty is loaded

        """
        if self._grid is None or self._gridproperty is None:
            raise ValueError("Ask for plot of grid, but no grid is loaded")

        ax, _bba = self._currentax(axisname="main")

        zinc = 0.5  # tmp

        zvv = self._grid.get_randomline(
            self.fence,
            self._gridproperty,
            zmin=self._zmin,
            zmax=self._zmax,
            zincrement=zinc,
        )

        h1, h2, v1, v2, arr = zvv

        # if vmin is not None or vmax is not None:
        #     arr = np.clip(arr, vmin, vmax)

        if self._colormap_grid is None:
            if colormap is None:
                colormap = "rainbow"
            self._colormap_grid = self.define_any_colormap(colormap)

        img = ax.imshow(
            arr,
            cmap=self._colormap_grid,
            vmin=vmin,
            vmax=vmax,
            extent=(h1, h2, v2, v1),
            aspect="auto",
            alpha=alpha,
        )

        logger.info("Actual VMIN and VMAX: %s", img.get_clim())
        # steer this?
        if self._colorlegend_grid:
            self._fig.colorbar(img, ax=ax)

    def plot_surfaces(
        self,
        fill=False,
        surfaces=None,
        surfacenames=None,
        colormap=None,
        onecolor=None,
        linewidth=1.0,
        legend=True,
        legendtitle=None,
        fancyline=False,
        axisname="main",
        gridlines=False,
    ):  # pylint: disable=too-many-branches, too-many-statements

        """Input a surface list (ordered from top to base) , and plot them."""

        # ax, bba = self._currentax(axisname=axisname)

        # either use surfaces from __init__, or override with surfaces
        # speciefied here
        if surfaces is None:
            surfaces = self._surfaces
            surfacenames = self._surfacenames

        surfacenames = [surf.name for surf in surfaces]
        # self._zmin = np.min([np.min(s.copy().values) for s in surfaces])
        # self._zmax = np.max([np.max(s.copy().values) for s in surfaces])
        # print(self._zmin, self._zmax)
        # if legendtitle is None:
        #     legendtitle = self._legendtitle

        # if colormap is None:
        #     colormap = self._colormap
        # else:
        #     self.define_colormap(colormap)

        nlen = len(surfaces)

        # legend
        slegend = []
        if surfacenames is None:
            for i in range(nlen):
                slegend.append("Surf {}".format(i))

        else:
            # do a check
            if len(surfacenames) != nlen:
                msg = (
                    "Wrong number of entries in surfacenames! "
                    "Number of names is {} while number of files "
                    "is {}".format(len(surfacenames), nlen)
                )
                logger.critical(msg)
                raise SystemExit(msg)

            slegend = surfacenames

        # if self._colormap.N < nlen:
        #     msg = "Too few colors in color table vs number of surfaces"
        #     raise SystemExit(msg)

        # sample the horizon to the fence:
        # colortable = self.get_colormap_as_table()
        for i in range(nlen):
            # usecolor = colortable[i]

            hfence1 = surfaces[i].get_randomline(self.fence).copy()
            x1 = hfence1[:, 0]
            y1 = hfence1[:, 1]

            self._data.append(
                {
                    "type": "line",
                    "fill": "tonexty" if i != 0 and fill else None,
                    "y": y1,
                    "x": x1,
                    # "marker": {"color": s_color},
                }
            )
            # ax.plot(x1, y1, linewidth=0.1 * linewidth, c="black")
            # ax.fill_between(x1, y1, y2, facecolor=colortable[i], label=slegend[i])

        # invert min,max to invert the Y axis
        # ax.set_ylim([self._zmax, self._zmin])

        # if legend:
        #     self._drawlegend(ax, bba, title=legendtitle)

        # if axisname != "main":
        #     ax.set_yticklabels([])

        # ax.tick_params(axis="y", direction="in")

        # if axisname == "main" and gridlines:
        #     ax.grid(color="grey", linewidth=0.2)

    def plot_wellmap(self, otherwells=None, expand=1):
        """Plot well map as local view, optionally with nearby wells.

        Args:
            otherwells (list of Polygons): List of surrounding wells to plot,
                these wells are repr as Polygons instances, one per well.
            expand (float): Plot axis expand factor (default is 1); larger
                values may be used if other wells are plotted.


        """
        ax = self._ax2

        if self.fence is not None:

            xwellarray = self._well.dataframe["X_UTME"].values
            ywellarray = self._well.dataframe["Y_UTMN"].values

            ax.plot(xwellarray, ywellarray, linewidth=4, c="cyan")

            ax.plot(self.fence[:, 0], self.fence[:, 1], linewidth=1, c="black")
            ax.annotate("A", xy=(self.fence[0, 0], self.fence[0, 1]), fontsize=8)
            ax.annotate("B", xy=(self.fence[-1, 0], self.fence[-1, 1]), fontsize=8)
            ax.set_aspect("equal", "datalim")

            left, right = ax.get_xlim()
            xdiff = right - left
            bottom, top = ax.get_ylim()
            ydiff = top - bottom

            ax.set_xlim(left - (expand - 1.0) * xdiff, right + (expand - 1.0) * xdiff)
            ax.set_ylim(bottom - (expand - 1.0) * ydiff, top + (expand - 1.0) * ydiff)
        if otherwells:
            for poly in otherwells:
                if not isinstance(poly, Polygons):
                    xtg.warn(
                        "<otherw> not a Polygons instance, but "
                        "a {}".format(type(poly))
                    )
                    continue
                if poly.name == self._well.xwellname:
                    continue
                xwp = poly.dataframe[poly.xname].values
                ywp = poly.dataframe[poly.yname].values
                ax.plot(xwp, ywp, linewidth=1, c="grey")
                ax.annotate(poly.name, xy=(xwp[-1], ywp[-1]), color="grey", size=5)

    def plot_map(self):
        """Plot well location map as an overall view (with field outline)."""

        if not self._outline:
            return

        ax = self._ax3
        if self.fence is not None:

            xp = self._outline.dataframe["X_UTME"].values
            yp = self._outline.dataframe["Y_UTMN"].values
            ip = self._outline.dataframe["POLY_ID"].values

            ax.plot(self._fence[:, 0], self._fence[:, 1], linewidth=3, c="red")

            for i in range(int(ip.min()), int(ip.max()) + 1):
                xpc = xp.copy()[ip == i]
                ypc = yp.copy()[ip == i]
                if len(xpc) > 1:
                    ax.plot(xpc, ypc, linewidth=0.3, c="black")

            ax.set_aspect("equal", "datalim")
