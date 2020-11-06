# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
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
