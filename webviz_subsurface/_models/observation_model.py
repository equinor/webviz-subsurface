from pathlib import Path
from typing import List
import yaml

from fmu.ensemble import Observations


class ObservationModel:
    def __init__(self, observation_file: Path = None) -> None:
        self.observations = self.load_yaml(observation_file) if observation_file else {}

    @staticmethod
    def load_yaml(yaml_file):
        with open(Path(yaml_file), "r") as stream:
            return yaml.safe_load(stream)

    def get_attributes(self) -> List:
        test = [attribute["key"] for attribute in self.observations.get("smry", [])]
        print(test)
        return test

    def get_observations_for_attribute(self, attribute) -> List:
        for attr in self.observations.get("smry", []):
            if str(attr["key"]) == str(attribute):
                print("OK")
                return attr["observations"]
        return None