"""Logitech G502 HERO: onboard profile (HID++ 2.0 feature 0x8100), including the
G-Shift layer, which libratbag's command-line tool does not edit."""
import os
import select
import time

from .hid import MouseError, open_first
from .keymap import CONSUMER, KEYS

NAME, VID, PID = "Logitech G502 HERO", 0x046D, 0xC08B
SLOTS = {"left": 0, "right": 1, "wheel": 2, "back": 3, "forward": 4,
         "trigger": 5, "g7": 6, "g8": 7, "top": 8}
OFFSET = {"normal": 32, "hold": 96}
SIZE, SW_ID = 256, 0x0A
OFF = b"\xff" * 4


def encode(action):
    if action in KEYS:
        return bytes([0x80, 0x02, 0x00, KEYS[action]])
    if action in CONSUMER:
        return bytes([0x80, 0x03]) + CONSUMER[action].to_bytes(2, "big")
    if action == "DpiCycle":
        return bytes([0x90, 0x05, 0xFF, 0xFF])
    if action == "Layer":
        return bytes([0x90, 0x0B, 0xFF, 0xFF])
    raise ValueError(f"G502 cannot store {action!r}")


def crc(data):
    c = 0xFFFF
    for x in data:
        c ^= x << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c.to_bytes(2, "big")


def sealed(data):
    return bytes(data[:-2]) + crc(data[:-2])


def patch(profile, buttons):
    """Return the profile with {layer: {button: action}} applied."""
    p = bytearray(profile)
    for layer, entries in buttons.items():
        for button, action in entries.items():
            at = OFFSET[layer] + 4 * SLOTS[button]
            p[at:at + 4] = encode(action)
            if action == "Layer":  # the layer button does nothing inside its own layer
                at = OFFSET["hold"] + 4 * SLOTS[button]
                p[at:at + 4] = OFF
    return sealed(p)


class G502:
    def __init__(self):
        self.feature = None
        self.fd = open_first(VID, PID, NAME, self._probe)
        info = self._call(self.feature, 0)
        if (info[7] << 8 | info[8]) != SIZE or info[1] != 2 or (info[9] & 3) != 2:
            raise MouseError(f"{NAME}: unexpected profile format; not touching it")
        self.sector = int.from_bytes(self._call(self.feature, 4)[:2], "big")
        if not 1 <= self.sector <= info[3] or self._call(self.feature, 2)[0] != 1:
            raise MouseError(f"{NAME}: not running one of its own saved profiles")

    def _probe(self, fd):
        self.fd = fd
        self.feature = self._call(0, 0, bytes([0x81, 0x00]))[0]
        return bool(self.feature)

    def _call(self, index, fn, args=b"", timeout=2.0):
        while select.select([self.fd], [], [], 0)[0]:
            os.read(self.fd, 64)
        os.write(self.fd, (bytes([0x11, 0xFF, index, fn << 4 | SW_ID]) + bytes(args)).ljust(20, b"\0"))
        end = time.monotonic() + timeout
        while (left := end - time.monotonic()) > 0 and select.select([self.fd], [], [], left)[0]:
            r = os.read(self.fd, 64)
            if len(r) < 7 or r[0] not in (0x10, 0x11) or r[1] != 0xFF:
                continue
            if r[2] in (0x8F, 0xFF) and r[3] == index:
                raise MouseError(f"{NAME}: HID++ error {r[5]}")
            if r[2] == index and r[3] == fn << 4 | SW_ID:
                return r[4:]
        raise MouseError(f"{NAME}: no reply")

    def _read_sector(self):
        out = b""
        for at in range(0, SIZE, 16):
            out += self._call(self.feature, 5, self.sector.to_bytes(2, "big") + at.to_bytes(2, "big"))[:16]
        if sealed(out) != out:
            raise MouseError(f"{NAME}: profile checksum is wrong; not touching it")
        return out

    def read(self):
        return {"sector": self.sector, "profile": self._read_sector().hex()}

    def wanted(self, keymap):
        m = keymap["g502"]
        new = patch(self._read_sector(), {"normal": m["normal"], "hold": m["hold"]})
        return {"sector": self.sector, "profile": new.hex()}

    def check(self, state):
        pass

    def write(self, state):
        if "profile" not in state:
            return
        data = bytes.fromhex(state["profile"])
        if state.get("sector", self.sector) != self.sector:
            raise MouseError(f"{NAME}: that backup belongs to another profile slot")
        if len(data) != SIZE or sealed(data) != data:
            raise MouseError(f"{NAME}: refusing to write a damaged profile")
        self._call(self.feature, 6, self.sector.to_bytes(2, "big") + b"\0\0" + SIZE.to_bytes(2, "big"))
        for at in range(0, SIZE, 16):
            self._call(self.feature, 7, data[at:at + 16])
        self._call(self.feature, 8, timeout=3)
        time.sleep(0.3)
        self._call(self.feature, 3, self.sector.to_bytes(2, "big"))  # reload
        time.sleep(0.3)
