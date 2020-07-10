# Webviz introduction

## Usage {docsify-ignore}

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

The latter is useful when one or more plugins included in the configuration need to do
some time-consuming data aggregation on their own, before presenting it to the user.
The time-consuming part will then be done in the `build` step, and you can run your
created application as many time as you want afterwards, with as little waiting
time as possible).

The `--portable` way also has the benefit of creating a :whale: Docker setup for your
application - ready to be deployed to e.g. a cloud provider.

### Fundamental configuration {docsify-ignore}

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
