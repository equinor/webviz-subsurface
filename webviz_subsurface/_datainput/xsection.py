import numpy.ma as ma


class XSectionFigure:
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

    """

    # pylint: disable=too-many-instance-attributes, too-many-arguments
    def __init__(
        self,
        zmin=None,
        zmax=None,
        well=None,
        surfaces=None,
        sampling=5,
        nextend=5,
        zonelogshift=0,
        surfacenames=None,
        cube=None,
        grid=None,
        gridproperty=None,
    ):

        self._data = []
        self._zmin = zmin if zmin else well.dataframe["Z_TVDSS"].min()
        self._zmax = zmax if zmax else well.dataframe["Z_TVDSS"].max()
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
            "xaxis": {
                "showgrid": False,
                "title": "Distance from well",
                "zeroline": False,
            },
            "yaxis": {
                "range": [self._zmax, self._zmin],
                "showgrid": False,
                "title": "Depth",
                "zeroline": False,
            },
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
        self, zonelogname="ZONELOG", facieslogname=None, zonemin=0,
    ):
        """Input an XTGeo Well object and plot it."""
        well = self._well

        # reduce the well data by Pandas operations
        dfr = well.dataframe
        well.dataframe = dfr[dfr["Z_TVDSS"] > self._zmin]

        # Create a relative XYLENGTH vector (0.0 where well starts)
        well.create_relative_hlen()

        dfr = well.dataframe

        # get the well trajectory (numpies) as copy
        zvals = dfr["Z_TVDSS"].values.copy()
        hvals = dfr["R_HLEN"].values.copy()

        self._plot_well_traj(zvals, hvals)
        if zonelogname:
            self._plot_well_zlog(dfr, zvals, hvals, zonelogname, zonemin)

        # plot the facies, if any, behind the trajectory; ie. first or second
        if facieslogname:
            self._plot_well_faclog(dfr, zvals, hvals, facieslogname)

    def _plot_well_traj(self, zvals, hvals):
        """Plot the trajectory as a black line"""

        zvals_copy = ma.masked_where(zvals < self._zmin, zvals)
        hvals_copy = ma.masked_where(zvals < self._zmin, hvals)

        self._data.append(
            {
                "x": hvals_copy,
                "y": zvals_copy,
                "name": self._well.name,
                "marker": {"color": "black"},
            }
        )

        # ax.plot(hvals_copy, zvals_copy, linewidth=6, c="black")

    def _plot_well_zlog(self, df, zvals, hvals, zonelogname, zonemin):
        """Plot the zone log as colored segments."""

        if zonelogname not in df.columns:
            return

        zonevals = df[zonelogname].values
        zomin = zonemin
        zomax = 0

        zomin = (
            zomin if zomin >= int(df[zonelogname].min()) else int(df[zonelogname].min())
        )
        zomax = int(df[zonelogname].max())
        for zone in range(zomin, zomax + 1):

            zvals_copy = ma.masked_where(zonevals != zone, zvals)
            hvals_copy = ma.masked_where(zonevals != zone, hvals)

            self._data.append(
                {
                    "x": hvals_copy,
                    "y": zvals_copy,
                    "line": {"width": 10},
                    "marker": {"opacity": 0.5},
                    # "connectgaps": True,
                    "name": f"Zone: {zone}",
                }
            )

    def _plot_well_faclog(self, df, zvals, hvals, facieslogname, facieslist=None):
        """Plot the facies log as colored segments.

        Args:
            df (dataframe): The Well dataframe.
            zvals (ndarray): The numpy Z TVD array.
            hvals (ndarray): The numpy Length  array.
            facieslogname (str): name of the facies log.
            facieslist (list): List of values to be plotted as facies
        """

        if facieslogname not in df.columns:
            return

        frecord = self._well.get_logrecord(facieslogname)
        frecord = {val: fname for val, fname in frecord.items() if val >= 0}

        if facieslist is None:
            facieslist = list(frecord.keys())

        faciesvalues = df[facieslogname].values

        for fcc in frecord:

            zvals_copy = ma.masked_where(faciesvalues != fcc, zvals)
            hvals_copy = ma.masked_where(faciesvalues != fcc, hvals)

            self._data.append(
                {
                    "x": hvals_copy,
                    "y": zvals_copy,
                    "line": {"width": 5},
                    "connectgaps": True,
                }
            )

        # self._drawlegend(ax, bba, title="Facies")

    # pylint: disable=too-many-locals
    def plot_cube(
        self,
        cube=None,
        vmin=None,
        vmax=None,
        alpha=0.7,
        interpolation="gaussian",
        sampling="nearest",
        name="seismic",
    ):
        """Plot a cube backdrop.

        Args:
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

        zinc = self._cube.zinc / 2.0

        zvalsv = self._cube.get_randomline(
            self.fence,
            zmin=self._zmin,
            zmax=self._zmax,
            zincrement=zinc,
            sampling=sampling,
        )

        xmin, xmax, ymin, ymax, arr = zvalsv
        x_inc = (xmax - xmin) / arr.shape[1]
        y_inc = (ymax - ymin) / arr.shape[0]
        # if vmin is not None or vmax is not None:
        #     arr = np.clip(arr, vmin, vmax)

        self._data.append(
            {
                "type": "heatmap",
                "z": arr,
                "x0": xmin,
                "xmax": xmax,
                "dx": x_inc,
                "y0": ymin,
                "ymax": ymax,
                "dy": y_inc,
                "zsmooth": "best",
                "showscale": False,
                "name": name
                # "colorscale": colors,
            }
        )

    # pylint: disable=too-many-locals
    def plot_grid3d(self, vmin=None, vmax=None, alpha=0.7):
        """Plot a sampled grid with gridproperty backdrop.

        Args:
            vmin (float): Minimum value in plot.
            vmax (float); Maximum value in plot
            alpha (float): Alpha blending number beween 0 and 1.

        Raises:
            ValueError: No grid or gridproperty is loaded

        """
        if self._grid is None or self._gridproperty is None:
            raise ValueError("Ask for plot of grid, but no grid is loaded")

        zinc = 0.5  # tmp

        zvalsv = self._grid.get_randomline(
            self.fence,
            self._gridproperty,
            zmin=self._zmin,
            zmax=self._zmax,
            zincrement=zinc,
        )

        xmin, xmax, ymin, ymax, arr = zvalsv
        x_inc = (xmax - xmin) / arr.shape[1]
        y_inc = (ymax - ymin) / arr.shape[0]
        # if vmin is not None or vmax is not None:
        #     arr = np.clip(arr, vmin, vmax)

        self._data.append(
            {
                "type": "heatmap",
                "z": arr,
                "x0": xmin,
                "xmax": xmax,
                "dx": x_inc,
                "y0": ymin,
                "ymax": ymax,
                "dy": y_inc,
                "zsmooth": "best",
                "showscale": False,
                # "colorscale": colors,
            }
        )

    def plot_surfaces(
        self, fill=False, surfaces=None, surfacenames=None,
    ):  # pylint: disable=too-many-branches, too-many-statements

        """Input a surface list (ordered from top to base) , and plot them."""

        # ax, bba = self._currentax(axisname=axisname)

        # either use surfaces from __init__, or override with surfaces
        # speciefied here

        nlen = len(surfaces)

        for i in range(nlen):

            hfence1 = surfaces[i].get_randomline(self.fence).copy()
            self._data.append(
                {
                    "type": "line",
                    "fill": "tonexty" if i != 0 and fill else None,
                    "y": hfence1[:, 1],
                    "x": hfence1[:, 0],
                    "name": surfacenames[i],
                    # "marker": {"color": s_color},
                }
            )
