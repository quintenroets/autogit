import os
import subprocess
import sys
import threading
from datetime import datetime
from threading import Lock

from libs.errorhandler import ErrorHandler
from libs.parser import Parser
from libs.cli import Cli
from libs.climessage import CliMessage
from libs.path import Path
from libs.threading import Threads

roots = [
    Path.scripts,
    Path.docs / "School"
    ]

print_mutex = Lock()
updated = False

class GitManager:
    @staticmethod
    def start(do_pull=False):
        folders = GitManager.get_git_folders()
        Threads(GitManager.update, folders, do_pull=do_pull).join()
                    
        if not updated and not do_pull:
            answer = GitManager.ask_exit()
            while not answer or (isinstance(answer, str) and answer == "pull"):
                print("Pulling..")
                Threads(GitManager.update, folders, do_pull=True).join()
                answer = GitManager.ask_exit()
                
    @staticmethod
    def ask_exit():
        print("Everything clean.")
        answer = Asker.get_answer("Exit?")
        return answer
        
                    
    @staticmethod
    def get_git_folders():
        folders = [
            Path(folder)
            for root in roots
            for folder in Cli.get(
                f"find {root} -type d -execdir test -d" + " {}/.git \; -print -prune"
                # very quick command to find folders that contain .git folder
                ).split("\n")
            if folder
            ]
        return folders

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
                    asker = Asker("Commit and push?")
                    pull = git.get("pull", check=False)
                    asker.join()
                    
                    commit_message = asker.response
                    if commit_message in ["", True]:
                        commit_message = "Update " + str(datetime.now())
                    if commit_message:
                        commit = git.get(f"commit -m'{commit_message}'")
                        push = git.run("push")
                else:
                    print("cleaned")
                print("")
                
    @staticmethod
    def clone(name):
        return Cli.run(f"git clone https://github.com/quintenroets/{name}")
        
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
        
class Asker:
    def __init__(self, question):
        self.question = question
        self.response = ""
        self.start_ask()
        
    def start_ask(self):
        self.thread = threading.Thread(target=self.ask, args=(self.question, ))
        self.thread.start()
        
    def ask(self, question):
        self.response = Asker.get_answer(question)
        
    def join(self):
        self.thread.join()

    @staticmethod
    def get_answer(question):
        choice_mappers = {
            True: ["", "yes", "y"],
            False: ["no", "n"]
            }
        question += " [Y/n] "

        print(question, end="")
        choice = input().lower().strip()
        for k, v in choice_mappers.items():
            if choice in v:
                choice = k
        return choice
    
def start():
    if "clone" in sys.argv:
        GitManager.clone(sys.argv[-1])
    else:
        GitManager.start(do_pull="pull" in sys.argv)
    

def main():
    with ErrorHandler():
        start()

if __name__ == "__main__":
    main()
