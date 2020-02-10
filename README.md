[![PyPI version](https://badge.fury.io/py/webviz-subsurface.svg)](https://badge.fury.io/py/webviz-subsurface)
[![Build Status](https://travis-ci.org/equinor/webviz-subsurface.svg?branch=master)](https://travis-ci.org/equinor/webviz-subsurface)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/9fd7a8b451754841a1eb6600c08be967)](https://www.codacy.com/manual/webviz/webviz-subsurface?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=equinor/webviz-subsurface&amp;utm_campaign=Badge_Grade)
[![Python 3.6 | 3.7 | 3.8](https://img.shields.io/badge/python-3.6%20|%203.7%20|%203.8-blue.svg)](https://www.python.org/)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

## Webviz subsurface

> :sparkles::eyeglasses: **[Live demo application](https://webviz-subsurface-example.azurewebsites.net)**

### Introduction

This repository contains subsurface specific standard `webviz` containers, which are used as
plugins in [webviz-config](https://github.com/equinor/webviz-config).

### Installation


The easiest way of installing this package is to run
```bash
pip install webviz-subsurface
```
Add `--upgrade` if you have installed earlier, but want to upgrade to a newer version.

If you want to install the latest, unreleased, code you can instead run
```bash
pip install git+https://github.com/equinor/webviz-subsurface
```

### Usage and documentation

For general usage, see the documentation on
[webviz-config](https://github.com/equinor/webviz-config). End-user documentation for
the subsurface containers are automatically built and hosted on the 
[github pages](https://equinor.github.io/webviz-subsurface/) for this repository.

There is also a [live demo application](https://webviz-subsurface-example.azurewebsites.net)
showing how a created application can look like, using the `master` branch of this repository.

### Example webviz configuration files

Example `webviz` configuration files, and corresponding test data, is available at
https://github.com/equinor/webviz-subsurface-testdata.

See that repository for instructions on how to download and run the examples.

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
also for subsurface containers, will therefore see large changes.
