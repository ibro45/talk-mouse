import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from talkmouse import cli, g502, keymap, razer, tester
from talkmouse.hid import MouseError


class Fake:
    def __init__(self, state, fail_after=None, drop=()):
        self.state, self.fail_after, self.drop, self.writes = dict(state), fail_after, set(drop), 0

    def read(self):
        return dict(self.state)

    def write(self, todo):
        for k, v in todo.items():
            self.writes += 1
            if self.fail_after is not None and self.writes > self.fail_after:
                self.fail_after = None
                raise MouseError("lost")
            if k in self.drop:
                self.drop.discard(k)
                continue
            self.state[k] = v


class Keymap(unittest.TestCase):
    def check(self, text):
        with tempfile.NamedTemporaryFile("w", suffix=".toml") as f:
            f.write(text); f.flush()
            return keymap.load(f.name)

    def test_shipped_keymap(self):
        km = keymap.load()
        for m in keymap.MICE:
            self.assertEqual(km[m]["hold"]["left"], km["send"])
            self.assertEqual(km[m]["hold"]["right"], km["dictation"])

    def test_rejects_bad_entries(self):
        base = (keymap.ROOT / "keymap.toml").read_text()
        for bad in (base.replace('top = "F15"', 'left = "F15"', 1), base.replace('"F14"', '"F99"', 1),
                    base.replace('top = "F15"', 'nose = "F15"', 1), base.replace('g8 = "F23"', 'g8 = "Layer"')):
            with self.assertRaises(ValueError):
                self.check(bad)

    def test_one_meaning_per_key_on_a_mouse(self):
        km = keymap.load()
        for m in keymap.MICE:
            acts = [a for l in keymap.LAYERS for a in km[m][l].values()]
            self.assertEqual(len(acts), len(set(acts)))


class Encoding(unittest.TestCase):
    def test_razer(self):
        self.assertEqual(razer.encode("F13").hex(), "02010068000000")
        self.assertEqual(razer.encode("VolumeUp").hex(), "0a0100e9000000")
        self.assertEqual(razer.encode("DpiCycle").hex(), "06010600000000")
        r = razer.report(0x02, 0x8C, 0x0A, [1, 4, 0])
        x = 0
        for b in r[2:88]:
            x ^= b
        self.assertEqual((len(r), r[88]), (90, x))

    def test_g502(self):
        self.assertEqual(g502.encode("F13").hex(), "80020068")
        self.assertEqual(g502.encode("DpiCycle").hex(), "9005ffff")
        self.assertEqual(g502.encode("Layer").hex(), "900bffff")
        self.assertEqual(g502.crc(b"123456789").hex(), "29b1")  # CRC-16/CCITT-FALSE check value

    def test_g502_patch_touches_only_listed_buttons(self):
        base = g502.sealed(bytes(range(256)))
        new = g502.patch(base, {"normal": {"back": "F13", "trigger": "Layer"}, "hold": {}})
        diff = {i for i in range(254) if base[i] != new[i]}
        allowed = {*range(44, 48), *range(52, 56), *range(116, 120)}
        self.assertTrue(diff and diff <= allowed)
        self.assertEqual(new[116:120], g502.OFF)
        self.assertEqual(g502.sealed(new), new)


class Writing(unittest.TestCase):
    def test_writes_only_differences(self):
        d = Fake({"a": 1, "b": 2})
        self.assertEqual(cli.write_verified("m", d, d.read(), {"a": 1, "b": 3}), 1)
        self.assertEqual((d.state, d.writes), ({"a": 1, "b": 3}, 1))

    def test_rolls_back_on_error_and_on_bad_readback(self):
        for kw in ({"fail_after": 1}, {"drop": {"b"}}):
            d = Fake({"a": 1, "b": 2}, **kw)
            with self.assertRaisesRegex(MouseError, "previous settings restored"):
                cli.write_verified("m", d, d.read(), {"a": 9, "b": 9})
            self.assertEqual(d.state, {"a": 1, "b": 2})

    def test_backup_round_trip(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, XDG_STATE_HOME=t):
            p = cli.backup("razer", {"x": "00"})
            self.assertEqual(json.loads(p.read_text()), {"mouse": "razer", "state": {"x": "00"}})


class Checklist(unittest.TestCase):
    def test_covers_every_key(self):
        km = keymap.load()
        events = {e for _, e in tester.checklist("g502", km)}
        self.assertTrue({"F13", "F20", "F23", "ENTER", "LEFT"} <= events)
        self.assertFalse({"Layer", "DpiCycle"} & events)


class Drawings(unittest.TestCase):
    def test_up_to_date(self):
        r = subprocess.run([sys.executable, str(keymap.ROOT / "tools/draw.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
