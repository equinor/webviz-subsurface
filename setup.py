from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

TESTS_REQUIRE = [
    "selenium>=3.141",
    "pylint",
    "mock",
    "black>=20.8b1",
    "bandit",
    "pytest-xdist",
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
        ]
    },
    entry_points={
        "webviz_config_plugins": [
            "BhpQc = webviz_subsurface.plugins:BhpQc",
            "DiskUsage = webviz_subsurface.plugins:DiskUsage",
            "HistoryMatch = webviz_subsurface.plugins:HistoryMatch",
            "HorizonUncertaintyViewer = webviz_subsurface.plugins:HorizonUncertaintyViewer",
            "InplaceVolumes = webviz_subsurface.plugins:InplaceVolumes",
            "InplaceVolumesOneByOne = webviz_subsurface.plugins:InplaceVolumesOneByOne",
            "MorrisPlot = webviz_subsurface.plugins:MorrisPlot",
            "ParameterAnalysis = webviz_subsurface.plugins:ParameterAnalysis",
            "ParameterCorrelation = webviz_subsurface.plugins:ParameterCorrelation",
            "ParameterDistribution = webviz_subsurface.plugins:ParameterDistribution",
            "ParameterParallelCoordinates = webviz_subsurface.plugins:ParameterParallelCoordinates",
            "ParameterResponseCorrelation = webviz_subsurface.plugins:ParameterResponseCorrelation",
            "PropertyStatistics = webviz_subsurface.plugins:PropertyStatistics",
            "PvtPlot = webviz_subsurface.plugins:PvtPlot",
            "RelativePermeability = webviz_subsurface.plugins:RelativePermeability",
            "ReservoirSimulationTimeSeries = webviz_subsurface.plugins:ReservoirSimulationTimeSeries",
            "ReservoirSimulationTimeSeriesOneByOne = webviz_subsurface.plugins:ReservoirSimulationTimeSeriesOneByOne",
            "ReservoirSimulationTimeSeriesRegional = webviz_subsurface.plugins:ReservoirSimulationTimeSeriesRegional",
            "RftPlotter = webviz_subsurface.plugins:RftPlotter",
            "RunningTimeAnalysisFMU = webviz_subsurface.plugins:RunningTimeAnalysisFMU",
            "SegyViewer = webviz_subsurface.plugins:SegyViewer",
            "SubsurfaceMap = webviz_subsurface.plugins:SubsurfaceMap",
            "SurfaceViewerFMU = webviz_subsurface.plugins:SurfaceViewerFMU",
            "SurfaceWithGridCrossSection = webviz_subsurface.plugins:SurfaceWithGridCrossSection",
            "SurfaceWithSeismicCrossSection = webviz_subsurface.plugins:SurfaceWithSeismicCrossSection",
            "WellCrossSection = webviz_subsurface.plugins:WellCrossSection",
            "WellCrossSectionFMU = webviz_subsurface.plugins:WellCrossSectionFMU",
            "AssistedHistoryMatchingAnalysis = webviz_subsurface.plugins:AssistedHistoryMatchingAnalysis",
        ]
    },
    install_requires=[
        "dash>=1.11",
        "dash_bootstrap_components>=0.10.3",
        "defusedxml>=0.6.0",
        # "ecl2df>=0.6.1; sys_platform=='linux'",
        "fmu-ensemble>=1.2.3",
        # "opm>=2020.10.1; sys_platform=='linux'",
        "pandas>=0.24",
        "pillow>=6.1",
        "pyscal>=0.4.1",
        "scipy>=1.2",
        "statsmodels>=0.12.1",  # indirect dependency through https://plotly.com/python/linear-fits/
        "webviz-config>=0.0.55",
        "webviz-subsurface-components>=0.2.0",
        "xtgeo>=2.8",
    ],
    tests_require=TESTS_REQUIRE,
    extras_require={"tests": TESTS_REQUIRE},
    setup_requires=["setuptools_scm~=3.2"],
    python_requires="~=3.6",
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
