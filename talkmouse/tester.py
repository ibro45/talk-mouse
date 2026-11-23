"""Live checklist. Only watches; the mouse keeps working normally."""
import curses
import selectors
import signal
import subprocess
import sys
import time

from . import g502, keymap, razer

IDS = {"razer": (razer.VID, razer.PID), "g502": (g502.VID, g502.PID)}


def checklist(mouse, km):
    """[(what to press, event name)]; evdev names without their prefix."""
    special = {"VolumeUp": "VOLUMEUP", "VolumeDown": "VOLUMEDOWN", "Enter": "ENTER"}
    rows = [("Left click", "LEFT"), ("Right click", "RIGHT"), ("Wheel click", "MIDDLE")]
    for layer, prefix in (("normal", ""), ("hold", "Trigger + ")):
        for button, action in km[mouse][layer].items():
            if action != "Layer" and action not in keymap.SPECIAL:
                rows.append((prefix + keymap.label(mouse, button), special.get(action, action)))
    return rows


def systemctl(*args):
    return subprocess.run(["systemctl", "--user", "--quiet", *args]).returncode == 0


def run(mouse, km, pause=None):
    try:
        import evdev
    except ImportError:
        sys.exit("talk-mouse: the tester needs python-evdev")
    if not sys.stdin.isatty():
        sys.exit("talk-mouse: run the tester in a terminal")
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: sys.exit(0))
    paused = bool(pause) and systemctl("is-active", pause)
    try:
        if paused:
            systemctl("stop", pause)
            time.sleep(0.5)
        devices = [d for d in map(evdev.InputDevice, evdev.list_devices())
                   if (d.info.vendor, d.info.product) == IDS[mouse]]
        if not devices:
            sys.exit("talk-mouse: mouse not found, or no permission to read it")
        for d in devices:
            try:
                d.grab()
                d.ungrab()
            except OSError:
                sys.exit(f"talk-mouse: another program has taken over {d.name}; stop it or use --pause UNIT")
        curses.wrapper(_screen, km[mouse]["name"], checklist(mouse, km), devices, evdev.ecodes, km["dictation"])
    except KeyboardInterrupt:
        pass
    finally:
        if paused:
            systemctl("start", pause)


def _screen(scr, title, rows, devices, E, dictation):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    scr.timeout(0)
    sel = selectors.DefaultSelector()
    for d in devices:
        sel.register(d, selectors.EVENT_READ)
    seen, last = set(), ""
    while True:
        for key, _ in sel.select(timeout=0.1):
            try:
                events = list(key.fileobj.read())
            except OSError:
                sys.exit("talk-mouse: the mouse was disconnected")
            for ev in events:
                if ev.type == E.EV_KEY and ev.value == 1:
                    names = E.bytype[E.EV_KEY].get(ev.code, str(ev.code))
                    names = names if isinstance(names, (list, tuple)) else [names]
                    short = [n.split("_", 1)[-1] for n in names]
                    seen.update(short)
                    last = short[0]
        c = scr.getch()
        if c in (ord("q"), ord("Q")):
            return
        if c in (ord("r"), ord("R")):
            seen.clear()
        scr.erase()
        h, w = scr.getmaxyx()

        def put(y, text, attr=0):
            if 0 <= y < h and w > 1:
                scr.addnstr(y, 0, text, w - 1, attr)
        put(0, f"{title} - button test", curses.A_BOLD)
        put(1, f"{sum(e in seen for _, e in rows)}/{len(rows)} seen   last: {last}   r reset   q quit")
        for i, (what, event) in enumerate(rows):
            ok = event in seen
            put(3 + i, f" [{'x' if ok else ' '}] {what:30} {event}", curses.color_pair(1) if ok else 0)
        put(4 + len(rows), f"{dictation} may start dictation and Enter reaches this window.", curses.A_DIM)
        scr.refresh()
