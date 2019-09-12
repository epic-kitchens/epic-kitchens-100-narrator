import os
from pathlib import Path

import yaml


class Settings:
    def __init__(self):
        self.setting_dir_path = self.get_settings_path()  # create the epic dir under user's home if it doesn't exist
        self._settings = self.load_settings() if self.settings_exist() else {}

    def settings_exist(self):
        return os.path.exists(self.get_settings_path())

    def load_settings(self):
        with open(self.get_settings_path()) as f:
            settings = yaml.load(f, Loader=yaml.FullLoader)

        return settings

    def get_epic_narrator_directory(self):
        settings_dir_path = os.path.join(str(Path.home()), 'epic_narrator')

        if not os.path.exists(settings_dir_path):
            os.makedirs(settings_dir_path)

        return settings_dir_path

    def get_settings_path(self):
        return os.path.join(self.get_epic_narrator_directory(), 'settings.yml')

    def update_settings(self, **kwargs):
        for k, v in kwargs.items():
            self._settings[k] = v

        with open(self.get_settings_path(), 'w') as yaml_file:
            yaml.dump(self._settings, yaml_file, default_flow_style=False)

    def get_setting(self, key):
        return self._settings[key] if key in self._settings else None

