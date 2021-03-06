import argparse


def install(*args):
    from .installer import Installer  # noqa: autoimport

    Installer.install(*args)


def clone(*args):
    from .installer import Installer  # noqa: autoimport

    Installer.clone(*args)


def refresh(do_pull=False):
    from .repomanager import RepoManager  # noqa: autoimport

    RepoManager.refresh(do_pull=do_pull)


def run_hooks():
    from .repomanager import RepoManager  # noqa: autoimport

    RepoManager.run_hooks()


def main():
    parser = argparse.ArgumentParser(description="Automate common git workflows")
    parser.add_argument("action", nargs="?", help="The action to do", default="refresh")
    parser.add_argument("names", nargs="*", help="repository names")

    args = parser.parse_args()
    action_mapper = {
        "refresh": refresh,
        "clone": clone,
        "install": install,
        "pull": lambda: refresh(do_pull=True),
        "hooks": run_hooks,
    }

    if args.action not in action_mapper:
        raise Exception(f"{args.action} not defined")
    action = action_mapper[args.action]
    action(*args.names)


if __name__ == "__main__":
    main()
