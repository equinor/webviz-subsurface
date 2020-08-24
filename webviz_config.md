# Plugin package webviz_config

?> :bookmark: This documentation is valid for version `0.1.0` of `webviz_config`. 

   
These are the basic Webviz configuration plugins, distributed through
the utility itself.

 

---



<div class="plugin-doc">

#### BannerImage

<!-- tabs:start -->
   

#### ** Description **

Adds a full width banner image, with an optional overlayed title.
Useful on e.g. the front page for introducing a field or project.


 

#### ** Arguments **

   

* **`image`:** Path to the picture you want to add.                Either absolute path or relative to the configuration file.
* **`title`:** Title which will be overlayed over the banner image.
* **`color`:** Color to be used for the font.
* **`shadow`:** Set to `False` if you do not want text shadow for the title.
* **`height`:** Height of the banner image (in pixels).


```yaml
    - BannerImage:
        image:  # Required, type str (corresponding to a path).
        title: "" # Optional, type str.
        color: "white" # Optional, type str.
        shadow: true # Optional, type bool.
        height: 300 # Optional, type int.
```

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### DataTable

<!-- tabs:start -->
   

#### ** Description **

Adds a table to the webviz instance, using tabular data from a provided csv file.
If feature is requested, the data could also come from a database.


 

#### ** Arguments **

   

* **`csv_file`:** Path to the csv file containing the tabular data. Either absolute               path or relative to the configuration file.
* **`sorting`:** If `True`, the table can be sorted interactively based              on data in the individual columns.
* **`filtering`:** If `True`, the table can be filtered based on values in the                individual columns.
* **`pagination`:** If `True`, only a subset of the table is displayed at once.                 Different subsets can be viewed from 'previous/next' buttons


```yaml
    - DataTable:
        csv_file:  # Required, type str (corresponding to a path).
        sorting: true # Optional, type bool.
        filtering: true # Optional, type bool.
        pagination: true # Optional, type bool.
```

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### EmbedPdf

<!-- tabs:start -->
   

#### ** Description **

Embeds a given PDF file into the page.

!> Webviz does not scan your PDF for malicious code. Make sure it comes from a trusted source.

 

#### ** Arguments **

   

* **`pdf_file`:** Path to the PDF file to include. Either absolute path or   relative to the configuration file.
* **`height`:** Height of the PDF object (in percent of viewport height).
* **`width`:** Width of the PDF object (in percent of available space).


```yaml
    - EmbedPdf:
        pdf_file:  # Required, type str (corresponding to a path).
        height: 80 # Optional, type int.
        width: 100 # Optional, type int.
```

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### Markdown

<!-- tabs:start -->
   

#### ** Description **

Renders and includes the content from a Markdown file.


 

#### ** Arguments **

   

* **`markdown_file`:** Path to the markdown file to render and include.                        Either absolute path or relative to the configuration file.



```yaml
    - Markdown:
        markdown_file:  # Required, type str (corresponding to a path).
```

   

#### ** Data input **


Images are supported, and should in the markdown file be given as either
relative paths to the markdown file itself, or as absolute paths.

> The markdown syntax for images has been extended to support   providing width and/or height for individual images (optional).   To specify the dimensions write e.g.
> ```markdown
> ![width=40%,height=300px](./example_banner.png "Some caption")
> ```

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### SyntaxHighlighter

<!-- tabs:start -->
   

#### ** Description **

Adds support for syntax highlighting of code. Language is automatically detected.


 

#### ** Arguments **

   

* **`filename`:** Path to a file containing the code to highlight.
* **`dark_theme`:** If `True`, the code is shown with a dark theme. Default is                 `False`, giving a light theme.


```yaml
    - SyntaxHighlighter:
        filename:  # Required, type str (corresponding to a path).
        dark_theme: false # Optional, type bool.
```

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### TablePlotter

<!-- tabs:start -->
   

#### ** Description **

Adds a plotter to the webviz instance, using tabular data from a provided csv file.
If feature is requested, the data could also come from a database.


 

#### ** Arguments **

   

* **`csv_file`:** Path to the csv file containing the tabular data.                   Either absolute path or relative to the configuration file.
* **`plot_options`:** A dictionary of plot options to initialize the plot with.
* **`filter_cols`:** Dataframe columns that can be used to filter data.
* **`filter_defaults`:** A dictionary with column names as keys,                          and a list of column values that should be preselected in the filter.                          If a columm is not defined, all values are preselected for the column.
* **`column_color_discrete_maps`:** A dictionary with column names as keys,                                     each key containing a new dictionary with the columns                                     unique values as keys, and the color they should be                                     plotted with as value. Hex values needs quotes ''                                     to not be read as a comment.
* **`lock`:** If `True`, only the plot is shown,               all dropdowns for changing plot options are hidden.


```yaml
    - TablePlotter:
        csv_file:  # Required, type str (corresponding to a path).
        plot_options: null # Optional, type dict.
        filter_cols: null # Optional, type list.
        filter_defaults: null # Optional, type dict.
        column_color_discrete_maps: null # Optional, type dict.
        lock: false # Optional, type bool.
```

 

<!-- tabs:end -->

</div>

