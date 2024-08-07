import os

if os.path.exists("logging.log"):
    with open("logging.log", "w") as f:
        f.write("")

git_sha = "undefined"
if os.path.exists("git_sha"):
    git_sha = open("git_sha").read()