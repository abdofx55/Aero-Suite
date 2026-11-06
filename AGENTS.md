# AI Agent Guidelines & Architecture Rules — Aero Suite

## 1. Project Overview & Target Hardware
Aero Suite is an automotive engineering toolkit designed for the **Dongfeng Aeolus** infotainment system (Android 8.1 Oreo, API 27, Snapdragon SoC). Modifications are deployed offline via USB flash drives (`/update/custom_rep.sh`).

---

## 2. STRICT INVARIANT: Payload Shell Script Generation (bash_builder)

> [!CRITICAL]
> **DO NOT WRITE RAW INLINE BASH STRINGS IN ANY PAYLOAD MODULE.**
> All shell commands, lifecycle operations, app installations, uninstalls, data wipes, and recovery routines MUST use the modular generator functions defined in:
> `src/payloads/bash_builder.py`

### Mandatory Rules for AI Agents:
1. **Consult Documentation First:**
   Before creating or modifying any payload in `src/payloads/`, you **MUST** read:
   - [`docs/BASH_BUILDER_REFERENCE.md`](file:///d:/Work/Projects/Aero/Aero_Suite/docs/BASH_BUILDER_REFERENCE.md)
   This reference lists all available building block functions, their parameters, and automotive edge cases.

2. **Re-use Existing Functions (Single Responsibility Principle):**
   - For uninstalling user apps: use `gen_uninstall_user_app(pkg)` (clears PM state and removes `/data/app` APKs).
   - For uninstalling system apps: use `gen_uninstall_system_app(pkg)` (dynamic `pm path` query, removes system dir, clears framework cache).
   - For dual-sweep uninstallation: use `gen_uninstall_app(pkg)`.
   - For data wiping: use granular functions (`gen_wipe_app_data`, `gen_wipe_account_databases`, `gen_wipe_bluetooth_data`, etc.).
   - For app launching: use `gen_launch_app(pkg)` (4-tier automotive fallback engine).
   - For partitions: use `gen_mount_rw()` and `gen_mount_ro()`.

3. **Adding New Shell Logic:**
   - If a shell operation does NOT yet exist in `bash_builder.py`, you **MUST NOT** inline it into the feature module.
   - Instead, declare a new atomic, single-responsibility generator function inside `src/payloads/bash_builder.py`, document it in `docs/BASH_BUILDER_REFERENCE.md`, and then import and invoke it.

4. **Modifying & Enhancing Existing Functions (Fix Protocol):**
   - You are **explicitly permitted and encouraged** to edit, fix, or optimize functions inside `bash_builder.py` whenever a bug, edge case, or automotive incompatibility is discovered.
   - **Fix at the Source:** Never work around a broken `bash_builder` function by writing custom bash in the calling feature module. Always fix the function directly inside `bash_builder.py` so the fix automatically benefits all features.
   - **Maintain Backward Compatibility:** Keep existing parameters intact (or add optional parameters with safe defaults) so existing callers do not break.
   - **Keep Documentation Synced:** When changing a function's behavior or parameters, update its docstring and its section in `docs/BASH_BUILDER_REFERENCE.md`.

5. **Testing & Verification:**
   - Always run `python -c "import compileall; compileall.compile_dir('src', force=True)"` after any payload edits.
   - Run verification test suites to verify `custom_rep.sh` generation without syntax errors.

---

## 3. Coding Style & Safety Standards
- **Automotive Safety:** Never execute synchronous unbounded commands without timeouts.
- **Log Everything:** Every generated shell line must append stdout and stderr to `${LOG_FILE}` (`>> "${log_var}" 2>&1`).
- **SELinux & Database Integrity:** Purge SQLite WAL/SHM locks (`*-wal`, `*-shm`) before touching `/data/data/`, and always invoke `restorecon -R` when writing private data.
- **Preserve Existing Documentation:** Never strip existing comments or docstrings from existing modules.

---

## 4. STRICT INVARIANT: PySide6 UI & Arabic (BiDi / RTL) Guidelines

> [!CRITICAL]
> **DO NOT USE HTML TAGS OR `Qt.RichText` FOR MULTI-LINE ARABIC DESCRIPTIONS.**
> Qt's Scribe engine has a known bug that misaligns mixed Arabic/English text (pushes English words to `x = 0` on the far left).
> All UI views MUST follow the standard documented in:
> [`docs/UI_RTL_GUIDELINES.md`](file:///d:/Work/Projects/Aero/Aero_Suite/docs/UI_RTL_GUIDELINES.md)

### Rules for UI Text & Layout:
1. **Plain `QLabel` Only:** Always use plain `QLabel(t("key"))` with `setWordWrap(True)`. Do NOT use `setTextFormat(Qt.RichText)` or inject `<div>`/`<span>`/`<p>` tags with `dir="rtl"` into translations.
2. **Standard Architecture:** Follow the clean pattern established in `RestoreView` and `AboutView`: a single `QLabel` inside a styled `QFrame[class="card"]`.
3. **Bullet Lists:** Put multi-line points separated by `\n\n• ` into a single locale string, rendered via one wrapping `QLabel`. Do not create complex dynamic widget rows unless absolutely necessary.
4. **Locale Translations (`ar.json`):** Keep technical English terms inline with Arabic context, avoid trailing English parenthetical headers, and prefix numbers with Arabic words (e.g., `معمارية 32-بت`).
5. **Visual Verification:** Always take a screenshot and inspect the rendered Arabic text before concluding any UI task.

