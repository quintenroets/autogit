import cli
import gui
import os
import shlex
import threading

from rich.console import Console
from datetime import datetime
from plib import Path

from libs.parser import Parser
from libs.threading import Thread, Threads

print_mutex = threading.Lock()
console = Console()


class GitManager:
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
        Threads(GitManager.update, folders, do_pull=do_pull).join()
        
        if do_pull and not GitManager.updated:
            print('Everything clean.')
            

    @staticmethod
    def update(folder, do_pull=False):
        git = GitCommander(folder)
        changes = git.get('diff')
        status = git.get('status --porcelain')
        
        # commited before but the push has failed
        comitted = not changes and not status and any(['ahead' in line and '##' in line for line in git.get('status --porcelain -b')])

        title = folder.name.capitalize()
        
        if do_pull:
            pull = git.get('pull')
            if 'Already up to date.' not in pull:
                with print_mutex:
                    console.rule(title)
                    print(pull)
                    GitManager.updated = True

        if changes or status or comitted:
            with print_mutex:
                console.rule(title)
                if not comitted:
                    with cli.status('Adding changes..'):
                        add = git.get('add .')
                        status = git.get('status --porcelain')
                    
                if changes or status:
                    GitManager.updated = True
                    
                    mapper = {'M': '*', 'D': '-', 'A': '+', 'R': '*', 'C': '*'}

                    status_lines = [mapper.get(line[0], '') + line[1:] for line in status.split('\n') if line]
                    if status_lines:
                        status_print = '\n'.join(status_lines + [''])
                        print(status_print)
                    
                        pull = Thread(git.get, 'pull', check=False).start()
                        commit_message = cli.ask('Commit and push?')
                    
                        while commit_message == 'show':
                            git.run('status -v')
                            commit_message = cli.ask('Commit and push?')
                    
                        if commit_message == True:
                            commit_message = 'Update ' + str(datetime.now())
                        if commit_message:
                            pull.join()
                            commit = git.get(f'commit -m"{commit_message}"')
                            git.run('push')
                    else:
                        cli.console.print('cleaned')
                elif comitted:
                    if cli.ask('Retry push?'):
                        git.run('push')
                else:
                    print('cleaned')
                print('')
                cli.run('clear')
                
    @staticmethod
    def get_git_manager():
        from github import Github # long import time
        return Github(os.environ['gittoken'])
                
    @staticmethod
    def get_base_url():
        g = GitManager.get_git_manager()
        return f'https://{os.environ["gittoken"]}@github.com/{g.get_user().login}'
    
    @staticmethod
    def get_all_repos():
        g = GitManager.get_git_manager()
        user = g.get_user()
        return [
            repo.name for repo in user.get_repos() 
            if repo.get_collaborators().totalCount == 1
            and repo.get_collaborators()[0].login == user.login 
            and not repo.archived
        ]
        
                
    @staticmethod
    def clone(*names):
        if not names:
            with cli.spinner('Fetching repo list'):
                repos = GitManager.get_all_repos()
            name = gui.ask('Choose repo', repos)
            if name:
                names = [name]
        
        for name in names:
            url = f'{GitManager.get_base_url()}/{name}'
            folder = Path.scripts / name
            if not folder.exists():
                cli.run('git clone', url, folder)
    
    @staticmethod
    def install(*names):
        urls = [f'git+{GitManager.get_base_url()}/{name}' for name in names]
        if not urls:
            urls.append(('-e', '.'))
        for url in urls:
            cli.run('pip install', {'force-reinstall', 'no-deps'}, url)
        for name in names:
            folder = Path.scripts / name
            folder.rmtree()
        
class GitCommander:
    def __init__(self, folder):
        self.command_start = ('git', '-C', folder)
        
    def run(self, command, **kwargs):
        self.check(command)
        return cli.run(*self.command_start, *shlex.split(command), **kwargs)
        
    def get(self, command, **kwargs):
        return self.run(command, **kwargs, capture_output=True).stdout.strip()
    
    def check(self, command):
        if command in ['pull', 'push']:
            url = self.get('config remote.origin.url')
            if '@' not in url:
                url = url.replace('https://', f'https://{os.environ["gittoken"]}@')
                self.run(f'config remote.origin.url {url}')
