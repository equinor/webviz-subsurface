from pathlib import Path
from typing import Any, Dict, List

import yaml


def load_and_validate_log_templates(log_templates: List[Path]) -> Dict[str, Any]:
    validated_templates = {}
    for idx, template_path in enumerate(log_templates):
        template = yaml.safe_load(template_path.read_text())
        # Validate against json schema here when available
        # https://github.com/equinor/webviz-subsurface-components/issues/508
        template_name = template.get("name", f"template_{idx+1}")
        validated_templates[template_name] = template
    return validated_templates
