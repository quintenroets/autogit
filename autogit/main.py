import argparse

from libs.cli import Cli
from libs.errorhandler import ErrorHandler

from .git import GitManager

def main():
    parser = argparse.ArgumentParser(description='Automate common git workflows')
    parser.add_argument('action', nargs="?", help='The action to do', default="refresh")
    parser.add_argument('names', nargs='*', help='repository names')
    
    Cli.set_title("Autogit")
    
    args = parser.parse_args()
    action_mapper = {
        "refresh": GitManager.refresh,
        "clone": GitManager.clone,
        "install": GitManager.install
        }
    action = action_mapper[args.action]
    with ErrorHandler():
        action(*args.names)
    
if __name__ == "__main__":
    main()
