import os
from dataclasses import dataclass, field
from threading import Thread
from typing import Dict, List

import cli
from plib import Path

from . import vpn

no_pull_changes_message = "Already up to date."


def ask_push():
    response = cli.prompt("Commit message", default=False)
    return response


def is_remote(command: str) -> bool:
    return command in ("push", "pull")


def is_reachable(remote: str) -> bool:
    return cli.check_succes(f"ping -c 1 {remote}")


def is_vpn_error(exc: Exception):
    vpn_error_messages = ("Could not resolve host", "status 128")
    error_message = str(exc)
    return any(m in error_message for m in vpn_error_messages)


@dataclass
class Repo:
    path: Path
    pull_output: str = None
    changes: str = None
    status: List[str] = field(default_factory=list)
    committed: List[str] = field(default_factory=list)
    update: bool = False
    vpn_activated: bool = False

    @property
    def title(self) -> str:
        return self.path.name.capitalize()

    @property
    def auto_add(self) -> bool:
        auto_add_skip_file = Path.assets / "autogit" / "skip_auto_add.yaml"
        return self.path.name not in auto_add_skip_file.yaml

    def check_updates(self):
        self.changes = (
            self.get("diff") or self.get("ls-files --others --exclude-standard")
            if self.auto_add
            else ""
        )
        self.status = self.get_status() if self.auto_add else []

        # committed before but the push has failed
        self.committed = not (self.changes or self.status) and [
            line
            for line in self.lines("status --porcelain -b")
            if "ahead" in line and "##" in line
        ]

        self.update = bool(self.changes or self.status or self.committed)

    def process_updates(self):
        self.clear()

        if self.changes:
            self.add()

        if self.status or self.committed:
            if self.status:
                self.show_status()

                pull = Thread(target=self.do_pull, kwargs={"check": False})
                pull.start()
                commit_message = ask_push()

                while commit_message == "show":
                    self.clear()
                    self.show_status(verbose=True)
                    commit_message = ask_push()

                if commit_message and len(commit_message) > 5:
                    if self.status:
                        pull.join()
                        self.get(f'commit -m"{commit_message}"')
                        self.run("push")
                    else:
                        print("cleaned")

            else:
                commit_info = self.committed[0].replace("[", "\[").replace("## ", "")
                if cli.confirm(f"Push ({commit_info}) ?", default=True):
                    self.run("push")

            cli.run("clear")

        else:
            print("cleaned")

    def run_hooks(self):
        pre_commit_file = self.path / ".git" / "hooks" / "pre-commit"
        if pre_commit_file.exists():
            cli.run(pre_commit_file, cwd=self.path)

    @property
    def changed_files(self) -> Dict[str, str]:
        return {
            filenames[-1]: symbol
            for line in self.status
            for symbol, *filenames in (line.split(),)
        }

    def show_status(self, verbose=False):
        status = self.lines("status -v", capture_output_tty=True)

        diff_indices = [i for i, line in enumerate(status) if "diff" in line] + [
            len(status)
        ]
        lines_amount = os.get_terminal_size().lines * 2 - 6

        symbols = {"M": "*", "D": "-", "A": "+", "R": "*", "C": "*"}
        colors = {"M": "blue", "D": "red", "A": "green", "R": "blue", "C": "blue"}

        for start, stop in zip(diff_indices, diff_indices[1:]):
            title = status[start]
            for filename, symbol in self.changed_files.items():
                if filename in title:
                    color = colors.get(symbol, "")
                    line = symbols.get(symbol, "") + f" [bold {color}]{filename}\n"
                    cli.console.print(line, end="")
            diff = [
                part
                for line in status[start:stop]
                for part in line.split("@@")
                if "\x1b[1m" not in line
            ] + [""]

            if lines_amount > len(diff) or verbose:
                lines_amount -= len(diff)
                for d in diff:
                    print(d)

    def clear(self):
        cli.console.clear()
        cli.console.rule(self.title)

    def add(self):
        self.get("add .")
        self.run_hooks()
        self.get("add .")

        self.status = self.get_status()

    def get_status(self):
        return self.lines("status --porcelain")

    def do_pull(self, check=True):
        self.pull_output = self.get("pull", check=check)

    def show_pull(self):
        if no_pull_changes_message not in self.pull_output:
            self.clear()
            print(self.pull_output)
            return True

    def lines(self, command, **kwargs):
        lines = self.get(command, **kwargs).split("\n")
        lines = [l for l in lines if l]
        return lines

    def get(self, command, **kwargs):
        output = self.run(command, **kwargs, capture_output=True)
        if "capture_output_tty" not in kwargs:
            output = output.stdout
        return output.strip()

    def run(self, command, **kwargs):
        try:
            result = cli.run(f"git -C {self.path} {command}", **kwargs)
        except Exception as e:
            if is_vpn_error(e):
                if command == "push":
                    pprint("Activating VPN..")
                    vpn.connect_vpn()
                    self.vpn_activated = True
                    result = cli.run(f"git -C {self.path} {command}", **kwargs)
                elif command == "pull":
                    # ignore not reachable after vpn when pulling
                    result = cli.run(f"echo {no_pull_changes_message}", **kwargs)
                else:
                    raise e
            else:
                raise e

        self.after_command(command)
        return result

    def check_vpn(self, url):
        domain = url.split("@")[1].split("/")[0]
        if not is_reachable(domain):
            vpn.connect_vpn()
            self.vpn_activated = True

    def after_command(self, _):
        if self.vpn_activated:
            vpn.disconnect_vpn()
            self.vpn_activated = False
