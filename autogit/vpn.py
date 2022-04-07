import sys

import cli


def connection_name():
    connection_types = cli.lines("nmcli -g type con show")
    connection_names = cli.lines("nmcli -g name con show")

    for type_, name in zip(connection_types, connection_names):
        if type_ == "vpn":
            return name

    raise Exception("No VPN found")


def connected():
    name = connection_name()
    return name in cli.lines("nmcli -g name con show --active")


def connect_vpn():
    run_action("up")


def disconnect_vpn():
    run_action("down")


def run_action(action):
    name = connection_name()
    try:
        cli.get("nmcli con", action, name)
    except Exception as e:
        ignore_errors = {"up": "already active", "down": "not an active connection"}
        if ignore_errors[action] not in str(e):
            raise e


def toggle():
    action = "down" if connected() else "up"
    run_action(action)


def main():
    if len(sys.argv) < 2:
        action = toggle
    else:
        action = connect_vpn if sys.argv[1] == "connect" else disconnect_vpn
    action()


if __name__ == "__main__":
    main()
