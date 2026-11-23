#!/usr/bin/python3
"""Draw docs/img/*.svg from keymap.toml. --check: fail if the files are out of date."""
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from talkmouse import keymap  # noqa: E402

BG, CARD, EDGE = "#14181f", "#1c222c", "#323b49"
BODY, BUTTON, LINE = "#262e3a", "#303a48", "#566275"
TEXT, DIM = "#e9edf3", "#9aa6b8"
TRIGGER, TALK, SEND, PLAIN = "#ffb454", "#62b5ff", "#74dd9b", "#c3cede"
FONT = "font-family=\"ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,'Noto Sans',sans-serif\""

# One generic mouse seen from above, thumb side on the left.
OUTLINE = "M150 12C226 12 258 66 262 150C266 236 274 318 244 388C220 444 92 444 66 388C40 330 46 244 44 150C46 66 74 12 150 12Z"
SHAPES = {
    "left": "M136 18V196H46Q43 150 46 128C52 64 82 24 136 18Z",
    "right": "M164 18V196H260Q262 150 258 128C250 64 218 24 164 18Z",
    "wheel": "M141 58Q141 49 150 49Q159 49 159 58V118Q159 127 150 127Q141 127 141 118Z",
    "top": "M140 146H160Q163 146 163 149V175Q163 178 160 178H140Q137 178 137 175V149Q137 146 140 146Z",
    "forward": "M44 214L60 210Q64 209 64 213V258Q64 262 60 262L45 264Q42 264 42 261V217Q42 214 44 214Z",
    "back": "M44 272L60 270Q64 270 64 274V318Q64 322 60 322L50 323Q46 323 46 319L42 276Q42 272 44 272Z",
    "trigger": "M40 128Q14 136 14 164V206Q14 214 22 212L38 207Q42 205 42 201V132Q42 128 40 128Z",
    "g7": "M62 100H78Q81 100 81 103V136Q81 139 78 139H61Q58 139 58 136V106Q58 100 62 100Z",
    "g8": "M72 58H82Q86 58 86 62V90Q86 93 83 93H65Q61 93 62 89L67 62Q68 58 72 58Z",
}
ANCHOR = {"left": (104, 52), "right": (232, 128), "wheel": (150, 62), "top": (150, 162), "forward": (53, 236),
          "back": (54, 296), "trigger": (27, 180), "g7": (69, 120), "g8": (75, 76), "wheel_up": (150, 60),
          "wheel_down": (150, 116)}


