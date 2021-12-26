import argparse

from .git import GitManager

def main():
    parser = argparse.ArgumentParser(description='Automate common git workflows')
    parser.add_argument('action', nargs="?", help='The action to do', default="refresh")
    parser.add_argument('names', nargs='*', help='repository names')
    
    args = parser.parse_args()
    action_mapper = {
        "refresh": GitManager.refresh,
        "clone": GitManager.clone,
        "install": GitManager.install
        }
    action = action_mapper[args.action]
    action(*args.names)
    
if __name__ == "__main__":
    main()
