from setuptools import setup, find_packages

setup(
    name='webviz-subsurface',
    version='0.0.1',
    description='Webviz config containers for subsurface data',
    url='https://github.com/equinor/webviz-subsurface',
    author='R&T Equinor',
    packages=find_packages(exclude=['tests']),
    entry_points={
        'webviz_config_containers': [
            'SummaryStats = webviz_subsurface.containers:SummaryStats',
            'ParameterDistribution = webviz_subsurface.containers:ParameterDistribution',
            'DiskUsage = webviz_subsurface.containers:DiskUsage',
            'SubsurfaceMap = webviz_subsurface.containers:SubsurfaceMap',
            'HistoryMatch = webviz_subsurface.containers:HistoryMatch'
        ]
    },
    zip_safe=False
)
