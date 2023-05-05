from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

TESTS_REQUIRE = [
    "bandit",
    "black>=22.1",
    "dash[testing]",
    "flaky",
    "isort",
    "mypy",
    "pylint<=2.13.9",  # Locked due to https://github.com/equinor/webviz-subsurface/issues/1052
    "pytest-mock",
    "pytest-xdist",
    "selenium>=3.141",
    "types-pkg-resources",
    "types-pyyaml",
]

# pylint: disable=line-too-long
setup(
    name="webviz-subsurface",
    description="Webviz config plugins for subsurface data",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/equinor/webviz-subsurface",
    author="R&T Equinor",
    packages=find_packages(exclude=["tests"]),
    package_data={
        "webviz_subsurface": [
            "_abbreviations/abbreviation_data/*.json",
            "_assets/css/*.css",
            "_assets/js/*.js",
            "ert_jobs/config_jobs/*",
        ]
    },
    entry_points={
        "webviz_config_plugins": [
            "AssistedHistoryMatchingAnalysis = webviz_subsurface.plugins._assisted_history_matching_analysis:AssistedHistoryMatchingAnalysis",
            "BhpQc = webviz_subsurface.plugins._bhp_qc:BhpQc",
            "CO2Leakage = webviz_subsurface.plugins._co2_leakage:CO2Leakage",
            "DiskUsage = webviz_subsurface.plugins._disk_usage:DiskUsage",
            "EXPERIMENTALGridViewerFMU = webviz_subsurface.plugins._grid_viewer_fmu:EXPERIMENTALGridViewerFMU",
            "GroupTree = webviz_subsurface.plugins._group_tree:GroupTree",
            "HistoryMatch = webviz_subsurface.plugins._history_match:HistoryMatch",
            "HorizonUncertaintyViewer = webviz_subsurface.plugins._horizon_uncertainty_viewer:HorizonUncertaintyViewer",
            "InplaceVolumes = webviz_subsurface.plugins._inplace_volumes:InplaceVolumes",
            "InplaceVolumesOneByOne = webviz_subsurface.plugins._inplace_volumes_onebyone:InplaceVolumesOneByOne",
            "LinePlotterFMU = webviz_subsurface.plugins._line_plotter_fmu.line_plotter_fmu:LinePlotterFMU",
            "MapViewerFMU = webviz_subsurface.plugins._map_viewer_fmu:MapViewerFMU",
            "MorrisPlot = webviz_subsurface.plugins._morris_plot:MorrisPlot",
            "ParameterAnalysis = webviz_subsurface.plugins._parameter_analysis:ParameterAnalysis",
            "ParameterCorrelation = webviz_subsurface.plugins._parameter_correlation:ParameterCorrelation",
            "ParameterDistribution = webviz_subsurface.plugins._parameter_distribution:ParameterDistribution",
            "ParameterParallelCoordinates = webviz_subsurface.plugins._parameter_parallel_coordinates:ParameterParallelCoordinates",
            "ParameterResponseCorrelation = webviz_subsurface.plugins._parameter_response_correlation:ParameterResponseCorrelation",
            "ProdMisfit = webviz_subsurface.plugins._prod_misfit:ProdMisfit",
            "PropertyStatistics = webviz_subsurface.plugins._property_statistics:PropertyStatistics",
            "PvtPlot = webviz_subsurface.plugins._pvt_plot:PvtPlot",
            "RelativePermeability = webviz_subsurface.plugins._relative_permeability:RelativePermeability",
            "ReservoirSimulationTimeSeries = webviz_subsurface.plugins._reservoir_simulation_timeseries:ReservoirSimulationTimeSeries",
            "ReservoirSimulationTimeSeriesOneByOne = webviz_subsurface.plugins._reservoir_simulation_timeseries_onebyone:ReservoirSimulationTimeSeriesOneByOne",
            "ReservoirSimulationTimeSeriesRegional = webviz_subsurface.plugins._reservoir_simulation_timeseries_regional:ReservoirSimulationTimeSeriesRegional",
            "RftPlotter = webviz_subsurface.plugins._rft_plotter:RftPlotter",
            "RunningTimeAnalysisFMU = webviz_subsurface.plugins._running_time_analysis_fmu:RunningTimeAnalysisFMU",
            "SegyViewer = webviz_subsurface.plugins._segy_viewer:SegyViewer",
            "SeismicMisfit = webviz_subsurface.plugins._seismic_misfit:SeismicMisfit",
            "SimulationTimeSeries = webviz_subsurface.plugins._simulation_time_series:SimulationTimeSeries",
            "SimulationTimeSeriesOneByOne = webviz_subsurface.plugins._simulation_time_series_onebyone:SimulationTimeSeriesOneByOne",
            "StructuralUncertainty = webviz_subsurface.plugins._structural_uncertainty:StructuralUncertainty",
            "SubsurfaceMap = webviz_subsurface.plugins._subsurface_map:SubsurfaceMap",
            "SurfaceViewerFMU = webviz_subsurface.plugins._surface_viewer_fmu:SurfaceViewerFMU",
            "SurfaceWithGridCrossSection = webviz_subsurface.plugins._surface_with_grid_cross_section:SurfaceWithGridCrossSection",
            "SurfaceWithSeismicCrossSection = webviz_subsurface.plugins._surface_with_seismic_cross_section :SurfaceWithSeismicCrossSection",
            "SwatinitQC = webviz_subsurface.plugins._swatinit_qc:SwatinitQC",
            "TornadoPlotterFMU = webviz_subsurface.plugins._tornado_plotter_fmu:TornadoPlotterFMU",
            "VfpAnalysis = webviz_subsurface.plugins._vfp_analysis:VfpAnalysis",
            "VolumetricAnalysis = webviz_subsurface.plugins._volumetric_analysis:VolumetricAnalysis",
            "WellAnalysis = webviz_subsurface.plugins._well_analysis:WellAnalysis",
            "WellCompletion = webviz_subsurface.plugins._well_completion:WellCompletion",
            "WellCompletions = webviz_subsurface.plugins._well_completions:WellCompletions",
            "WellCrossSection = webviz_subsurface.plugins._well_cross_section:WellCrossSection",
            "WellCrossSectionFMU = webviz_subsurface.plugins._well_cross_section_fmu:WellCrossSectionFMU",
            "WellLogViewer = webviz_subsurface.plugins._well_log_viewer:WellLogViewer",
        ],
        "console_scripts": ["smry2arrow_batch=webviz_subsurface.smry2arrow_batch:main"],
    },
    install_requires=[
        "dash>=2.0.0",
        "dash_bootstrap_components>=0.10.3",
        "dash-daq>=0.5.0",
        "defusedxml>=0.6.0",
        "ecl2df>=0.15.0; sys_platform=='linux'",
        "flask-caching",
        "fmu-ensemble>=1.2.3",
        "fmu-tools>=1.8",
        "geojson>=2.5.0",
        "jsonschema>=3.2.0",
        "opm>=2020.10.1,<=2022.10; sys_platform=='linux'",
        "pandas>=1.1.5,<2.0",
        "pillow>=6.1",
        "pyarrow>=5.0.0",
        "pyjwt>=2.6.0",
        "pyscal>=0.7.5",
        "scipy>=1.2",
        "statsmodels>=0.12.1",  # indirect dependency through https://plotly.com/python/linear-fits/
        "xtgeo>=2.20.0",
        "vtk>=9.2.2",
        "webviz-config",
        "webviz-core-components>=0.6",
        "webviz-subsurface-components>=0.4.15",
    ],
    extras_require={"tests": TESTS_REQUIRE},
    setup_requires=["setuptools_scm~=3.2"],
    python_requires="~=3.8",
    use_scm_version=True,
    zip_safe=False,
    project_urls={
        "Documentation": "https://equinor.github.io/webviz-subsurface",
        "Download": "https://pypi.org/project/webviz-subsurface/",
        "Source": "https://github.com/equinor/webviz-subsurface",
        "Tracker": "https://github.com/equinor/webviz-subsurface/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Environment :: Web Environment",
        "Framework :: Dash",
        "Framework :: Flask",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
)
