from pathlib import Path
from typing import List
import yaml

from fmu.ensemble import Observations


class ObservationModel:
    def __init__(self, observation_file: Path) -> None:
        self.observations = self.load_yaml(observation_file)

    @staticmethod
    def load_yaml(yaml_file):
        with open(Path(yaml_file), "r") as stream:
            return yaml.safe_load(stream)

    def get_attributes(self) -> List:
        return [attribute["key"] for attribute in self.observations.get("general", [])]

    def get_observations_for_attribute(self, attribute) -> List:
        for attr in self.observations.get("general", []):
            if str(attr["key"]) == str(attribute):
                return attr["observations"]
        return None