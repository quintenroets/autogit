import cli
import gui
from plib import Path

from .token import git_token


class Installer:
    @classmethod
    @property
    def git(cls):
        from github import Github  # noqa: autoimport

        return Github(git_token())

    @classmethod
    @property
    def base_url(cls):
        return f"https://{git_token()}@github.com/{cls.git.get_user().login}"

    @staticmethod
    def get_all_repos():
        user = Installer.git.get_user()
        return [
            repo.name
            for repo in user.get_repos()
            if repo.get_collaborators().totalCount == 1
            and repo.get_collaborators()[0].login == user.login
            and not repo.archived
        ]

    @staticmethod
    def clone(*names):
        if not names:
            with cli.console.status("Fetching repo list"):
                repos = GitManager.get_all_repos()
            name = gui.ask("Choose repo", repos)
            if name:
                names = [name]

        for name in names:
            url = f"{Installer.base_url}/{name}"
            folder = Path.scripts / name
            if not folder.exists():
                cli.run("git clone", url, folder)

    @staticmethod
    def install(*names):
        urls = [f"git+{Installer.base_url}/{name}" for name in names]
        if not urls:
            urls.append(("-e", "."))
        for url in urls:
            cli.run("pip install", {"force-reinstall", "no-deps"}, url)
        for name in names:
            folder = Path.scripts / name
            folder.rmtree()
