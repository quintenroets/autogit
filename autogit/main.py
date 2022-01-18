import argparse

    
def install():
    from .installer import Installer
    Installer.install()
    

def clone():
    from .installer import Installer
    Installer.clone()
    
    
    
def refresh(do_pull=False):
    from .repomanager import RepoManager
    RepoManager.refresh(do_pull=do_pull)
    

def main():
    parser = argparse.ArgumentParser(description='Automate common git workflows')
    parser.add_argument('action', nargs='?', help='The action to do', default='refresh')
    parser.add_argument('names', nargs='*', help='repository names')
        
    args = parser.parse_args()
    action_mapper = {
        'refresh': refresh,
        'clone': clone,
        'install': install,
        'pull': lambda: refresh(do_pull=True)
        }
    
    if args.action not in action_mapper:
        raise Exception(f'{args.action} not defined')
    action = action_mapper[args.action]
    action(*args.names)
    
if __name__ == '__main__':
    main()
