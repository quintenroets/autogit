import cli
import gui
import os
import shlex
import tbhandler.threading as threading

from plib import Path

from libs.parser import Parser


print_mutex = threading.Lock()


def ask_push():
    default = 'cancel'
    response = cli.prompt('Commit message', default=default)
    response = response != default and response
    return response


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
        threading.Threads(GitManager.update, folders, do_pull=do_pull).join()
        
        if do_pull and not GitManager.updated:
            print('Everything clean.')
            

    @staticmethod
    def update(folder, do_pull=False):
        git = GitCommander(folder)
        changes = git.get('diff')
        status = git.status()
        
        # commited before but the push has failed
        comitted = not changes and not status and any(['ahead' in line and '##' in line for line in git.get('status --porcelain -b')])
        
        if do_pull:
            pull = git.get('pull')
            if 'Already up to date.' not in pull:
                with print_mutex:
                    cli.console.rule(git.title)
                    print(pull)

        if changes or status or comitted:
            with print_mutex:
                cli.console.rule(git.title)
                if not comitted:
                    with cli.console.status('Adding changes'):
                        add = git.get('add .')
                        status = git.status()
                    
                if status:
                    GitManager.updated = True
                    git.show_status(status)
                
                    pull = threading.Thread(git.get, 'pull', check=False).start()
                    commit_message = ask_push()
                
                    while commit_message == 'show':
                        git.show_verbose_status()
                        commit_message = ask_push()

                    if commit_message:
                        pull.join()
                        commit = git.get(f'commit -m"{commit_message}"')
                        git.run('push')
                elif comitted:
                    GitManager.updated = True
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


symbols = {'M': '*', 'D': '-', 'A': '+', 'R': '*', 'C': '*'}
colors = {'M': 'blue', 'D': 'red', 'A': 'green', 'R': 'blue', 'C': 'blue'}


class GitCommander:
    def __init__(self, folder):
        self.command_start = ('git', '-C', folder)
        self.title = folder.name.capitalize()
        self.filenames = {}
        
    def show_status(self, status):
        filenames = {}
        for line in status:
            symbol, filename = line.split()
            self.filenames[filename] = symbol
            color = colors.get(symbol, '')
            line = symbols.get(symbol, '') + f' [bold {color}]' + filename
            cli.console.print(line)
                        
        cli.console.print('')
        
    def show_verbose_status(self):
        status = self.lines('status -v', tty=True)
        cli.run('clear')
        cli.console.rule(self.title)
        diff_indices = [i for i, line in enumerate(status) if 'diff' in line] + [len(status)]
        for start, stop in zip(diff_indices, diff_indices[1:]):
            title = status[start]
            for filename, symbol in self.filenames.items():
                if filename in title:
                    color = colors.get(symbol, '')
                    line = symbols.get(symbol, '') + f' [bold {color}]' + filename + '\n'
                    cli.console.print(line)
            diff = '\n'.join([l for l in status[start:stop] if '\x1b[1m' not in l]) + '\n'
            print(diff)
        
    def status(self):
        return self.lines('status --porcelain')
        
    def lines(self, command, **kwargs):
        lines = self.get(command, **kwargs).split('\n')
        lines = [l for l in lines if l]
        return lines
        
    def get(self, command, **kwargs):
        output = self.run(command, **kwargs, capture_output=True)
        if 'tty' not in kwargs:
            output = output.stdout
        return output.strip()
        
    def run(self, command, **kwargs):
        self.check(command)
        return cli.run(*self.command_start, *shlex.split(command), **kwargs)
    
    def check(self, command):
        if command in ['pull', 'push']:
            url = self.get('config remote.origin.url')
            if '@' not in url:
                url = url.replace('https://', f'https://{os.environ["gittoken"]}@')
                self.run(f'config remote.origin.url {url}')
