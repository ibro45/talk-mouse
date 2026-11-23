"""Find a mouse's hidraw nodes."""
import glob
import os


class MouseError(Exception):
    pass


def hidraw_nodes(vid, pid):
    tag = f"{vid:04X}:{pid:04X}"
    return [f"/dev/{os.path.basename(d)}" for d in sorted(glob.glob("/sys/class/hidraw/hidraw*"))
            if tag in os.path.realpath(f"{d}/device").upper()]


def open_first(vid, pid, name, probe):
    """Open the first node for which probe(fd) is true."""
    nodes, denied = hidraw_nodes(vid, pid), False
    for path in nodes:
        try:
            fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        except PermissionError:
            denied = True
            continue
        try:
            if probe(fd):
                return fd
        except (OSError, MouseError):
            pass
        os.close(fd)
    if denied:
        raise MouseError(f"{name}: no permission (see setup/70-talk-mouse.rules)")
    raise MouseError(f"{name}: " + ("not answering; move it to wake it up" if nodes else "not connected"))
