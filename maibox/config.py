import json
import os.path

if not os.path.exists("server_config.json"):
    raise Exception("server_config.json not found")

with open("server_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
def check_config(config):
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, (dict, list)):
                check_config(value)  # Recursive call for nested dicts/lists
            elif isinstance(value, bool):
                continue
            elif not value:
                raise Exception(f"Empty value found at key: {key}")
    elif isinstance(config, list):
        for index, item in enumerate(config):
            if isinstance(item, (dict, list)):
                check_config(item)  # Recursive call for nested lists containing dicts/lists
            elif isinstance(item, bool):
                continue
            elif not item:
                raise Exception(f"Empty value found at list index: {index}")

check_config(config)

def get_config():
    return config

def get_config_with_reload():
    global config
    with open("server_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    check_config(config)
    return config
