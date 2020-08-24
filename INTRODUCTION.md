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
have time-consuming data aggregration to do.

A feature in Dash, used by `webviz` is [hot reload](https://community.plot.ly/t/announcing-hot-reload/14177).
When the Dash Python code file is saved, the content seen in the web browser is
automatically reloaded (no need for localhost server restart). This feature is passed on to
the Webviz configuration utility, meaning that if you run
```bash
webviz build ./examples/basic_example.yaml
```
and then modify `./examples/basic_example.yaml` while the Webviz application is
still running, a hot reload will occur.

#### Localhost certificate

For quick local analysis, `webviz-config` uses `https` and runs on `localhost`.
In order to create your personal :lock: `https` certificate (only valid for `localhost`), run
```bash
webviz certificate --auto-install
```
Certificate installation guidelines will be given when running the command.

#### User preferences

You can set preferred :rainbow: theme and/or :earth_africa: browser, such that `webviz` remembers it for later
runs. E.g.

```bash
webviz preferences --theme equinor --browser firefox
```

#### YAML schema

By running `webviz schema` you will get a YAML (or technically, a JSON) schema which you can use in text editors, which then will
help you with auto-completion, detect mistakes immediately, and get hover description on different plugins.

If you are using Visual Studio Code, we recommend [Red Hat's YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml). After installing the extension, and adding something like
```json
{
  ...
  "yaml.schemas": { "file:///some/path/to/your/webviz_schema.json": ["*webviz*.yml", "*webviz*.yaml"]}
}
```
to your `settings.json` file, you will get help from the editor on YAML files following the namepatterns to the right (might have to restart the editor after updating the settings).
