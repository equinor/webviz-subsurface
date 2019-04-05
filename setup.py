from setuptools import setup, find_packages

tests_require = [
    'chromedriver-binary',
    'dash>=0.38.0',
    'ipdb',
    'percy',
    'selenium',
    'flake8',
    'pylint',
    'pytest-dash>=2.1.1',
    'mock'
]

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
    install_requires=[
        'scipy>=1.2.1',
        'webviz-plotly>=0.0.1',
        'webviz-subsurface-components>=0.0.2',
        'webviz-config>=0.0.2'
    ],
    tests_require=tests_require,
    extras_require={'tests': tests_require},
    setup_requires=['setuptools_scm>=3.2.0'],
    use_scm_version=True,
    zip_safe=False
)