def text(x, y, s, size=16, fill=TEXT, weight=400, anchor="start", extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{escape(s)}</text>'


def mouse(g502, fills=None):
    fills = fills or {}
    out = [f'<path d="{OUTLINE}" fill="{BODY}" stroke="{LINE}" stroke-width="2.5"/>']
    for name, d in SHAPES.items():
        if name in ("g7", "g8") and not g502:
            continue
        out.append(f'<path d="{d}" fill="{fills.get(name, BUTTON)}" stroke="{LINE}" stroke-width="1.8"/>')
    out.append(f'<path d="M145 66H155M145 78H155M145 90H155M145 102H155" stroke="{LINE}" stroke-width="2"/>')
    return "".join(out)


def svg(w, h, title, desc, body, style=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d" {FONT}>'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>{style}'
            f'<rect width="{w}" height="{h}" rx="18" fill="{BG}"/>{body}</svg>\n')


def colour(action, km):
    return {km["send"]: SEND, km["dictation"]: TALK, "Layer": TRIGGER}.get(action, PLAIN)


def pretty(action, km):
    return {km["send"]: "Enter: send", km["dictation"]: f"{action}: talk / stop", "Layer": "Second layer",
            "VolumeUp": "Volume up", "VolumeDown": "Volume down"}.get(action, action)


def keymap_svg(km, name):
    m, g502 = km[name], name == "g502"
    W, H, ox, oy = 960, 620, 330, 112
    normal, hold = m["normal"], m["hold"]
    wheel_hold = ["Click " + pretty(hold["wheel"], km)] if "wheel" in hold else []
    if "wheel_up" in hold and "wheel_down" in hold:
        wheel_hold.append("scroll volume" if hold["wheel_up"] == "VolumeUp" else f"{hold['wheel_up']} / {hold['wheel_down']} on scroll")
    # Listed top to bottom in the order they sit on the mouse, so pointer lines never cross.
    left = ["left", "g8", "g7", "trigger", "forward", "back"] if g502 else ["left", "trigger", "forward", "back"]
    right = ["wheel", "right", "top"]
    rows_l = [124 + 80 * i for i in range(6)] if g502 else [150, 262, 358, 454]
    rows_r = [150, 270, 390]
    plain = {"left": "Left click", "right": "Right click", "wheel": "Click and scroll as usual"}
    heads = {"left": "Left button", "right": "Right button", "wheel": "Wheel"}
    b = [text(40, 52, m["name"], 26, weight=650), text(40, 80, "What each button sends", 16, DIM)]
    b.append(f'<circle cx="650" cy="46" r="6" fill="{PLAIN}"/>' + text(664, 51, "normal", 15, DIM))
    b.append(f'<circle cx="746" cy="46" r="6" fill="{TRIGGER}"/>' + text(760, 51, "while the trigger is held", 15, DIM))
    b.append(f'<g transform="translate({ox} {oy})">{mouse(g502, {"trigger": TRIGGER, "left": "#2c4a42", "right": "#2b4460"})}</g>')
    for x, edge, names, rows in ((40, 236, left, rows_l), (700, 688, right, rows_r)):
        for n, y in zip(names, rows):
            ax, ay = ANCHOR[n][0] + ox, ANCHOR[n][1] + oy
            b.append(f'<path d="M{edge} {y + 4}L{ax} {ay}" stroke="{LINE}" stroke-width="1.5"/><circle cx="{ax}" cy="{ay}" r="4" fill="{TEXT}"/>')
            b.append(text(x, y, heads.get(n) or keymap.label(name, n), 16, weight=650))
            if n == "trigger":
                b.append(text(x, y + 21, "Hold for the second layer", 15, TRIGGER))
                continue
            b.append(text(x, y + 21, pretty(normal[n], km) if n in normal else plain[n], 15, PLAIN))
            held = ", ".join(wheel_hold) if n == "wheel" else pretty(hold[n], km) if n in hold else ""
            if held:
                b.append(f'<circle cx="{x + 5}" cy="{y + 36}" r="4.5" fill="{TRIGGER}"/>' + text(x + 16, y + 41, held, 15, colour(hold.get(n), km), 600))
    b.append(text(W / 2, H - 16, "Generic mouse seen from above, thumb side on the left. Not to scale.", 13, DIM, anchor="middle"))
    desc = "; ".join(f"{keymap.label(name, n)}: " + ", ".join(
        ([f"normal {normal[n]}"] if n in normal else []) + ([f"trigger held {hold[n]}"] if n in hold else []))
        for n in keymap.LABELS if n in normal or n in hold)
    return svg(W, H, f"{m['name']} button map", desc, "".join(b))


# ---- the animation ---------------------------------------------------------
T = 14.0
SHOW = {  # name: [(on, off), ...] in seconds
    "trigger": [(0.8, 3.0), (7.4, 10.6)], "right": [(1.7, 2.2), (8.0, 8.5)], "left": [(9.6, 10.1)],
    "rec": [(2.1, 8.15)], "ready": [(0, 1.85), (8.45, 13.6)], "draft": [(2.0, 9.8)], "sent": [(9.8, 13.6)], "reply": [(10.7, 13.6)],
    "s1": [(0.8, 1.7)], "s2": [(1.7, 2.8)], "s3": [(2.8, 7.4)], "s4": [(7.4, 9.0)], "s5": [(9.0, 10.8)],
}
WORDS = "Find why the login test fails and fix it".split()
for i in range(len(WORDS)):
    SHOW[f"w{i}"] = [(3.2 + i * 0.42, 13.6)]
STILL = {"trigger", "ready", "draft", "right", "left", "s1", "s2", "s3", "s4", "s5"} | {f"w{i}" for i in range(len(WORDS))}


def css():
    out = [".a{opacity:0}" + "".join(f".{n}{{opacity:1}}" for n in sorted(STILL)),
           "@media (prefers-reduced-motion:no-preference){"]
    fade = 0.12
    for n, spans in SHOW.items():
        pts = {0.0: 0.0, T: 0.0}
        for on, off in spans:
            pts.update({max(on - fade, 0): 1.0 if on == 0 else 0.0, on: 1.0, off: 1.0, min(off + fade, T): 0.0})
            if on == 0:
                pts[0.0] = 1.0
        frames = "".join(f"{t / T * 100:.2f}%{{opacity:{v:g}}}" for t, v in sorted(pts.items()))
        out.append(f"@keyframes k-{n}{{{frames}}}.{n}{{animation:k-{n} {T:g}s linear infinite}}")
    return "<style>" + "".join(out) + "}</style>"


def hero(km):
    W, H = 960, 560
    b = [text(40, 54, "Speak, send, repeat. No keyboard needed.", 27, weight=650)]
    lit = lambda cls, n, c: f'<path class="a {cls}" d="{SHAPES[n]}" fill="{c}" stroke="{c}" stroke-width="2"/>'
    b.append(f'<g transform="translate(108 84) scale(.76)">{mouse(False)}'
             + lit("trigger", "trigger", TRIGGER) + lit("right", "right", TALK) + lit("left", "left", SEND) + "</g>")
    b.append(text(72, 200, "trigger", 15, TRIGGER, 600, "middle", 'class="a trigger"'))
    b.append(text(262, 172, "talk", 17, BG, 700, "middle", 'class="a right"') + text(182, 172, "send", 17, BG, 700, "middle", 'class="a left"'))
    x, y, w, h = 400, 92, 520, 306
    b.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{CARD}" stroke="{EDGE}" stroke-width="1.5"/>')
    b.append(text(x + 24, y + 36, "Agent", 17, DIM, 600))
    b.append(f'<g class="a rec"><circle cx="{x + w - 118}" cy="{y + 30}" r="6" fill="{TALK}"/>' + text(x + w - 104, y + 36, "Listening", 16, TALK, 600) + "</g>")
    b.append(text(x + w - 24, y + 36, "Mic off", 16, DIM, 400, "end", 'class="a ready"'))
    half = " ".join(WORDS)
    b.append(f'<g class="a sent"><rect x="{x + 96}" y="{y + 60}" width="{w - 120}" height="50" rx="12" fill="#25443a"/>' + text(x + 114, y + 91, half, 17) + "</g>")
    b.append(f'<g class="a reply">' + text(x + 24, y + 152, "On it. Running the login test first.", 17, TEXT) + "</g>")
    b.append(f'<rect x="{x + 20}" y="{y + h - 94}" width="{w - 40}" height="74" rx="12" fill="{BG}" stroke="{EDGE}" stroke-width="1.5"/>')
    spans = "".join(f'<tspan class="a w{i}">{escape(wd)} </tspan>' for i, wd in enumerate(WORDS))
    b.append(f'<g class="a draft"><text x="{x + 40}" y="{y + h - 50}" font-size="18" fill="{TEXT}">{spans}</text></g>')
    steps = [("s1", "1", "Hold trigger", "thumb", TRIGGER), ("s2", "2", "Right click", "start talking", TALK), ("s3", "3", "Speak", "words appear", TALK),
             ("s4", "4", "Trigger + right", "stop talking", TALK), ("s5", "5", "Trigger + left", "Enter: send", SEND)]
    sw, gap, sx, sy = 168, 10, 40, 440
    for i, (cls, n, head, sub, c) in enumerate(steps):
        px = sx + i * (sw + gap)
        b.append(f'<rect x="{px}" y="{sy}" width="{sw}" height="84" rx="12" fill="{CARD}" stroke="{EDGE}" stroke-width="1.5"/>')
        b.append(f'<rect class="a {cls}" x="{px}" y="{sy}" width="{sw}" height="84" rx="12" fill="none" stroke="{c}" stroke-width="2.5"/>')
        b.append(text(px + 16, sy + 36, f"{n}  {head}", 17, weight=650) + text(px + 16, sy + 62, sub, 15, c))
    return svg(W, H, "Speak, send, repeat: the five steps",
               "Hold the thumb trigger and right click to start dictation, speak, hold the trigger and right click to stop, then hold the trigger and left click to press Enter.",
               "".join(b), css())


def main():
    km = keymap.load()
    files = {"loop.svg": hero(km), "razer.svg": keymap_svg(km, "razer"), "g502.svg": keymap_svg(km, "g502")}
    out, stale = ROOT / "docs/img", []
    for name, data in files.items():
        p = out / name
        if "--check" in sys.argv:
            if not p.exists() or p.read_text() != data:
                stale.append(name)
        else:
            out.mkdir(parents=True, exist_ok=True)
            p.write_text(data)
    if stale:
        sys.exit("out of date: " + ", ".join(stale) + " (run tools/draw.py)")


if __name__ == "__main__":
    main()
