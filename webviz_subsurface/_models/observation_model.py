from pathlib import Path
from typing import Dict, List, Optional

import yaml


class ObservationModel:
    def __init__(
        self,
        observation_file: Path = None,
        observation_key: str = "general",
        remap_key: Dict[str, str] = None,
        remap_value: Dict[str, str] = None,
    ) -> None:
        self.observations = self.load_yaml(observation_file) if observation_file else {}
        self.observation_group = observation_key
        self.remap_key = remap_key if remap_key else {}
        self.remap_value = remap_value if remap_value else {}

    @staticmethod
    def load_yaml(yaml_file: Path) -> Dict:
        with open(Path(yaml_file), "r") as stream:
            return yaml.safe_load(stream)

    def get_attributes(self) -> List:
        return [
            attribute["key"]
            for attribute in self.observations.get(self.observation_group, [])
        ]

    def get_observations_for_attribute(
        self, attribute: str, value: str
    ) -> Optional[List]:
        for attr in self.observations.get(self.observation_group, []):
            if str(attr["key"]) == self.remap_key.get(attribute, attribute):
                observations = []
                for obs in attr.get("observations", []):
                    observations.append(
                        {
                            "value": obs.get("value", None),
                            "error": obs.get("error", None),
                            value: obs.get(self.remap_value.get(value, value), None),
                        }
                    )
                return observations
        return None
