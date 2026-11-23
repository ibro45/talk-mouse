"""Razer Basilisk V3 X HyperSpeed: onboard buttons (class 0x02, set 0x0C / get 0x8C).

Arguments: <store> <button> <layer> <action: 7 bytes>. Store 1 is saved on the
mouse, store 0 is the live copy. Layer 0 is normal, 1 is Hypershift (trigger held).
"""
import fcntl
import time

from .hid import MouseError, open_first
from .keymap import CONSUMER, KEYS

NAME, VID, PID = "Razer Basilisk V3 X HyperSpeed", 0x1532, 0x00B9
SLOTS = {"left": 0x01, "right": 0x02, "wheel": 0x03, "back": 0x04, "forward": 0x05,
         "wheel_up": 0x09, "wheel_down": 0x0A, "trigger": 0x39, "top": 0x60}
LAYER = {"normal": 0, "hold": 1}
STORES = (1, 0)
OK, BUSY = 0x02, 0x01
HYPERSHIFT = 0x0C


def encode(action):
    if action in KEYS:
        raw = [0x02, 0x01, 0x00, KEYS[action]]
    elif action in CONSUMER:
        raw = [0x0A, 0x01, CONSUMER[action] >> 8, CONSUMER[action] & 0xFF]
    elif action == "DpiCycle":
        raw = [0x06, 0x01, 0x06]
    else:
        raise ValueError(f"Razer cannot store {action!r}")
    return bytes(raw).ljust(7, b"\0")


def report(cls, cmd, size, args):
    r = bytearray(90)
    r[1], r[5], r[6], r[7] = 0x1F, size, cls, cmd
    r[8:8 + len(args)] = bytes(args)
    for b in r[2:88]:
        r[88] ^= b
    return bytes(r)


def _feature(nr, length):
    return (3 << 30) | (length << 16) | (ord("H") << 8) | nr


class Razer:
    def __init__(self):
        self.fd = open_first(VID, PID, NAME, self._probe)

    def _probe(self, fd):
        self.fd = fd
        self.get(1, SLOTS["left"], 0)
        return True

    def _call(self, cls, cmd, size, args):
        fcntl.ioctl(self.fd, _feature(0x06, 91), b"\0" + report(cls, cmd, size, args))
        for _ in range(40):
            time.sleep(0.035)
            buf = bytearray(91)
            fcntl.ioctl(self.fd, _feature(0x07, 91), buf)
            r = buf[1:]
            if r[0] != BUSY and (r[6], r[7]) == (cls, cmd):
                break
        if r[0] != OK or (r[6], r[7]) != (cls, cmd):
            raise MouseError(f"{NAME}: command {cls:#04x}/{cmd:#04x} failed (status {r[0]:#04x})")
        return bytes(r[8:88])

    def get(self, store, slot, layer):
        a = self._call(0x02, 0x8C, 0x0A, [store, slot, layer])
        if a[0] != store or a[1] != slot:
            raise MouseError(f"{NAME}: stale reply for button {slot:#04x}")
        return a[3:10]

    def set(self, store, slot, layer, action):
        self._call(0x02, 0x0C, 0x0A, [store, slot, layer, *action])

    def read(self):
        return {f"{s}/{l}/{b}": self.get(s, SLOTS[b], l).hex()
                for s in STORES for l in (0, 1) for b in SLOTS}

    def wanted(self, keymap):
        out = {}
        for layer, buttons in LAYER.items():
            for button, action in keymap["razer"][layer].items():
                for store in STORES:
                    out[f"{store}/{buttons}/{button}"] = encode(action).hex()
        return out

    def check(self, state):
        if any(bytes.fromhex(state[f"{s}/0/trigger"])[0] != HYPERSHIFT for s in STORES):
            raise MouseError(f"{NAME}: the thumb trigger is not set to Hypershift; set it once in Synapse")

    def write(self, state):
        for key, value in state.items():
            store, layer, button = key.split("/")
            self.set(int(store), SLOTS[button], int(layer), bytes.fromhex(value))
