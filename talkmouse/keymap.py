"""Load keymap.toml and check it."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = {"Enter": 0x28, **{f"F{n}": 0x68 + n - 13 for n in range(13, 25)}}  # HID keyboard usages
CONSUMER = {"VolumeUp": 0xE9, "VolumeDown": 0xEA}                           # HID consumer usages
SPECIAL = ("DpiCycle",)  # handled inside the mouse; sends nothing to the computer
MICE = ("razer", "g502")
LAYERS = ("normal", "hold")
LABELS = {
    "left": "Left click", "right": "Right click", "wheel": "Wheel click",
    "wheel_up": "Scroll up", "wheel_down": "Scroll down",
    "back": "Side back", "forward": "Side forward", "top": "Top button",
    "g7": "G7", "g8": "G8", "trigger": "Thumb trigger",
}
G502_LABELS = {"back": "G4 (side back)", "forward": "G5 (side forward)",
               "top": "G9 (behind wheel)", "trigger": "G6 (thumb trigger)"}


def label(mouse, button):
    return (G502_LABELS if mouse == "g502" else {}).get(button, LABELS[button])


def load(path=ROOT / "keymap.toml"):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    for mouse in MICE:
        for layer in LAYERS:
            for button, action in data[mouse][layer].items():
                where = f"{mouse}.{layer}.{button}"
                if button not in LABELS:
                    raise ValueError(f"{where}: unknown button")
                if action == "Layer":
                    if (layer, button) != ("normal", "trigger"):
                        raise ValueError(f"{where}: only the trigger can be the layer button")
                elif action not in KEYS and action not in CONSUMER and action not in SPECIAL:
                    raise ValueError(f"{where}: unknown action {action!r}")
                if layer == "normal" and button in ("left", "right"):
                    raise ValueError(f"{where}: refusing to replace a normal click")
    return data
