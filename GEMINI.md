# Antigravity & Gemini Project Rules — Aero Suite

Please refer to and strictly enforce all guidelines specified in:
[AGENTS.md](file:///d:/Work/Projects/Aero/Aero_Suite/AGENTS.md)

### Key Directives:
- **Never inline raw bash scripts.** Always use `src/payloads/bash_builder.py`.
- **Reference manual:** Read `docs/BASH_BUILDER_REFERENCE.md` before writing any payload logic.
- **Maintain SOLID & SRP:** Every new shell operation must be added as an atomic generator in `bash_builder.py` before use.
- **Compile check:** Ensure all files pass `compileall`.
- **UI & Arabic (BiDi / RTL):** Read `docs/UI_RTL_GUIDELINES.md`. Never use HTML or `Qt.RichText` for multi-line Arabic text (causes Qt Scribe to push English words to the far left). Always use plain `QLabel(t("key"))` with `setWordWrap(True)`.
- **Visual Verification:** Always take and inspect a screenshot of rendered Arabic text before marking any UI task complete.

