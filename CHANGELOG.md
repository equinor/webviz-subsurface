# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
