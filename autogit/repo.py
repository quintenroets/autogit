import cli
import os
import subprocess

from threading import Thread

symbols = {"M": "*", "D": "-", "A": "+", "R": "*", "C": "*"}
colors = {"M": "blue", "D": "red", "A": "green", "R": "blue", "C": "blue"}


def ask_push():
    response = cli.prompt("Commit message", default=False)
    return response


class Repo:
    def __init__(self, path):
        self.path = path
        self.changed_files = {}
        self.pull = None

    @property
    def title(self):
        return self.path.name.capitalize()

    def check_updates(self):
        self.changes = self.get("diff") or self.get(
            "ls-files --others --exclude-standard"
        )
        self.status = self.get_status()

        # commited before but the push has failed
        self.commited = not (self.changes or self.status) and any(
            [
                "ahead" in line and "##" in line
                for line in self.lines("status --porcelain -b")
            ]
        )

        self.update = self.changes or self.status or self.commited

    def process_updates(self):
        self.clear()

        if self.changes:
            self.add()

        if self.status:
            self.run_hooks()

        if self.status or self.commited:
            if self.status:
                self.show_status()

                pull = Thread(target=self.do_pull, kwargs={"check": False})
                pull.start()
                commit_message = ask_push()

                while commit_message == "show":
                    self.show_verbose_status(force=True)
                    commit_message = ask_push()

                if commit_message and len(commit_message) > 5:
                    pull.join()
                    commit = self.get(f'commit -m"{commit_message}"')
                    self.run("push")
            else:
                if cli.confirm("Retry push?", default=True):
                    self.run("push")

            cli.run("clear")

    def run_hooks(self):
        if (self.path / ".pre-commit-config.yaml").exists():
            autochanges = (
                subprocess.run(
                    ("pre-commit", "run"), cwd=self.path, capture_output=True
                ).returncode
                != 0
            )
        if autochanges:
            self.add()

    def show_status(self):
        filenames = {}
        for line in self.status:
            symbol, filename = line.split()
            self.changed_files[filename] = symbol

        self.show_verbose_status(force=False)

    def show_verbose_status(self, force=False):
        status = self.lines("status -v", capture_output_tty=True)

        diff_indices = [i for i, line in enumerate(status) if "diff" in line] + [
            len(status)
        ]
        lines_amount = os.get_terminal_size().lines - 6

        for start, stop in zip(diff_indices, diff_indices[1:]):
            title = status[start]
            for filename, symbol in self.changed_files.items():
                if filename in title:
                    color = colors.get(symbol, "")
                    line = (
                        symbols.get(symbol, "") + f" [bold {color}]" + filename + "\n"
                    )
                    cli.console.print(line, end="")
            diff = [
                part
                for l in status[start:stop]
                for part in l.split("@@")
                if "\x1b[1m" not in l
            ] + [""]

            if lines_amount > len(diff) or force:
                lines_amount -= len(diff)
                for d in diff:
                    print(d)

    def clear(self):
        cli.console.clear()
        cli.console.rule(self.title)

    def add(self):
        self.get("add .")
        self.status = self.get_status()

    def get_status(self):
        return self.lines("status --porcelain")

    def do_pull(self, check=True):
        self.pull = self.get("pull", check=check)

    def show_pull(self):
        if "Already up to date." not in self.pull:
            cli.console.rule(git.title)
            print(pull)
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
        self.check(command)
        return cli.run(f"git -C {self.path} {command}", **kwargs)

    def check(self, command):
        if command in ["pull", "push"]:
            url = self.get("config remote.origin.url")
            if "@" not in url:
                url = url.replace("https://", f'https://{os.environ["gittoken"]}@')
                self.run(f"config remote.origin.url {url}")
