import os

if os.path.exists("logging.log"):
    with open("logging.log", "w") as f:
        f.write("")