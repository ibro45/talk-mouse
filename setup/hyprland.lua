-- Omarchy / Hyprland (Lua config). Put your own speech-to-text command here.
o.bind("F20", "Toggle dictation", "voxtype record toggle")

-- Make F13-F24 reach apps as plain function keys. If you already set kb_options,
-- add the option to your existing list instead.
hl.config({ input = { kb_options = "fkeys:basic_13-24" } })
