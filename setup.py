from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

TESTS_REQUIRE = ["selenium>=3.141", "pylint", "mock", "black", "bandit", "pytest-xdist"]

setup(
    name="webviz-subsurface",
    description="Webviz config plugins for subsurface data",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/equinor/webviz-subsurface",
    author="R&T Equinor",
    packages=find_packages(exclude=["tests"]),
    package_data={"webviz_subsurface": ["_abbreviations/abbreviation_data/*.json"]},
    entry_points={
        "webviz_config_plugins": [
            "ParameterDistribution = webviz_subsurface.plugins:ParameterDistribution",
            "ParameterCorrelation = webviz_subsurface.plugins:ParameterCorrelation",
            "ParameterResponseCorrelation = "
            + "webviz_subsurface.plugins:ParameterResponseCorrelation",
            "DiskUsage = webviz_subsurface.plugins:DiskUsage",
            "SubsurfaceMap = webviz_subsurface.plugins:SubsurfaceMap",
            "HistoryMatch = webviz_subsurface.plugins:HistoryMatch",
            "MorrisPlot = webviz_subsurface.plugins:MorrisPlot",
            "InplaceVolumes = webviz_subsurface.plugins:InplaceVolumes",
            "InplaceVolumesOneByOne = webviz_subsurface.plugins:InplaceVolumesOneByOne",
            "ReservoirSimulationTimeSeries = "
            + "webviz_subsurface.plugins:ReservoirSimulationTimeSeries",
            "ReservoirSimulationTimeSeriesOneByOne = "
            + "webviz_subsurface.plugins:ReservoirSimulationTimeSeriesOneByOne",
            "SurfaceViewerFMU = webviz_subsurface.plugins:SurfaceViewerFMU",
            "SegyViewer = webviz_subsurface.plugins:SegyViewer",
            "SurfaceWithGridCrossSection = "
            + "webviz_subsurface.plugins:SurfaceWithGridCrossSection",
            "SurfaceWithSeismicCrossSection = "
            + "webviz_subsurface.plugins:SurfaceWithSeismicCrossSection",
            "WellCrossSection = webviz_subsurface.plugins:WellCrossSection",
            "WellCrossSectionFMU = webviz_subsurface.plugins:WellCrossSectionFMU",
            "ParameterParallelCoordinates = "
            + "webviz_subsurface.plugins:ParameterParallelCoordinates",
            "RunningTimeAnalysisFMU = webviz_subsurface.plugins:RunningTimeAnalysisFMU",
            "RelativePermeability = webviz_subsurface.plugins:RelativePermeability",
            "ReservoirSimulationTimeSeriesRegional = "
            + "webviz_subsurface.plugins:ReservoirSimulationTimeSeriesRegional",
            "RftPlotter =  webviz_subsurface.plugins:RftPlotter",
        ]
    },
    install_requires=[
        "fmu-ensemble>=1.2.3",
        "matplotlib>=3.0",
        "pandas>=0.24",
        "pillow>=6.1",
        "pyscal>=0.4.1",
        "scipy>=1.2",
        "webviz-config>=0.0.55",
        "webviz-subsurface-components>=0.0.23",
        "xtgeo>=2.8",
    ],
    tests_require=TESTS_REQUIRE,
    extras_require={"tests": TESTS_REQUIRE},
    setup_requires=["setuptools_scm~=3.2"],
    python_requires="~=3.6",
    use_scm_version=True,
    zip_safe=False,
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
