# Webviz introduction

### Fundamental configuration

A configuration consists of some mandatory properties, e.g. app title,
and one or more pages. A page has a title and some content.
Each page can contain as many plugins as you want.

Plugins represent predefined content, which can take one or more arguments.
Lists and descriptions of installed plugins can be found on the other subpages.

Content which is not plugins is interpreted as text paragraphs.

A simple example configuration:
```yaml
# This is a webviz configuration file example.
# The configuration files use the YAML standard (https://en.wikipedia.org/wiki/YAML).

title: Reek Webviz Demonstration

pages:

 - title: Front page
   content:
    - BannerImage:
        image: ./example_banner.png
        title: My banner image
    - Webviz created from a configuration file.

 - title: Markdown example
   content:
    - Markdown:
        markdown_file: ./example-markdown.md
```

### Command line usage

#### Get documentation

You can always run `webviz --help` to see available command line options.
To see command line options on a subcommand, run e.g. `webviz build --help`.

:books: To open the `webviz` documentation on all installed plugins, run `webviz docs`.

#### Portable vs. non-portable

Assuming you have a configuration file `your_config.yml`,
there are two main usages of `webviz`:

```bash
webviz build your_config.yml
```
and
```bash
webviz build your_config.yml --portable ./some_output_folder
python ./some_output_folder/webviz_app.py
```

**Portable**

The portable way is useful when one or more plugins included in the configuration need to do
some time-consuming data aggregation on their own, before presenting it to the user.
The time-consuming part will then be done in the `build` step, and you can run your
created application as many time as you want afterwards, with as little waiting
time as possible.

The `--portable` way also has the benefit of creating a :whale: Docker setup for your
application - ready to be deployed to e.g. a cloud provider.

**Non-portable**

Non-portable is the easiest way if none of the plugins
have time-consuming data aggregation to do.

