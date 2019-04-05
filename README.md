# Webviz subsurface configuration 


### Introduction

This repository contains subsurface specific standard webviz containers, which are used as
plugins in [webviz-config](https://github.com/equinor/webviz-config).


### Installation

As Dash is using Python3-only functionality, you should create a Python3
virtual environment before installation. One way of doing this is
```bash
PATH_TO_VENV='./my_new_venv'
python3 -m virtualenv $PATH_TO_VENV
source $PATH_TO_VENV/bin/activate
```

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

### Usage

For general usage, see the documentation on
[webviz-config](https://github.com/equinor/webviz-config).

Take a look at [this configuration example](./examples/basic_example.yaml)
for something subsurface specific.


### Creating new elements

If you are interested in creating new elements which can be configured through
the configuration file, take a look at the
[webviz-config contribution guide](https://github.com/equinor/webviz-config).


### Disclaimer

This is a tool under heavy development. The current configuration file layout,
also for subsurface pages, will therefore see large changes.
