"""talk-mouse show | apply | restore | test"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import g502, keymap, razer
from .hid import MouseError

DRIVERS = {"razer": razer.Razer, "g502": g502.G502}


def changes(current, wanted):
    return {k: v for k, v in wanted.items() if current.get(k) != v}


def backup(mouse, state):
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "talk-mouse"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{mouse}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    with open(path, "x") as f:
        json.dump({"mouse": mouse, "state": state}, f, indent=1)
    return path


def write_verified(mouse, dev, before, wanted):
    """Write only what differs. On any failure, put the old settings back."""
    todo = changes(before, wanted)
    try:
        dev.write(todo)
        left = changes(dev.read(), wanted)
        if left:
            raise MouseError(f"{mouse}: {len(left)} settings did not read back correctly")
    except (OSError, MouseError) as e:
        print(f"{e}\nPutting the previous settings back...", file=sys.stderr)
        old = {k: before[k] for k in todo}
        dev.write(old)
        if changes(dev.read(), old):
            raise MouseError(f"{mouse}: could not restore; use 'talk-mouse restore' with the backup") from e
        raise MouseError(f"{mouse}: previous settings restored") from e
    return len(todo)


def cmd_show(mouse, _args, km):
    dev = DRIVERS[mouse]()
    todo = changes(dev.read(), dev.wanted(km))
    print(f"{km[mouse]['name']}: " + ("differs from keymap.toml" if todo else "matches keymap.toml"))
    for layer, title in (("normal", "normal"), ("hold", "trigger held")):
        for button, action in km[mouse][layer].items():
            print(f"  {title:13} {keymap.label(mouse, button):20} {action}")


def cmd_apply(mouse, args, km):
    dev = DRIVERS[mouse]()
    before, wanted = dev.read(), dev.wanted(km)
    dev.check(before)
    if not changes(before, wanted):
        print(f"{km[mouse]['name']}: already up to date")
    elif args.dry_run:
        print(f"{km[mouse]['name']}: would change {', '.join(changes(before, wanted))}")
    else:
        print(f"backup: {backup(mouse, before)}")
        write_verified(mouse, dev, before, wanted)
        print(f"{km[mouse]['name']}: written and verified")


def cmd_restore(args):
    saved = json.loads(Path(args.file).read_text())
    mouse = saved["mouse"]
    dev = DRIVERS[mouse]()
    before = dev.read()
    if not changes(before, saved["state"]):
        print(f"{mouse}: already matches that backup")
        return
    print(f"backup: {backup(mouse, before)}")
    write_verified(mouse, dev, before, saved["state"])
    print(f"{mouse}: restored and verified")


def main(argv=None):
    p = argparse.ArgumentParser(prog="talk-mouse", description="Mouse buttons for talking to agents.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, text in (("show", "compare the mouse with keymap.toml (read-only)"),
                       ("apply", "save keymap.toml on the mouse"), ("test", "live button checklist")):
        s = sub.add_parser(name, help=text)
        s.add_argument("mouse", choices=DRIVERS)
        if name == "apply":
            s.add_argument("-n", "--dry-run", action="store_true")
        if name == "test":
            s.add_argument("--pause", metavar="UNIT", help="stop this systemd user service while testing")
    s = sub.add_parser("restore", help="put a backup back on the mouse")
    s.add_argument("file")
    args = p.parse_args(argv)
    try:
        if args.cmd == "restore":
            cmd_restore(args)
        elif args.cmd == "test":
            from . import tester
            tester.run(args.mouse, keymap.load(), args.pause)
        else:
            {"show": cmd_show, "apply": cmd_apply}[args.cmd](args.mouse, args, keymap.load())
    except (MouseError, OSError, ValueError, KeyError) as e:
        sys.exit(f"talk-mouse: {e}")
