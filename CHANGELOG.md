# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED] - YYYY-MM-DD

### Changed
- [#1122](https://github.com/equinor/webviz-subsurface/pull/1122) - `opm` and `ecl2df` are now optional, making `windows-subsurface` possible to install and import on non-unix based systems. **NOTE:** a lot of the functionality in `webviz-subsurface` is built on `opm` and `ecl2df`, and issues are therefore expected on eg Windows and macOS. Use with care.

### Added
- [#1162](https://github.com/equinor/webviz-subsurface/pull/1162) - `RelativePermeability` can now be initialized with only `pyscal` formatted input files instead of paths to ensembles using a new `scal_scenarios` input option.

## [0.2.16] - 2022-11-09

### Changed
- [#1138](https://github.com/equinor/webviz-subsurface/pull/1138) - More flexibility in the input to the `GroupTree` plugin. New input parameters `terminal_node`, `tree_type`, `excl_well_startswith` and `excl_well_endswith`. Relaxed requirements on summary input.

## [0.2.15] - 2022-10-10

### Added
- [#1114](https://github.com/equinor/webviz-subsurface/pull/1114) - Added a flag in config for `MapViewerFMU` to set initial state of hillshading.
- [#1111](https://github.com/equinor/webviz-subsurface/pull/1111) - `EXPERIMENTALGridViewerFMU` - New experimental plugin to visualize grid models.
>>>>>>> Add grid viewer
- [#1058](https://github.com/equinor/webviz-subsurface/pull/1058) - `WellCompletion` - New implementation of the `WellCompletions` plugin, which is faster, has more functionality (single realization) and utilizes the webviz layout framework (WLF).


### Fixed
- [#1061](https://github.com/equinor/webviz-subsurface/pull/1061) - Removed a pandas dataframe as function argument from a webvizstore decorated function as it can cause incompabilities between different environments.
- [#1114](https://github.com/equinor/webviz-subsurface/pull/1114) - Fixed an exception in `MapViewerFMU` when a map does not exist.
- [#1118](https://github.com/equinor/webviz-subsurface/pull/1118) - `MapViewerFMU` - Removed `zoom` and `bounds` props from `DeckGLMap` as they are now automatically calculated.
- [#1094](https://github.com/equinor/webviz-subsurface/pull/1094) - Fixed issues with ambiguous truth of `pandas.Series` in `EnsembleSummaryProvider`.
- [#1107](https://github.com/equinor/webviz-subsurface/pull/1107) - Fixed bug in `ParameterResponseCorrelation` that caused the plugin to fail if the `response_filters` parameter was not given.

### Changed

- [#1097](https://github.com/equinor/webviz-subsurface/pull/1007) - `smry2arrow_batch` - Now supports an arbitrary number of paths as input, meaning that it is no longer needed to wrap a wildcarded runpath pattern with "". It is though still required if defining a wildcarded eclbase.
- [#1083](https://github.com/equinor/webviz-subsurface/pull/1083) - Converted the `ParameterCorrelation` plugin to WLF (Webviz Layout Framework).
- [#1080](https://github.com/equinor/webviz-subsurface/pull/1080) - Converted the `GroupTree` plugin to WLF (Webviz Layout Framework).
- [#1089](https://github.com/equinor/webviz-subsurface/pull/1089) - Converted the `WellAnalysis` plugin to WLF (Webviz Layout Framework).
- [#1086](https://github.com/equinor/webviz-subsurface/pull/1086) - Converted the `SimulationTimeSeries` plugin to WLF (Webviz Layout Framework). Also increase maximum number of initial vectors from 3 to 5.
- [#1078](https://github.com/equinor/webviz-subsurface/pull/1078) - Converted the `PvtPlot` plugin to WLF (Webviz Layout Framework).
- [#1092](https://github.com/equinor/webviz-subsurface/pull/1092) - Converted the `TornadoPlotterFMU` plugin to WLF (Webviz Layout Framework).
- [#1085](https://github.com/equinor/webviz-subsurface/pull/1085) - Converted the `ProdMisfit` plugin to WLF (Webviz Layout Framework).
- [#1113](https://github.com/equinor/webviz-subsurface/pull/1113) - Converted the `RftPlotter` plugin to WLF (Webviz Layout Framework). Combined the crossplot and misfit per observation to one new view: `Sim vs Obs`.


## [0.2.14] - 2022-06-28

### Fixed

- [#1055](https://github.com/equinor/webviz-subsurface/pull/1055) - `ProdMisfit` - Fixed a bug related to the input argument *excl_name_contains*.
- [#1053](https://github.com/equinor/webviz-subsurface/pull/1046) - `SwatinitQC` - Fixed an issue so that relative paths for the `faultlines` argument works.
- [#1046](https://github.com/equinor/webviz-subsurface/pull/1046) - `MapViewerFMU` - Fixed an issue related to upstream changes in prop specification for the DeckGLMap component.

### Changed

- [#1020](https://github.com/equinor/webviz-subsurface/pull/1020) - `WellAnalysis` - Several improvements and bug fixes. F.ex a well attribute filter in the well overview plots and the possibility to see production only after a given date.
- [#1017](https://github.com/equinor/webviz-subsurface/pull/1017) - `SeismicMisfit` - Added support for X,Y,Z,ID header in polygon files and improved error handling when inconsistency between obs and sim data.
- [#1030](https://github.com/equinor/webviz-subsurface/pull/1030) - Implemented new summary data provider (using `.arrow` files) for the `ParameterResponseCorrelation` plugin.
- [#1041](https://github.com/equinor/webviz-subsurface/pull/1041) - Increased maximum number of selected vectors in `SimulationTimeSeries` plugin.
- [#1035](https://github.com/equinor/webviz-subsurface/pull/1035) - Removed `pydeck` dependency.

### Added

- [#1037](https://github.com/equinor/webviz-subsurface/pull/1037) - `MapViewerFMU` - Color tables are now customizable from the config file.

## [0.2.13] - 2022-05-05

### Added

- [#938](https://github.com/equinor/webviz-subsurface/pull/938) - `ProdMisfit` - New plugin for well production misfit visualization. Features visualization of production misfit at selected dates, production coverage at selected dates and heatmap representation of ensemble mean misfit for selected dates.
- [#1013](https://github.com/equinor/webviz-subsurface/pull/1013) - `MapViewerFMU` - Added option to specify the folder where maps are located (relative to runpath in each realization).
- [#936](https://github.com/equinor/webviz-subsurface/pull/936) - `ParameterResponseCorrelation` - Added options to interactively change correlation method and response aggregation, correlation cut-off and parameter filter.

### Changed

- [#1015](https://github.com/equinor/webviz-subsurface/pull/1015) - Improved error reporting for `.arrow` files where dates are not monotonically increasing.
- [#1028](https://github.com/equinor/webviz-subsurface/pull/1028) - `BhpQc` - read data from `.arrow` files instead of `.UNSMRY`.

### Fixed

- [#1014](https://github.com/equinor/webviz-subsurface/pull/1014) - `ParameterResponseCorrelation` and `BhpQc` - fix bug in range slider. `VolumetricAnalysis` - prevent "Totals" volumes (if present) beeing included in the sum when comparing static and dynamic volumes, and do not include non-numeric columns as volumetric responses.

## [0.2.12] - 2022-04-07

### Added

- [#981](https://github.com/equinor/webviz-subsurface/pull/981) - `WellAnalysis` - New plugin well analysis. One tab for well production overview plots and one for well control mode and network analysis.
- [#987](https://github.com/equinor/webviz-subsurface/pull/987) - `SwatinitQC` - New plugin for QC of Water Initialization in Eclipse runs where the `SWATINIT` keyword has been used.
- [#988](https://github.com/equinor/webviz-subsurface/pull/988) - `ParameterAnalysis` and `PropertyStatistics` - Switched to the VectorSelector component, and other various improvements.

### Fixed

- [#996](https://github.com/equinor/webviz-subsurface/pull/996) - `VolumetricAnalysis` - Fixed issue with the `Tornadoplot` tab not shown if volumes from both dynamic and static sources were included.
- [#985](https://github.com/equinor/webviz-subsurface/pull/985) - `WellLogViewer` - Updated data format to latest version. Requires no changes in input data.

### Changed

- [#988](https://github.com/equinor/webviz-subsurface/pull/988) - `ParameterAnalysis` and `PropertyStatistics`- Changed to reading unsmry data from `.arrow` files and deprecated the usage of aggregated csvfiles as input.
- [#986](https://github.com/equinor/webviz-subsurface/pull/986) - Avoid copying surfaces when using `MapViewerFMU` in non-portable mode.

## [0.2.11] - 2022-03-14

### Added

- [#971](https://github.com/equinor/webviz-subsurface/pull/971) - `MapViewerFMU` - New plugin for visualizing surface from FMU.
- [#940](https://github.com/equinor/webviz-subsurface/pull/940) - `SimulationTimeSeries` - Added configurable user defined vector definitions.
- [#951](https://github.com/equinor/webviz-subsurface/pull/951) - `SimulationTimeSeries` - Added calculating delta relative to date within ensemble - i.e. subtract realization values on selected date from corresponding realization values for each date in the selected vectors.
- [#944](https://github.com/equinor/webviz-subsurface/pull/940) - `WellCompletions` - Added support for zone to layer mappings that are potentially different across realizations.
- [#949](https://github.com/equinor/webviz-subsurface/pull/949) - `RftPlotter` - Added zone filter to the map options and parameter filter and some more options to the parameter response tab.

### Changed

- [#940](https://github.com/equinor/webviz-subsurface/pull/940) - `SimulationTimeSeries` - Changed vector annotation from "AVG_" with suffix "R" and "INTVL_" to "PER_DAY_" and "PER_INTVL_". Retrieve `VectorDefinitions` via Python-API for `webviz-subsurface-components`.
- [#956](https://github.com/equinor/webviz-subsurface/pull/956) - `SimulationTimeSeries` - Deprecate usage of user input options {vector1, vector2, vector3}. Add list of vectors as user input options for initially selected vectors.
- [#961](https://github.com/equinor/webviz-subsurface/pull/961) - Improved error message when there are none valid realizations in an ensemble.
- [#970](https://github.com/equinor/webviz-subsurface/pull/970) - Replaced modals with new Dialog component in `StructuralUncertainty`. Changed display of uncertainty table to be a Dialog.
- [#980](https://github.com/equinor/webviz-subsurface/pull/980) - Deprecated plugin `SurfaceViewerFMU`. This has been replaced by the faster, and more feature-rich plugin `MapViewerFMU`.

### Fixed

- [#965](https://github.com/equinor/webviz-subsurface/pull/965) - Allow a filtered subset of surface names for multiple attributes in `StructuralUncertainty`.
- [#972](https://github.com/equinor/webviz-subsurface/pull/972) - FIxed bug occuring when ensembles had different PORE/PORV naming standards in the volumetric input files. Also fixed bug occuring if only BO and/or BG was selected in the table.
- [#958](https://github.com/equinor/webviz-subsurface/pull/958) - Disable unwanted calculation of `marks` in some `RangeSlider` components.

## [0.2.10] - 2022-02-09

### Fixed

- [#921](https://github.com/equinor/webviz-subsurface/pull/921) - Fixed bug with History Vectors in new `SimulationTimeSeries` plugin. Replaced hard coded realization number of 0, with first valid realization in provider.
- [#926](https://github.com/equinor/webviz-subsurface/pull/926) - `VolumetricAnalysis` - Fixed bug when building portables with aggregated (`csvfile_vol`) input.
- [#929](https://github.com/equinor/webviz-subsurface/pull/929) - `TornadoWidget` - No longer skipping sensitivities with `SENSNAME="ref"` from tornado bars if there is more than one realization with `SENSNAME="ref"`.
- [#932](https://github.com/equinor/webviz-subsurface/pull/932) - `RftPlotter` - Fixed bug related to calculated correlations returning `NaN` if the response variable has constant values.
- [#937](https://github.com/equinor/webviz-subsurface/pull/937) - `SimulationTimeSeries` - Fixed hover info for observation trace

### Changed

- [#924](https://github.com/equinor/webviz-subsurface/pull/924) - Improvements to the `ParameterFilter` functionality, e.g information regarding active filters and which relizatons are filtered out, and better handling of multiple ensembles. Improvements to the `ParameterAnalysis` plugin, e.g. added boxplot, fixed table formatting and update of parameters based on selected ensemble.
- [#935](https://github.com/equinor/webviz-subsurface/pull/935) - Deprecated plugin `ReservoirSimulationTimeSeries`. This has been replaced by the faster, more flexible and less memory hungry plugin `SimulationTimeSeries`.

## [0.2.9] - 2022-01-06

### Fixed

- [#888](https://github.com/equinor/webviz-subsurface/pull/888) - Improved `SeismicMisfit` performance when using polygon files with a large number of polygons.
- [#911](https://github.com/equinor/webviz-subsurface/pull/911) - Handle ensembles with missing surface folders in `PropertyStatistics`.

### Added

- [#880](https://github.com/equinor/webviz-subsurface/pull/880) - Show hover information for uncertainty envelope in `StructuralUncertainty`.
- [#883](https://github.com/equinor/webviz-subsurface/pull/883) - Added `Statistics + Realizations`-plot for New `SimulationTimeSeries` plugin. Includes filtering of realizations and selection to calculate statistics from all realizations or selected subset of realizations. Updated visualization mode included in user download data.
- [#867](https://github.com/equinor/webviz-subsurface/pull/867) - Added new `SimulationTimeSeries` plugin, with code structure according to best practice plugin example `webviz-plugin-boilerplate` and usage of `EnsembleSummaryProvider`. New functionality as multiple Delta Ensembles in same plot, selectable resampling frequency and possibility to group subplots per selected ensemble or per selected vector.
- [#884](https://github.com/equinor/webviz-subsurface/pull/884) - Added a new tab to the `RFTPlotter` plugin, with functionality to analyse RFT pressure responses to parameters.

### Changed

- [#889](https://github.com/equinor/webviz-subsurface/pull/889) - Added `rel_file_pattern` argument to .arrow related factory methods in EnsembleSummaryProviderFactory.
- [#895](https://github.com/equinor/webviz-subsurface/pull/895) - Various improvements to `VolumetricAnalysis` mainly affecting functionality in the `Inplace distribution` tab e.g. merged functionality in pages `Custom plotting` and `1 plot / 1 table` into one, added colorby option in `Plots per zone/region`, and added shade to the convergence plot to indicate missing realizations.

## [0.2.8] - 2021-12-10

### Fixed

- [#877](https://github.com/equinor/webviz-subsurface/pull/877) - Update `WellLogViewer` to work with the latest version of the component.
- [#875](https://github.com/equinor/webviz-subsurface/pull/875) - Fixed an issue with the uncertainty envelope in `Structural Uncertainty` where the plot misbehaved for discontinuous surfaces. A side effect is that percentile calculations are now much faster.

### Added

- [#856](https://github.com/equinor/webviz-subsurface/pull/856) - `VolumetricAnalysis` - Added support for comparing sensitivities both within and across ensembles.
- [#721](https://github.com/equinor/webviz-subsurface/pull/721) - Added data provider for reading ensemble summary data through a unified interface, supporting optional lazy resampling/interpolation depending on data input format.
- [#845](https://github.com/equinor/webviz-subsurface/pull/845) - Added realization plot colored by sensitivity to tornado tab in `VolumetricAnalysis`.

### Changed

- [#855](https://github.com/equinor/webviz-subsurface/pull/855) - `VolumetricAnalysis` now supports mixing sensitivity and non-sensitivity ensembles.
- [#853](https://github.com/equinor/webviz-subsurface/pull/853) - `ParameterResponseCorrelation` improvements. Constant parameters are removed from the correlation figure, and option to set maximum number of parameters is added. Trendline is added to the scatterplot. Axis in correlation figure is now calculated based on data.
- [#844](https://github.com/equinor/webviz-subsurface/pull/844) - `SeismicMisfit` improvements. Data ranges now follows selected attribute. User defined zooms are now kept during callbacks. New option in slice plot to show individual realizations. Prettyfied all hoverdata. New colorscales. Polygons sorted by name in drop down selector.
- [#842](https://github.com/equinor/webviz-subsurface/pull/842) - `GroupTree` improvements. Supporting groups as leaf nodes.
- [#854](https://github.com/equinor/webviz-subsurface/pull/854) - `RFTPlotter` improvements. Fixed some bugs that caused webviz to crash, improved the layout some places and fixed broken links in documentation.

## [0.2.7] - 2021-11-08

### Added

- [#851](https://github.com/equinor/webviz-subsurface/pull/851) - Added new column 'SENSNAME_CASE' for improved plotting and filtering of sensitivity ensembles.
- [#825](https://github.com/equinor/webviz-subsurface/pull/825) - Added options to create separate tornado's for e.g Region/Zone in `VolumetricAnalysis`. As well as various improvements to the tornado figure.
- [#734](https://github.com/equinor/webviz-subsurface/pull/645) - New plugin, `SeismicMisfit`, for comparing observed and modelled seismic attributes. Multiple views, including misfit quantification and coverage plots.
- [#809](https://github.com/equinor/webviz-subsurface/pull/809) - `GroupTree` - added more statistical options (P10, P90, P50/Median, Max, Min). Some improvements to the menu layout and behaviour

### Fixed

- [#841](https://github.com/equinor/webviz-subsurface/pull/841) - Bugfixes and improved hoverlabels for `Tornado component`.
- [#833](https://github.com/equinor/webviz-subsurface/pull/833) - Fixed errors in `VolumetricAnalysis` related to empty/insufficient data after filtering in the `tornadoplots` and `comparison` tabs.
- [#817](https://github.com/equinor/webviz-subsurface/pull/817) - `DiskUsage` - Fixed formatting error in bar chart tooltip.
- [#820](https://github.com/equinor/webviz-subsurface/pull/820) - `SurfaceWithGridCrossSection` - Fixed an issue with intersecting grids generated with
  `xtgeo==2.15.2`. Grids exported from RMS with this version of xtgeo should be re-exported using a newer version as the subgrid information is incorrect.
- [#838](https://github.com/equinor/webviz-subsurface/pull/838) - `AssistedHistoryMatchingAnalysis` - Fixed an issue with output of a callback being used as input in another before the output object was guaranteed to exist.

## [0.2.6] - 2021-10-08

### Added

- [#783](https://github.com/equinor/webviz-subsurface/pull/783) - `VolumetricAnalysis` - added tab with Fipfile QC for inspection of which `FIPNUM's` and `REGION∕ZONE's` that have been combined in order to get comparable volumes between dynamic and static sources. This tab is only available if a fipfile is given as input.
- [#777](https://github.com/equinor/webviz-subsurface/pull/777) - `VolumetricAnalysis` - added tabs with `Source comparison` and `Ensemble comparison` as QC tools for quick identification of where and why volumetric changes occur across sources (e.g. static vs dynamic) or ensembles (e.g. model revisions or ahm iterations).
- [#709](https://github.com/equinor/webviz-subsurface/pull/709) - Added `VectorCalculator` component in `ReservoirSimulationTimeSeries` plugin for calculation and graphing of custom simulation time series vectors.
- [#773](https://github.com/equinor/webviz-subsurface/pull/773) - `VolumetricAnalysis` - added functionality of easy switching bewteen `FIPNUM` and `REGION/ZONE` filter for cases where each fipnum belongs to a unique region and zone.
- [#770](https://github.com/equinor/webviz-subsurface/pull/770) - Added support for dynamic volumetric files in `VolumetricAnalysis` and possibility of combining static and dynamic volumes on a comparable level. To trigger this behaviour a fipfile with `FIPNUM` to `REGION/ZONE` mapping information needs to be provided. Also added support for giving multiple files as input per source.
- [#755](https://github.com/equinor/webviz-subsurface/pull/755) - Updated existing and added new tests for the Drogon dataset.

### Changed

- [#788](https://github.com/equinor/webviz-subsurface/pull/788) - Prevent mixing volumes from different sensitivities in `VolumetricAnalysis` by not allowing to select more than one sensitivity as a filter unless SENSNAME has been grouped on by the user.
- [#760](https://github.com/equinor/webviz-subsurface/pull/760) - Updated to `Dash 2.0`.
- [#761](https://github.com/equinor/webviz-subsurface/pull/761) - Store `xtgeo.RegularSurface` as bytestream instead of serializing to `json`.

### Fixed

- [#802](https://github.com/equinor/webviz-subsurface/pull/802) - Removed `BO` or `BG` as response options for the tornados in `VolumetricAnalysis`, selecting them caused an error.
- [#794](https://github.com/equinor/webviz-subsurface/pull/794) - Fixed an issue in `VolumetricAnalysis` to prevent design matrix runs with only a single montecarlo sensitivity to be interpreted as a sensitivity run.
- [#765](https://github.com/equinor/webviz-subsurface/pull/765) - Use correct inline/xline ranges for axes in `SegyViewer` z-slice graph.
- [#782](https://github.com/equinor/webviz-subsurface/pull/782) - Fixed an issue in `VolumetricAnalysis` when calculating property columns on grouped selections.
- [#791](https://github.com/equinor/webviz-subsurface/pull/791) - Ensure correct map bounds in `SurfaceViewerFMU` when switching between attributes with different geometry.

## [0.2.5] - 2021-09-03

### Added

- [#733](https://github.com/equinor/webviz-subsurface/pull/733) - Added plugin to visualize well logs from files using [videx-welllog](https://github.com/equinor/videx-wellog).
- [#708](https://github.com/equinor/webviz-subsurface/pull/708) - Added support for new report format for `DiskUsage`, which improves the estimate of free disk space.

### Changed

- [#724](https://github.com/equinor/webviz-subsurface/pull/724) - Seperated out Tables as a new tab to `VolumetricAnalysis`
- [#723](https://github.com/equinor/webviz-subsurface/pull/723) - Added custom option to allow free selection of responses shown in the tornadoplots in `VolumetricAnalysis`
- [#717](https://github.com/equinor/webviz-subsurface/pull/717) - Keep zoom state in `ReservoirSimulationTimeseries` (inc `Regional` and `OneByOne`) and `RelativePermeability` plugins using `uirevision`.
- [#707](https://github.com/equinor/webviz-subsurface/pull/707) - Generalized and improved some plot functions in `PropertyStatistics`, `ParameterAnalysis` and `VolumetricAnalysis`. Replaced histogram with distribution plot in `PropertyStatistics`.

### Fixed

- [#749](https://github.com/equinor/webviz-subsurface/pull/749) - `LinePlotterFMU` check function for `x` axis value alignment across realizations now supports single valued columns.
- [#747](https://github.com/equinor/webviz-subsurface/pull/747) - Added missing realization filter on `OK` file in `EnsembleTableProviderFactory`.
- [#753](https://github.com/equinor/webviz-subsurface/pull/753) - Do not add `Count` column from grid property statistics input data as a selector in `PropertyStatistics`. Handle missing surfaces in `PropertyStatistics`

## [0.2.4] - 2021-07-13

### Added

- [#669](https://github.com/equinor/webviz-subsurface/pull/669) - New generic plugin to visualize tornado plots from a csv file of responses.
- [#685](https://github.com/equinor/webviz-subsurface/pull/685) - Added ERT forward model to convert from `.UNSMRY` to Arrow IPC file format (`.arrow`).
- [#662](https://github.com/equinor/webviz-subsurface/pull/662) - Added support in `WellCompletion` for connection history from summary data.

### Changed

- [#681](https://github.com/equinor/webviz-subsurface/pull/681) - `VolumetricAnalysis` upgrades - added page with tornadoplots to `VolumetricAnalysis`, automatic computation of volumes
  from the water zone if the volumes from the full grid geometry are included, and possibility of computing NTG from facies.
- [#683](https://github.com/equinor/webviz-subsurface/pull/683) - Added deprecation warning to `InplaceVolumesOneByOne`.
- [#661](https://github.com/equinor/webviz-subsurface/pull/661) - Moved existing clientside function to a general dash_clientside file to facilitate adding more functions later on.
- [#658](https://github.com/equinor/webviz-subsurface/pull/658) - Refactored Tornado figure code to be more reusable. Improved the Tornado bar visualization, added table display
  and improved layout in relevant plugins.
- [#676](https://github.com/equinor/webviz-subsurface/pull/676) - Added realization points to Tornado visualization. Various improvements to Tornado figure layout.
- [#667](https://github.com/equinor/webviz-subsurface/pull/667) - Standardized layout and styling of plugins.

### Fixed

- [#666](https://github.com/equinor/webviz-subsurface/pull/666) - Handle operations between surfaces with different topology in `SurfaceViewerFMU`
- [#675](https://github.com/equinor/webviz-subsurface/pull/675) - Adjust minimum zoom level in surface plugins for visualization of large surfaces.
- [#715](https://github.com/equinor/webviz-subsurface/pull/715) - After this, the `WellCompletion` plugin finds the kh unit even if the unit system is in an INCLUDE file. Also, `well_connection_status_file` refers to the same variable in the plugin and ert job.

## [0.2.3] - 2021-06-07

### Changed

- [#651](https://github.com/equinor/webviz-subsurface/pull/651) - Fixed issue with `_` in regions for `ReservoirSimulationTimeseriesRegional`.
- [#642](https://github.com/equinor/webviz-subsurface/pull/642) - New functionality in `WellCompletions`: New stratigraphy input and tree
  selector in filters. Possibility to input colors either in stratigraphy or in the zone_layer_mapping `.lyr`-file. And kh unit automatically
  found in Eclipse files.

### Fixed

- [#659](https://github.com/equinor/webviz-subsurface/pull/659) - Added missing `display: block` in option selectors (e.g. radio items).

### Added

- [#645](https://github.com/equinor/webviz-subsurface/pull/645) - New generic lineplotter plugin for FMU data. This is the first plugin that uses
  a new system to reduce the memory footprint of large datasets.
- [#641](https://github.com/equinor/webviz-subsurface/pull/641) - New plugin to analyze volumetrics results from FMU ensembles, replaces the `InplaceVolumes` plugin.

## [0.2.2] - 2021-04-30

### Changed

- [#618](https://github.com/equinor/webviz-subsurface/pull/618) - Added deprecation warning to `HorizonUncertaintyViewer`,
  `WellCrossSection` and `WellCrossSectionFMU`. These plugins will soon be removed. Relevant functionality is implememented
  in the new `StructuralUncertainty` plugin.
- [#646](https://github.com/equinor/webviz-subsurface/pull/646) - Replaced `DropDowns` in `ReservoirSimulationTimeSeries` plugin with `VectorSelector` components.

### Fixed

- [#621](https://github.com/equinor/webviz-subsurface/pull/621) - Fixed issue in `StructuralUncertainty` where map base layers did not load
  correctly from persisted user settings.
- [#626](https://github.com/equinor/webviz-subsurface/pull/626) - Fixed small bugs in the docstring of `WellCompletions` and added a tour_steps method.

## [0.2.1] - 2021-04-27

### Changed

- [#612](https://github.com/equinor/webviz-subsurface/pull/612) - New features in `ReservoirSimulationTimeSeries`: Statistical lines, option to remove history trace, histogram available when plotting individual realizations.

### Fixed

- [#615](https://github.com/equinor/webviz-subsurface/pull/615) - Improve table performance of `AssistedHistoryMatchingAnalysis`.

### Added

- [#605](https://github.com/equinor/webviz-subsurface/pull/605) - New plugin to analyze structural uncertainty from FMU ensembles.
- [#610](https://github.com/equinor/webviz-subsurface/pull/610) - New plugin `WellCompletions` to visualize completion data of simulation wells.

## [0.2.0] - 2021-03-28

- [#604](https://github.com/equinor/webviz-subsurface/pull/604) - Consolidates surface loading and statistical calculation of surfaces by introducing a shared
  SurfaceSetModel. Refactored SurfaceViewerFMU to use SurfaceSetModel.
- [#586](https://github.com/equinor/webviz-subsurface/pull/586) - Added phase ratio vs pressure and density vs pressure plots. Added unit and density functions to PVT library. Refactored code and added checklist for plots to be viewed in PVT plot plugin. Improved the layout.
- [#599](https://github.com/equinor/webviz-subsurface/pull/599) - Fixed an issue in ParameterAnalysis where the plugin did not initialize without FIELD vectors

### Fixed

- [#602](https://github.com/equinor/webviz-subsurface/pull/602) - Prevent calculation of data for download at initialisation of ReservoirSimulationTimeSeries.
- [#592](https://github.com/equinor/webviz-subsurface/pull/592) - Fixed bug for inferred frequency of yearly summary data.
- [#594](https://github.com/equinor/webviz-subsurface/pull/594) - Fixed bug in SurfaceViewerFMU where surfaces with only undefined values was not handled properly.
- [#584](https://github.com/equinor/webviz-subsurface/pull/584) - Fixed bug for in RelativePermeability plugin where it was not possible to plot against oil saturation axis when using relperm data of "family 2".
- [#595](https://github.com/equinor/webviz-subsurface/pull/595) - Raise a descriptive error in SurfaceViewerFMU plugin if no surfaces are available.

## [0.1.9] - 2021-02-23

### Fixed

- [#569](https://github.com/equinor/webviz-subsurface/pull/569) - Allow sharing of ensemble smry datasets in memory between plugins instances. Note that currently sharing can only be accomplished between plugin instances that use the same ensembles, column_keys and time_index.
- [#552](https://github.com/equinor/webviz-subsurface/pull/552) - Fixed an issue where webvizstore was not properly initialized in ParameterAnalysis plugin
- [#549](https://github.com/equinor/webviz-subsurface/pull/549) - Fixed issue in WellCrossSectionFMU that prevented use of user provided colors.
- [#561](https://github.com/equinor/webviz-subsurface/pull/561) - Fixed issue in ParameterAnalysis for non-numeric parameters (dropping them).

## [0.1.8] - 2021-01-26

### Changed

- [#538](https://github.com/equinor/webviz-subsurface/issues/538) - Refactored code for reading Eclipse INIT files and added framework for units and unit conversions.
- [#544](https://github.com/equinor/webviz-subsurface/pull/544) - All plugins now use new special `webviz_settings` argument to plugin's `__init__` method for common settings in favor of piggybacking dictionary onto the to the Dash applicaton object.
- [#541](https://github.com/equinor/webviz-subsurface/pull/541) - Implemented new onepass shader for all surface plugins.

### Fixed

- [#536](https://github.com/equinor/webviz-subsurface/pull/536) - Fixed issue and bumped dependencies related to Pandas version 1.2.0. Bumped dependency to webviz-config to support mypy typechecks.

## [0.1.7] - 2020-12-19

### Fixed

- [#526](https://github.com/equinor/webviz-subsurface/pull/526) - Fixes to `SurfaceViewerFMU`. User defined map units are now correctly displayed. Map height can now be set (useful for maps with elongated geometry). Added some missing documentation
- [#531](https://github.com/equinor/webviz-subsurface/pull/531) - The change in [#505](https://github.com/equinor/webviz-subsurface/pull/505) resulted in potentially very large datasets when using `raw` sampling. Some users experienced `MemoryError`. `column_keys` filtering is therefore now used when loading and storing data if `sampling` is `raw` in plugins using `UNSMRY` data, most noticable in `BhpQc` which has `raw` as the default and only option.

### Added

- [#529](https://github.com/equinor/webviz-subsurface/pull/529) - Added support for PVDO and PVTG to PVT plot and to respective data modules.
- [#509](https://github.com/equinor/webviz-subsurface/pull/509) - Added descriptive hoverinfo to `ParameterAnalysis`. Average and standard deviation of parameter value
  for each ensemble shown on mouse hover over figure. Included dynamic sizing of plot titles and plot spacing to optimize the appearance of plots when many parameters are plotted.

## [0.1.6] - 2020-11-30

### Fixed

- [#505](https://github.com/equinor/webviz-subsurface/pull/505) - Fixed recent performance regression issue for loading of UNSMRY data. Loading times when multiple plugins are using the same data is now significantly reduced. Note that all UNSMRY vectors are now stored in portable apps, independent of choice of column_keys in individual plugins.

## [0.1.5] - 2020-11-26

### Added

- [#478](https://github.com/equinor/webviz-subsurface/pull/478) - New plugin `AssistedHistoryMatchingAnalysis`. This dashboard helps to analyze the update step performed during assisted history match. E.g. which observations are causing an update in a specific parameter. Based on Kolmogorov–Smirnov.
- [#494](https://github.com/equinor/webviz-subsurface/pull/494) - New plugin `ParameterAnalysis`. Dashboard to visualize parameter distributions and statistics for FMU ensembles, and to investigate parameter correlations on reservoir simulation time series data.

### Fixed

- [#486](https://github.com/equinor/webviz-subsurface/pull/486) - Bug fix in `PropertyStatistics`. Show realization number instead of dataframe index for hover text.
- [#498](https://github.com/equinor/webviz-subsurface/pull/498) - Bug fix in `RFT-plotter`. Sort dataframe by date to get correct order in date-slider.

## [0.1.4] - 2020-10-29

### Added

- [#457](https://github.com/equinor/webviz-subsurface/pull/457) - Raise a descriptive error if a scratch ensemble is empty, i.e. no `OK` target file is found in any realizations.
- [#427](https://github.com/equinor/webviz-subsurface/pull/427) - `BhpQc` plugin added: Quality check that simulated bottom hole pressures are realistic.
- [#481](https://github.com/equinor/webviz-subsurface/pull/481) - `RFT-plotter`: Added support for MD, and made ECLIPSE RFT data optional.
- [#467](https://github.com/equinor/webviz-subsurface/pull/467) - `PropertyStatistics` plugin added: QC and analysis of grid property statistics.

### Fixed

- [#450](https://github.com/equinor/webviz-subsurface/pull/450) - Flipped colormap for subsurface maps (such that deeper areas get darker colors). Also fixed hill shading such that input values are treated as depth, not positive elevation.
- [#459](https://github.com/equinor/webviz-subsurface/pull/459) - Bug fix in ReservoirSimulationTimeSeries. All `History` traces are now toggled when clicking `History` in the legend.
- [#474](https://github.com/equinor/webviz-subsurface/pull/474) - Bug fix in ParameterCorrelation. Constant parameters are now removed if `drop_constants` is set to `True`
- [#480](https://github.com/equinor/webviz-subsurface/pull/480) - Bug fix in SubsurfaceMap, InplaceVolumes and InplaceVolumesOneByOne: Filter on `OK` file is now applied when loading data from ensembles through fmu-ensemble.
- [#482](https://github.com/equinor/webviz-subsurface/pull/482) - Bug fix in ReservoirSimulationTimeSeries: NaN values are now dropped instead of being replaced by zeros, e.g. if some realizations are missing in one of the ensembles, if the dates don't match, or if a vector is missing in one of the ensembles.

## [0.1.3] - 2020-09-24

### Added

- [#417](https://github.com/equinor/webviz-subsurface/pull/417) - Added an optional argument `--testdata-folder` to `pytest`, can be used when [test data](https://github.com/equinor/webviz-subsurface-testdata) is in non-default location.
- [#422](https://github.com/equinor/webviz-subsurface/pull/422) - `HistoryMatch` plugin now
  quietly excludes all realizations lacking an `OK` file written by `ERT` on completion of realization workflow, similar to behavior of other plugins that read from individual realizations. Previously wrote warnings for missing data.
- [#428](https://github.com/equinor/webviz-subsurface/pull/428) - Plugin controls, such as dropdown selections, set by the user is kept on page reload.
- [#435](https://github.com/equinor/webviz-subsurface/pull/435) - Suppress a warning in SurfaceViewerFMU when calculating statistics from surfaces where one or more surface only has NaN values. [#399](https://github.com/equinor/webviz-subsurface/pull/399)
- [#438](https://github.com/equinor/webviz-subsurface/pull/438) - Improved documentation of generation of data input for `RelativePermability` plugin.
- [#434](https://github.com/equinor/webviz-subsurface/pull/434) - Improved hillshading and colors in plugins with map views.
- [#439](https://github.com/equinor/webviz-subsurface/pull/439) - Pie chart and bar chart are now visualized together in `DiskUsage`. Free space is now visualized as well.

### Fixed

- [#432](https://github.com/equinor/webviz-subsurface/pull/432) - Bug fix in ReservoirSimulationTimeSeries. Vectors starting with A, V, G, I, N, T, V and L resulted in crash due to a bug introduced in [#373](https://github.com/equinor/webviz-subsurface/pull/373) (most notably group and aquifer vectors).
- [#442](https://github.com/equinor/webviz-subsurface/pull/442) - Bug fix in ReservoirSimulationTimeSeries. Wrong realization number was shown if data set contained missing realizations. Now uses correct realization number from data.
- [#447](https://github.com/equinor/webviz-subsurface/pull/447) - Changed two `webvizstore` decorated functions such that they do not take in `pandas` objects as arguments, which are known to not have `repr()` useful for hashing.

## [0.1.2] - 2020-08-24

### Changed

- [#415](https://github.com/equinor/webviz-subsurface/pull/415) - Now using `xml` package from standard Python library (together with [`defusexml`](https://pypi.org/project/defusedxml/)) instead of [`bs4`](https://pypi.org/project/beautifulsoup4/).
