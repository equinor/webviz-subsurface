from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

TESTS_REQUIRE = ["selenium~=3.141", "pylint", "mock", "black", "bandit", "pytest-xdist"]

setup(
    name="webviz-subsurface",
    description="Webviz config plugins for subsurface data",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/equinor/webviz-subsurface",
    author="R&T Equinor",
    packages=find_packages(exclude=["tests"]),
    package_data={"webviz_subsurface": ["_abbreviations/*.json"]},
    entry_points={
        "webviz_config_plugins": [
            "ParameterDistribution = webviz_subsurface.plugins:ParameterDistribution",
            "ParameterCorrelation = webviz_subsurface.plugins:ParameterCorrelation",
            "ParameterResponseCorrelation = "
            + "webviz_subsurface.plugins:ParameterResponseCorrelation",
            "DiskUsage = webviz_subsurface.plugins:DiskUsage",
            "SubsurfaceMap = webviz_subsurface.plugins:SubsurfaceMap",
            "HistoryMatch = webviz_subsurface.plugins:HistoryMatch",
            "Intersect = webviz_subsurface.plugins:Intersect",
            "MorrisPlot = webviz_subsurface.plugins:MorrisPlot",
            "InplaceVolumes = webviz_subsurface.plugins:InplaceVolumes",
            "InplaceVolumesOneByOne = webviz_subsurface.plugins:InplaceVolumesOneByOne",
            "ReservoirSimulationTimeSeries = "
            + "webviz_subsurface.plugins:ReservoirSimulationTimeSeries",
            "ReservoirSimulationTimeSeriesOneByOne = "
            + "webviz_subsurface.plugins:ReservoirSimulationTimeSeriesOneByOne",
            "SegyViewer = webviz_subsurface.plugins:SegyViewer",
            "SurfaceWithGridCrossSection = "
            + "webviz_subsurface.plugins:SurfaceWithGridCrossSection",
            "SurfaceWithSeismicCrossSection = "
            + "webviz_subsurface.plugins:SurfaceWithSeismicCrossSection",
            "WellCrossSection = webviz_subsurface.plugins:WellCrossSection",
            "WellCrossSectionFMU = webviz_subsurface.plugins:WellCrossSectionFMU",
        ]
    },
    install_requires=[
        "scipy~=1.2",
        "matplotlib~=3.0",
        "pandas~=0.24",
        "pillow~=6.1",
        "xtgeo~=2.1",
        "webviz-config>=0.0.48",
        "webviz-subsurface-components>=0.0.22",
    ],
    tests_require=TESTS_REQUIRE,
    extras_require={"tests": TESTS_REQUIRE},
    setup_requires=["setuptools_scm~=3.2"],
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
