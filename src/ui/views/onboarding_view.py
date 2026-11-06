"""
onboarding_view.py — Immersive Full-Canvas Cyber-Luxury Onboarding Screen for Aero Suite.
Provides a modern first-run experience (inspired by Antigravity IDE & Cursor),
allowing the user to set their preferred language before entering the studio.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
import theme
from core.i18n import SUPPORTED_LANGUAGES, get_i18n, set_onboarding_completed
from core.constants import DEVELOPER_NAME


class LanguageCard(QFrame):
    """Interactive luxury card representing a selectable language option."""
    clicked = Signal(str)

    def __init__(self, lang_code: str, meta: dict, parent=None):
        super().__init__(parent)
        self.lang_code = lang_code
        self.meta = meta
        self.is_selected = False

        self.setFixedHeight(68)
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()
        self.update_visual()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Flag
        flag_lbl = QLabel(self.meta.get("flag", "🌐"))
        flag_lbl.setStyleSheet("font-size: 26px; background: transparent; border: none;")
        layout.addWidget(flag_lbl)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setAlignment(Qt.AlignVCenter)

        self.lbl_native = QLabel(self.meta.get("native", self.lang_code))
        self.lbl_native.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {theme.TEXT_PRIMARY}; background: transparent; border: none;")
        text_col.addWidget(self.lbl_native)

        subtitles = {
            "ar": "اللغة الافتراضية • مصر والشرق الأوسط",
            "en": "Default International • English",
            "es": "Español • América Latina y España",
            "pt": "Português • Brasil e América do Sul",
            "ru": "Русский язык • СНГ и Россия",
            "zh": "简体中文 • 东风奕炫车主",
            "vi": "Tiếng Việt • Thị trường Việt Nam"
        }
        self.lbl_sub = QLabel(subtitles.get(self.lang_code, self.meta.get("name", "")))
        self.lbl_sub.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; background: transparent; border: none;")
        text_col.addWidget(self.lbl_sub)

        layout.addLayout(text_col, stretch=1)

        # Selection indicator badge
        self.chk_badge = QLabel("✓")
        self.chk_badge.setFixedSize(26, 26)
        self.chk_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.chk_badge)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_visual()

    def update_visual(self):
        if self.is_selected:
            self.setStyleSheet(f"""
                LanguageCard {{
                    background-color: {theme.CYAN_ALPHA_15};
                    border: 2px solid {theme.CYAN_PRIMARY};
                    border-radius: 12px;
                }}
            """)
            self.lbl_native.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; background: transparent; border: none;")
            self.chk_badge.setStyleSheet(f"""
                background-color: {theme.CYAN_PRIMARY};
                color: #000000;
                font-weight: bold;
                font-size: 13px;
                border-radius: 13px;
                border: none;
            """)
            self.chk_badge.setVisible(True)
        else:
            self.setStyleSheet(f"""
                LanguageCard {{
                    background-color: {theme.SURFACE_2};
                    border: 1px solid {theme.BORDER_SLATE};
                    border-radius: 12px;
                }}
                LanguageCard:hover {{
                    background-color: {theme.SURFACE_3};
                    border: 1px solid {theme.BORDER_CYAN};
                }}
            """)
            self.lbl_native.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.TEXT_PRIMARY}; background: transparent; border: none;")
            self.chk_badge.setStyleSheet(f"""
                background-color: transparent;
                color: {theme.BORDER_SLATE};
                font-size: 13px;
                border: 1px solid {theme.BORDER_SLATE};
                border-radius: 13px;
            """)
            self.chk_badge.setVisible(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.lang_code)


class OnboardingView(QWidget):
    """Full-canvas onboarding screen welcoming new users and allowing instant language configuration."""
    completed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_lang = get_i18n().current_lang or "ar"
        self.cards_map = {}
        self._init_ui()
        self._apply_language_preview(self.selected_lang)

    def _init_ui(self):
        self.setStyleSheet(f"""
            OnboardingView {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #141A26, stop:0.4 #0E121B, stop:1 #080A0F);
            }}
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setAlignment(Qt.AlignCenter)

        # Center Card Container
        center_card = QFrame()
        center_card.setFixedWidth(740)
        center_card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(22, 28, 42, 0.95);
                border: 1px solid rgba(0, 210, 255, 0.22);
                border-radius: 16px;
            }}
        """)
        card_layout = QVBoxLayout(center_card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(20)

        # 1. Brand Logo & Product Banner
        brand_row = QHBoxLayout()
        brand_row.setAlignment(Qt.AlignCenter)
        brand_row.setSpacing(12)

        self.lbl_logo = QLabel("⚡ AERO SUITE")
        self.lbl_logo.setStyleSheet(
            f"font-size: 26px; font-weight: 900; color: {theme.CYAN_PRIMARY}; "
            f"letter-spacing: 2px; font-family: 'Space Grotesk', 'Segoe UI', sans-serif; background: transparent; border: none;"
        )
        brand_row.addWidget(self.lbl_logo)

        lbl_badge = QLabel(f"v{theme.APP_VERSION}")
        lbl_badge.setFixedHeight(28)
        lbl_badge.setAlignment(Qt.AlignCenter)
        lbl_badge.setStyleSheet(
            f"background-color: {theme.CYAN_ALPHA_15}; color: {theme.CYAN_PRIMARY}; "
            f"border: 1px solid {theme.BORDER_CYAN}; border-radius: 6px; padding: 0 10px; "
            f"font-size: 11px; font-weight: bold; background: {theme.CYAN_ALPHA_15};"
        )
        brand_row.addWidget(lbl_badge)
        card_layout.addLayout(brand_row)

        self.lbl_platform = QLabel("Dongfeng Shine (Aeolus D53) IVI Studio")
        self.lbl_platform.setAlignment(Qt.AlignCenter)
        self.lbl_platform.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; background: transparent; border: none; letter-spacing: 0.5px;")
        card_layout.addWidget(self.lbl_platform)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.5 {theme.CYAN_PRIMARY}, stop:1 transparent); border: none;")
        card_layout.addWidget(divider)

        # 2. Welcoming Headline & Prompt
        self.lbl_welcome = QLabel("مرحباً بك في Aero Suite")
        self.lbl_welcome.setAlignment(Qt.AlignCenter)
        self.lbl_welcome.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {theme.TEXT_PRIMARY}; "
            f"font-family: 'Space Grotesk', 'Cairo', 'Segoe UI', sans-serif; background: transparent; border: none;"
        )
        card_layout.addWidget(self.lbl_welcome)

        self.lbl_prompt = QLabel("اختر لغة العرض المفضلة لبدء تخصيص شاشة سيارتك\nSelect your preferred language to begin customizing your vehicle")
        self.lbl_prompt.setAlignment(Qt.AlignCenter)
        self.lbl_prompt.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; line-height: 1.5; background: transparent; border: none;")
        card_layout.addWidget(self.lbl_prompt)

        card_layout.addSpacing(6)

        # 3. Language Selection Grid (7 Languages)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        langs = [
            ("ar", 0, 0, 1, 1),
            ("en", 0, 1, 1, 1),
            ("es", 1, 0, 1, 1),
            ("pt", 1, 1, 1, 1),
            ("ru", 2, 0, 1, 1),
            ("zh", 2, 1, 1, 1),
            ("vi", 3, 0, 1, 2),
        ]

        for item in langs:
            code = item[0]
            r, c = item[1], item[2]
            row_span = item[3]
            col_span = item[4]
            meta = SUPPORTED_LANGUAGES.get(code, {})
            card = LanguageCard(code, meta, self)
            card.clicked.connect(self._on_card_clicked)
            grid_layout.addWidget(card, r, c, row_span, col_span)
            self.cards_map[code] = card

        card_layout.addLayout(grid_layout)

        card_layout.addSpacing(6)

        # 4. Action Button
        btn_box = QHBoxLayout()
        btn_box.setAlignment(Qt.AlignCenter)

        self.btn_start = QPushButton("ابدأ الاستخدام 🚀")
        self.btn_start.setFixedHeight(46)
        self.btn_start.setFixedWidth(300)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.CYAN_PRIMARY};
                color: #000000;
                font-size: 15px;
                font-weight: 900;
                border-radius: 8px;
                border: 1px solid {theme.CYAN_PRIMARY};
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: {theme.CYAN_HOVER};
                border-color: {theme.CYAN_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #00A6CC;
            }}
        """)
        self.btn_start.clicked.connect(self._on_start_clicked)
        btn_box.addWidget(self.btn_start)
        card_layout.addLayout(btn_box)

        # Bottom Tip
        self.lbl_tip = QLabel("يمكنك دائماً تغيير اللغة لاحقاً من الشريط العلوي للتطبيق 🌐")
        self.lbl_tip.setAlignment(Qt.AlignCenter)
        self.lbl_tip.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; background: transparent; border: none;")
        card_layout.addWidget(self.lbl_tip)

        root_layout.addWidget(center_card)

        # Update initial selection
        if self.selected_lang in self.cards_map:
            self.cards_map[self.selected_lang].set_selected(True)

    def _on_card_clicked(self, code: str):
        self.selected_lang = code
        for c, card in self.cards_map.items():
            card.set_selected(c == code)
        self._apply_language_preview(code)

    def _apply_language_preview(self, code: str):
        """Live updates text on the onboarding screen as the user toggles different language cards."""
        is_rtl = (code == "ar")
        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

        translations = {
            "ar": {
                "welcome": "مرحباً بك في استوديو Aero Suite ⚡",
                "prompt": "استوديو احترافي لتثبيت التطبيقات وتخصيص شاشات سيارات دانج فينج شاين.\nاختر لغتك المفضلة للبدء في تجهيز الفلاشة.",
                "start": "ابدأ الاستخدام 🚀",
                "tip": "يمكنك دائماً تغيير اللغة لاحقاً من الشريط العلوي للتطبيق 🌐"
            },
            "en": {
                "welcome": "Welcome to Aero Suite Studio ⚡",
                "prompt": "Advanced automotive payload generator & studio for Dongfeng Shine infotainment.\nSelect your preferred interface language to continue.",
                "start": "Get Started 🚀",
                "tip": "You can always change the language at any time from the top bar 🌐"
            },
            "es": {
                "welcome": "Bienvenido a Aero Suite Studio ⚡",
                "prompt": "Estudio avanzado de instalación de APK y personalización para Dongfeng Shine.\nElige tu idioma preferido para comenzar a preparar tu unidad USB.",
                "start": "Comenzar Ahora 🚀",
                "tip": "Siempre puedes cambiar el idioma desde la barra superior de la aplicación 🌐"
            },
            "pt": {
                "welcome": "Bem-vindo ao Aero Suite Studio ⚡",
                "prompt": "Estúdio profissional de instalação de APKs e customização Dongfeng Shine.\nEscolha seu idioma preferido para começar a preparar seu pen drive.",
                "start": "Começar Agora 🚀",
                "tip": "Você sempre pode alterar o idioma a qualquer momento na barra superior 🌐"
            },
            "ru": {
                "welcome": "Добро пожаловать в Aero Suite ⚡",
                "prompt": "Профессиональный инструмент настройки ГУ для Dongfeng Shine.\nВыберите удобный язык интерфейса для начала работы.",
                "start": "Начать использование 🚀",
                "tip": "Вы всегда сможете изменить язык в верхней панели программы 🌐"
            },
            "zh": {
                "welcome": "欢迎使用 Aero Suite 车机工作站 ⚡",
                "prompt": "专为东风奕炫 (Dongfeng Shine) 车机打造的 APK 安装与系统维护套件。\n请选择您的首选界面语言以开始配置。",
                "start": "立即开始 🚀",
                "tip": "您随时可以在顶部导航栏切换界面语言 🌐"
            },
            "vi": {
                "welcome": "Chào mừng đến với Aero Suite Studio ⚡",
                "prompt": "Bộ công cụ chuyên nghiệp cài đặt ứng dụng và tùy biến màn hình Dongfeng Shine.\nChọn ngôn ngữ giao diện ưa thích của bạn để bắt đầu chuẩn bị USB.",
                "start": "Bắt đầu ngay 🚀",
                "tip": "Bạn luôn có thể đổi ngôn ngữ bất cứ lúc nào từ thanh trên cùng 🌐"
            }
        }

        t_data = translations.get(code, translations["en"])
        self.lbl_welcome.setText(t_data["welcome"])
        self.lbl_prompt.setText(t_data["prompt"])
        self.btn_start.setText(t_data["start"])
        self.lbl_tip.setText(t_data["tip"])

    def _on_start_clicked(self):
        """Finalizes language selection, commits to settings, and unlocks the main studio interface."""
        set_onboarding_completed(True)
        get_i18n().set_language(self.selected_lang)
        self.completed.emit(self.selected_lang)
