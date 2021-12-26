import os
import subprocess
import sys
import threading
from datetime import datetime
from threading import Lock

from libs.parser import Parser
from libs.cli import Cli
from libs.climessage import CliMessage, ask
from libs.path import Path
from libs.threading import Thread, Threads

print_mutex = Lock()
updated = False


class GitManager:    
    @staticmethod
    def refresh(*roots, do_pull=False):
        if not roots:
            roots = [Path.scripts, Path.docs / "School"]
        
        folders = [
            folder for root in roots for folder in root.find(lambda p: (p / ".git").exists())
        ]
        
        Threads(GitManager.update, folders, do_pull=do_pull).join()
        exit_message = "Everything clean.\nExit?"
                    
        if not updated and not do_pull:
            answer = ask(exit_message)
            while not answer or (isinstance(answer, str) and answer == "pull"):
                print("Pulling..")
                Threads(GitManager.update, folders, do_pull=True).join()
                answer = ask(exit_message)

    @staticmethod
    def update(folder, do_pull=False):
        git = GitCommander(folder)
        changes = git.get("diff")
        status = git.get("status")
        clean = not changes and "nothing to commit, working tree clean" in status

        title_message = "\n".join(["", folder.name.capitalize(), "=" * 80])
        
        if do_pull:
            pull = git.get("pull")
            if "Already up to date." not in pull:
                with print_mutex:
                    print(title_message)
                    print(pull)

        elif not clean:
            with print_mutex:
                print(title_message)
                with CliMessage("Adding changes.."):
                    add = git.get("add .")
                    status = git.get("status")
                    status = Parser.after(status, "to unstage)\n")
                    clean = "nothing to commit, working tree clean" in status
                    
                if not clean:
                    global updated
                    updated = True
                    
                    print(status, end="\n\n")
                    pull = Thread(git.get, "pull", check=False).start()
                    commit_message = ask("Commit and push?")
                    pull.join()
                    
                    if commit_message == True:
                        commit_message = "Update " + str(datetime.now())
                    if commit_message:
                        commit = git.get(f"commit -m'{commit_message}'")
                        push = git.run("push")
                else:
                    print("cleaned")
                print("")
                
    @staticmethod
    def get_base_url():
        from github import Github # long import time
        g = Github(os.environ["gittoken"])
        return f"https://github.com/{g.get_user().login}"
                
    @staticmethod
    def clone(*names):
        for name in names:
            url = f"{GitManager.get_base_url()}/{name}"
            folder = Path.scripts / name
            Cli.run(
                f"git clone {url} {folder}",
                f"cd {folder}",
                "autogit install"
                )
    
    @staticmethod
    def install(*names):
        urls = [f"git+{GitManager.get_base_url()}/{name}" for name in names]
        if not urls:
            urls.append("-e .")
        Cli.run(f"pip install --force-reinstall --no-deps {url}" for url in urls)
        
class GitCommander:
    def __init__(self, folder):
        self.command_start = f'git -C "{folder}" '
        
    def get(self, command, **kwargs):
        self.check(command)
        return Cli.get(self.command_start + command, **kwargs)
        
    def run(self, command, **kwargs):
        self.check(command)
        return Cli.run(self.command_start + command, **kwargs)
    
    def check(self, command):
        if command in ["pull", "push"]:
            url = self.get("config remote.origin.url")
            if "@" not in url:
                url = url.replace("https://", f"https://{os.environ['gittoken']}@")
                self.run(f"config remote.origin.url {url}")
