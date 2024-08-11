import json
import os.path
import yaml

if not (os.path.isfile("server_config.yaml") or os.path.isfile("server_config.yml")):
    raise Exception("server_config not found")

config = {}
if os.path.exists("server_config.yaml"):
    with open("server_config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
elif os.path.exists("server_config.yml"):
    with open("server_config.yml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

def get_config():
    return config

def get_config_with_reload():
    global config
    if os.path.exists("server_config.yaml"):
        with open("server_config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    elif os.path.exists("server_config.yml"):
        with open("server_config.yml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    return config
