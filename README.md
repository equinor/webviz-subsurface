[![PyPI version](https://badge.fury.io/py/webviz-subsurface.svg)](https://badge.fury.io/py/webviz-subsurface)
[![Build Status](https://github.com/equinor/webviz-subsurface/workflows/webviz-subsurface/badge.svg)](https://github.com/equinor/webviz-subsurface/actions?query=branch%3Amaster)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/equinor/webviz-subsurface.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/equinor/webviz-subsurface/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/equinor/webviz-subsurface.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/equinor/webviz-subsurface/context:python)
[![Python 3.8 | 3.9 | 3.10](https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10-blue.svg)](https://www.python.org/)
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

### Review of contributions

When doing review of contributions, it is usually useful to also see the resulting application live, and
not only the code changes. In order to facilitate this, this repository is using GitHub actions.

When on a feature branch, and a commit message including the substring `[deploy test]` arrives, the GitHub 
action workflow will try to build and deploy a test Docker image for you (which you then can link to a web app with
e.g. automatic reload on new images). All you need to do in your own fork is to add
GitHub secrets with the following names:
  - `review_docker_registry_url`: The registry to push to (e.g. `myregistry.azurecr.io`)
  - `review_docker_registry_username`: Registry login username.
  - `review_docker_registry_token`: Registry login token (or password).
  - `review_container_name`: What you want to call the container pushed to the registry.

You are encouraged to rebase and squash/fixup unnecessary commits before pull request is merged to `master`.

### Disclaimer

This is a tool under heavy development. The current configuration file layout,
also for subsurface containers, will therefore see large changes.
