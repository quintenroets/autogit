import cli
from plib import Path


def main():
    command = "pre-commit install -f"
    commands = (command, f"{command} --hook-type pre-push")
    for command in commands:
        cli.run(command)
    #project_root = cli.get("git rev-parse --show-toplevel")
    #dest = Path(project_root) / ".git" / "hooks" / "pre-commit"
    #template = Path.assets / "autogit" / "pre-commit-template"
    #template.copy_to(dest)
