# UI & Arabic (BiDi / RTL) Guidelines — Aero Suite

This document establishes the strict architectural and styling standard for rendering text and handling Bidirectional (Arabic / English) layouts in Aero Suite using **PySide6 / Qt**.

---

## 1. The Core Problem: Qt Scribe & RichText BiDi Bug

When PySide6/Qt renders RichText (`setTextFormat(Qt.RichText)` or strings containing HTML tags like `<div>`, `<span>`, `<p>`, `<br>`):
- Qt's text engine (**Scribe**) handles mixed BiDi poorly when block tags or `dir="rtl"` / `align="right"` attributes are used.
- In mixed Arabic/English text (e.g. an Arabic paragraph containing English words like `Android 8.1`, `Snapdragon`, `Shine Max`), Scribe often **separates the LTR runs and left-aligns them to `x = 0`**, while the Arabic remains on the right.
- This creates huge awkward gaps, breaks inline sentence flow, and causes continuation lines to reset to left-to-right alignment.

---

## 2. The Golden Rule: Plain Text `QLabel` with WordWrap

> [!CRITICAL]
> **NEVER use HTML or `Qt.RichText` for multi-line descriptive text or bullet lists in Arabic.**
> Always use a plain `QLabel` with `setWordWrap(True)`.

### ✅ The Standard Pattern (Follow `RestoreView` Architecture):

```python
# 1. Instantiate as plain QLabel with translatable text
desc_label = QLabel(t("section.description"))

# 2. Enable word wrap
desc_label.setWordWrap(True)

# 3. Style via stylesheet or objectName / class (NOT inline HTML)
desc_label.setStyleSheet("""
    color: #cbd5e1;
    font-size: 13px;
    line-height: 1.6;
    padding: 0;
    margin: 0;
""")

# 4. Add to card layout
card_layout.addWidget(desc_label)
```

### Why this works:
1. `QApplication.setLayoutDirection(Qt.RightToLeft)` is globally set when Arabic is active.
2. Qt's **HarfBuzz** shaper automatically aligns plain text to the right in RTL mode.
3. Natural inline placement of English words, technical terms, and punctuation is preserved without artificial line breaks.
4. Continuation lines wrap cleanly to the right edge.

---

## 3. Anti-Patterns (STRICTLY FORBIDDEN)

| ❌ Anti-Pattern | Why it Fails |
| :--- | :--- |
| `label.setTextFormat(Qt.RichText)` | Triggers Qt Scribe HTML parser, breaking BiDi inline flow. |
| `<div align="right" dir="rtl">...</div>` | Causes LTR runs (English words) to snap to `x=0` on the far left. |
| `<span dir="ltr">term</span>` inside Arabic | Causes baseline shifts and disjointed spacing. |
| Creating a custom widget/row for each bullet point | Adds layout padding overhead and can misalign bullets relative to multi-line wrapped text. |
| Appending English titles at the end of Arabic headers | e.g. `العربيات المدعومة (Supported Cars)` flips parentheses and breaks trailing layout. |

---

## 4. Bullet Lists & Multi-line Descriptions

For sections with lists or multiple points:
1. Put the entire multi-line text into a single key in `locales/ar.json` (and `en.json`), using newline `\n\n` and bullet characters (`• ` or numbered `1. `):
   ```json
   "about.compatibility_desc": "• سيارات دونغ فينغ (Dongfeng) في مصر والشرق الأوسط المزودة بنظام ملاحة وشاشة أندرويد.\n\n• شاشات أندرويد 8.1 (Android 8.1 Oreo) معمارية 32-بت (armeabi-v7a).\n\n• دعم كامل لـ Shine Max وAeolus مع معالجات Snapdragon المخصصة."
   ```
2. Render it with a single plain `QLabel`:
   ```python
   list_label = QLabel(t("about.compatibility_desc"))
   list_label.setWordWrap(True)
   card_layout.addWidget(list_label)
   ```

---

## 5. Translation Guidelines (`locales/ar.json`)

When writing or updating Arabic strings:
1. **Natural Word Order:** Keep English brand names and technical abbreviations inline with Arabic context:
   - ✅ `سيارات دونغ فينغ (Dongfeng) في مصر`
   - ❌ `Dongfeng سيارات في مصر`
2. **Numbers & Architectures:** Prefix numbers with Arabic context to avoid bidirectional flip:
   - ✅ `معمارية 32-بت (armeabi-v7a)`
   - ❌ `32-bit (armeabi-v7a) معمارية`
3. **No Trailing Parentheses in Titles:**
   - ✅ `📸 الشكل والتصميم المرجعي للشاشة المستهدفة`
   - ❌ `📸 الشكل والتصميم المرجعي للشاشة المستهدفة (Visual Reference)`

---

## 6. Verification Protocol

Whenever modifying or adding any UI view:
1. Never assume layout direction works without visual inspection.
2. Run test script or headless screenshot capture for **both** Arabic (`ar`) and English (`en`) locales:
   ```bash
   python -c "from PySide6.QtWidgets import QApplication; ..."
   ```
3. Inspect the resulting screenshot to confirm:
   - Text starts from the right edge in Arabic.
   - Wrapped lines continue from the right edge.
   - English terms appear at their natural reading position inside sentences.
