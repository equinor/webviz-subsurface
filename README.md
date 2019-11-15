[![PyPI version](https://badge.fury.io/py/webviz-subsurface.svg)](https://badge.fury.io/py/webviz-subsurface)
[![Build Status](https://travis-ci.org/equinor/webviz-subsurface.svg?branch=master)](https://travis-ci.org/equinor/webviz-subsurface)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/9fd7a8b451754841a1eb6600c08be967)](https://www.codacy.com/manual/webviz/webviz-subsurface?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=equinor/webviz-subsurface&amp;utm_campaign=Badge_Grade)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

## Webviz subsurface configuration 

### Introduction

This repository contains subsurface specific standard `webviz` containers, which are used as
plugins in [webviz-config](https://github.com/equinor/webviz-config).

### Installation


The easiest way of installing this package is to run
```bash
pip install webviz-subsurface
```

If you want to install the latest code you can instead run
```bash
git clone git@github.com:Equinor/webviz-subsurface.git
cd webviz-subsurface
pip install .
```

### Usage and documentation

For general usage, see the documentation on
[webviz-config](https://github.com/equinor/webviz-config). Take a look at
[this configuration example](./examples/basic_example.yaml)
for something subsurface specific.

End-user documentation for the subsurface containers are automatically built
and hosted on the [github pages](https://equinor.github.io/webviz-subsurface/)
for this repository.

### Examples

Two examples are provided in the examples/ folder.

For both examples it is first necessary to download [webviz-subsurface-testdata](https://github.com/equinor/webviz-subsurface-testdata).

**basic_example.yaml**: Example of running webviz-subsurface with already processed files.

```bash
cd examples
git clone --depth=1 https://github.com/equinor/webviz-subsurface-testdata
webviz build basic_example.yaml
```

**full_example.yaml**: Example of running webviz-subsurface with raw FMU results.

```bash
git clone --depth=1 https://github.com/equinor/webviz-subsurface-testdata
```

Replace `./webviz-subsurface-testdata` in `examples/full_example.yaml` with the full path to the test data.

```bash
webviz build examples/full_example.yaml
```


### Creating new elements

If you are interested in creating new elements which can be configured through
the configuration file, take a look at the
[webviz-config contribution guide](https://github.com/equinor/webviz-config/blob/master/CONTRIBUTING.md).

You can do automatic linting of your code changes by running
```bash
black --check webviz_subsurface tests # Check code style
pylint webviz_subsurface tests # Check code quality
bandit -r -c ./bandit.yml webviz_subsurface tests  # Check Python security best practice
```

### Disclaimer

This is a tool under heavy development. The current configuration file layout,
also for subsurface pages, will therefore see large changes.
