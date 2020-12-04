def hex_to_rgba(hex_string: str, opacity: float = 1.0) -> str:
    """Converts the given hex color to rgba"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {opacity})"
