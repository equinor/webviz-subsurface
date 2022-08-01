class LayoutStyle:
    MAIN_HEIGHT = "87vh"
    HEADER = {
        "font-size": "15px",
        "color": "black",
        "text-transform": "uppercase",
        "border-color": "black",
    }
    TABLE_HEADER = {"fontWeight": "bold"}
    TABLE_STYLE = {"max-height": MAIN_HEIGHT, "overflowY": "auto"}
    TABLE_CELL_WIDTH = 95
    TABLE_CELL_HEIGHT = "10px"
    TABLE_HIGHLIGHT = {"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"}
    TABLE_CSS = [
        {
            "selector": ".dash-spreadsheet tr",
            "rule": f"height: {TABLE_CELL_HEIGHT};",
        },
    ]
