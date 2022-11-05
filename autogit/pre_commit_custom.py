import cli
from plib import Path


def main():
    cli.run("pre-commit install -f")
    project_root = cli.get("git rev-parse --show-toplevel")
    dest = Path(project_root) / ".git" / "hooks" / "pre-commit"
    template = Path.assets / "autogit" / "pre-commit-template"
    template.copy_to(dest)
