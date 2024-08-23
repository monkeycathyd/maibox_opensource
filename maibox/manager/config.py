import os.path
import yaml

cfg_name = "server_config"

if not (os.path.isfile(f"{cfg_name}.yaml") or os.path.isfile(f"{cfg_name}.yml")):
    raise Exception(f"{cfg_name} not found")

def load_config():
    cfg = {}
    if os.path.exists(f"{cfg_name}.yaml"):
        with open(f"{cfg_name}.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    elif os.path.exists(f"{cfg_name}.yml"):
        with open(f"{cfg_name}.yml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

    return cfg

config = load_config()

def get_config():
    return config

def get_config_with_reload():
    global config
    config = load_config()
    return config
