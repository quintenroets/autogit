import cli
import os
import threading

from plib import Path
from libs.parser import Parser
from tbhandler import Threads
from .repo import Repo


class RepoManager:
    updated = False
    
    @staticmethod
    def refresh(*roots, do_pull=False):
        if not roots:
            roots = [Path.scripts] 
        
        def is_git(folder):
            return (folder / '.git').exists()
        
        folders = [
            folder for root in roots for folder in root.find(is_git, follow_symlinks=False)
        ]
        repos = [Repo(folder) for folder in folders]
        if do_pull:
            with cli.console.status('Pulling'):
                Threads(r.do_pull for r in repos).join()

            for r in repos:
                RepoManager.updated = RepoManager.updated or r.show_pull()
            if not RepoManager.updated:
                cli.console.print('No remote changes [bold green]\u2713')
                
        else:
            Threads(r.check_updates for r in repos).join()
            for r in repos:
                if r.update:
                    r.process_updates()
                    RepoManager.updated = True
