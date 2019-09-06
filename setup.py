from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

tests_require = [
    'chromedriver-binary>=74.0.3729.6.0',
    'ipdb',
    'percy',
    'selenium~=3.141',
    'flake8',
    'pylint',
    'mock'
]

setup(
    name='webviz-subsurface',
    description='Webviz config containers for subsurface data',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/equinor/webviz-subsurface',
    author='R&T Equinor',
    packages=find_packages(exclude=['tests']),
    entry_points={
        'webviz_config_containers': [
            'ParameterDistribution = webviz_subsurface.containers:ParameterDistribution',
            'DiskUsage = webviz_subsurface.containers:DiskUsage',
            'SubsurfaceMap = webviz_subsurface.containers:SubsurfaceMap',
            'HistoryMatch = webviz_subsurface.containers:HistoryMatch',
            'Intersect = webviz_subsurface.containers:Intersect',
            'MorrisPlot = webviz_subsurface.containers:MorrisPlot',
            'InplaceVolumes = webviz_subsurface.containers:InplaceVolumes',
            'ReservoirSimulationTimeSeries = webviz_subsurface.containers:ReservoirSimulationTimeSeries',
            'StructuralUncertainty = webviz_subsurface.containers:StructuralUncertainty'
        ]
    },
    install_requires=[
        'scipy~=1.2',
        'dash-daq~=0.1',
        'webviz-config>=0.0.4',
        'webviz-subsurface-components',
        'pillow'
    ],
    tests_require=tests_require,
    extras_require={'tests': tests_require},
    setup_requires=['setuptools_scm~=3.2'],
    use_scm_version=True,
    zip_safe=False
)