A feature in Dash, used by `webviz` is [hot reload](https://community.plot.ly/t/announcing-hot-reload/14177).
When the Dash Python code file is saved, the content seen in the web browser is
automatically reloaded (no need for localhost server restart). This feature is passed on to
the Webviz configuration utility, meaning that if you run
```bash
webviz build ./examples/basic_example.yaml
```
and then modify `./examples/basic_example.yaml` while the Webviz application is
still running, a hot reload will occur.

#### Localhost HSTS

Previous versions of webviz generated a local certificate to force localhost
connections to go through HTTPS. This is no longer the case and localhost
connections use HTTP. As such, the `webviz certificate` command has been
deprecated.

Some browsers will force HTTPS and require extra steps to remove this security.
Note that this is safe as no external computer may connect to a localhost
server.

If you're having issues connecting to a localhost server running Webviz due to
security issues, perform the following steps:

##### Google Chrome and Chromium

These are the steps to remove HSTS, a security feature that forces HTTPS
connections even though the user has specified HTTP:

1. Navigate to chrome://net-internals/#hsts
2. In the **Delete domain security policies**, type in "localhost" and click
   delete

##### Firefox

Firefox does not have issues connecting to localhost addresses over HTTP.

#### User preferences

You can set preferred :rainbow: theme and/or :earth_africa: browser, such that `webviz` remembers it for later
runs. E.g.

```bash
webviz preferences --theme equinor --browser firefox
```

#### YAML schema

If you are using an editor that supports YAML file validation towards a schema (like Visual Studio Code),
Webviz can provide your editor with a schema which then will help you with e.g. auto-completion,
detect mistakes immediately and get hover description on different plugins.

##### Visual Studio Code

If you are using [Visual Studio Code](https://code.visualstudio.com/) as editor you can
follow these steps in order to enable validation:

1) Open Visual Studio Code by e.g. running the command `code`
2) From there, open the "Extension Marketplace" by e.g. `Ctrl`+`Shift`+`X`
3) Search for the extension `redhat.vscode-yaml` (which is [Red Hat's YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml))
4) Click `Install`
5) Open `settings.json` by e.g. `Ctrl`+`,`
6) Search for the setting `Yaml: Schemas` and click "Edit in `settings.json`"
7) Between `yaml.schemas: {` and the following `}` insert:
    ```json
    "PATH_TO_YOUR_SCHEMA": ["*webviz*.{yml, yaml}"]
    ```
   where you replace `PATH_TO_YOUR_SCHEMA` with what you get from one of these options:
      * Use [one of the online URLs](https://equinor.github.io/webviz-awesome/)
        where regularly updated schemas are hosted.
      * Run `webviz schema` and use the file path the schema is written to.
        Note that if you use this option you need to rerun `webviz schema`
        when you update or install new plugin projects in order to
        keep the schema used by the editor updated with what is actually installed.

After these steps you will start getting help from the editor on YAML files
having `webviz` as part of the filename. You might have to restart the editor
after updating the settings.

#### Logging

The default logging configuration for a Webviz application is to only show log messages with level `WARNING` or `ERROR`.
This global logging level can be changed on the command line using the `--loglevel` argument like this:
```bash
webviz build ./examples/basic_example.yaml --loglevel INFO
```

In practice, setting the global logging level to `INFO` or `DEBUG` will likely flood the log with messages from various 
sub-modules, possibly obscuring messages from the module(s) of interest. To allow finer grain control over logging, 
Webviz accepts the `--logconfig` command line argument which allows detailed logging configuration through a YAML file:
```bash
webviz build ./examples/basic_example.yaml --logconfig my_log_config.yaml
```

The YAML file is expected to contain a dictionary with logging configuration adhering to the [schema described 
here](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema). This allows for full 
flexibility with regards to configuring logging in the Webviz application, including setting multiple handlers, 
filtering and customized log message formatting.

Included below is a simple YAML dictionary showing an *incremental* configuration suitable for controlling the level of the 
root logger and a few named loggers. Please note the mandatory `version` key and the inclusion of the `incremental` key 
(see Python docs for more information on [incremental configurations](https://docs.python.org/3/library/logging.config.html#incremental-configuration)).
If you need more flexibility than incremental configurations allow, you are free to specify a full configuration, but be
aware that this quickly becomes quite involved and requires a good understanding of the schema mentioned above.

```yaml
# This is a skeleton for a simple, incremental logging configuration.
# See https://docs.python.org/3/library/logging.config.html#logging-config-dictschema for schema.

version: 1
incremental: True

root:
  level: DEBUG
loggers:
  werkzeug:
    level: ERROR
  some.other.module:
    level: INFO
```

Please note that if both `--loglevel` and `--logconfig` are specified, the latter will take precedence. Internally, the 
global log level set by `--loglevel` will be applied first. Then the configuration specified by `--logconfig` will
be applied, possibly overwriting any overlapping settings.

#### Deployment

When you have created a portable Webviz application, you are approximately one command away of either creating a new application in cloud (or updating an existing application). Note that all deploy workflows listed below require that you install the deployment dependencies first by running
```bash
pip install webviz-config[deployment]
```

##### Azure

Automatic deployment to Azure Web app service is very much possible, and only a community PR away (most of the machinery and Azure CLI wrappers are already in place through the Radix deployment feature).

##### Radix

[Radix is an open source hosting framework](https://github.com/equinor/radix-platform/) by Equinor, built on top of Kubernetes. 

###### Initial deploy

For the initial deploy workflow, you will need to have the GitHub CLI binary `gh` and
Radix CLI binary `rx` in your `$PATH`. You can download them from
https://github.com/cli/cli/releases and https://github.com/equinor/radix-cli/releases
respectively. Also make sure you have a somewhat recent `git` version available (`>=2.0`).

When you execute
```bash
webviz deploy radix ./your_portable_app owner/reponame --initial-deploy
```
where `./your_portable_app` is a generated portable app, Webviz will do the following:

* Guide you through Azure CLI, GitHub CLI and Radix CLI login procedure (if not already logged in).
* Ask for your input on necessary Radix and Azure configuration settings.
* Create Azure app registration (with necessary callback setting, client secret etc).
* Create Azure blob storage account and container (if it doesn't already exist).
* Upload static app resources (i.e. those coming from `webviz_storage`) to the blob container.
* Create a private GitHub repository at `https://github.com/owner/reponame`.
* Add the Python code to the repository, together with automatically generated Radix configuration file.
* Turning on GitHub vulnerability alerts for the new repository.
* Create the new Radix application, and configure a webhook from the GitHub repository to the Radix application.
* Add Radix SSH deploy key to the GitHub private repository.
* Set Radix secrets, as well as build and deploy the Radix application.

When the Radix application is available online, it will open in your default browser.

###### Redeploy

Overwriting, or redeploying, an existing Radix Webviz application is easier. You do
```bash
webviz deploy radix ./your_portable_app owner/reponame
```
and Webviz will:
* Guide you through Azure CLI login procedure (if not already logged in).
* Upload the new static resources to the blob storage container.
* Create a new commit in the GitHub repository `https://github.com/owner/reponame`.
* The new commit automatically triggers a new Radix build and deploy.
