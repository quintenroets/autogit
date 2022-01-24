import cli
from libs.threading import Threads
from plib import Path

from .repo import Repo


def get_repos(*roots):
    if not roots:
        roots = [Path.scripts]

    def is_git(folder):
        return (folder / ".git").exists()

    repos = [
        Repo(folder)
        for root in roots
        for folder in root.find(is_git, follow_symlinks=False)
    ]
    return repos


class RepoManager:
    updated = False

    @staticmethod
    def refresh(*roots, do_pull=False):
        repos = get_repos(*roots)
        if do_pull:
            with cli.console.status("Pulling"):
                Threads(r.do_pull for r in repos).start().join()

            for r in repos:
                RepoManager.updated = RepoManager.updated or r.show_pull()
            if not RepoManager.updated:
                cli.console.print("No remote changes [bold green]\u2713")

        else:
            Threads(r.check_updates for r in repos).start().join()
            for r in repos:
                if r.update:
                    r.process_updates()
                    RepoManager.updated = True

    @staticmethod
    def run_hooks():
        repos = get_repos()
        Threads(r.check_updates for r in repos).start().join()
        for r in repos:
            if r.changes:
                r.add()
                r.run_hooks()
