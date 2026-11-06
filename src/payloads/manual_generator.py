"""
manual_generator.py — Unified & Localized Vehicle Manuals Generator (_Info.html).
Generates friendly, colloquial, step-by-step guides for Dongfeng Shine infotainment payloads.
Supports Single-Action and Multi-Action (Composite Basket) USB flash drives.
Languages: Arabic (Egyptian colloquial), English, Russian, and Chinese.
"""
import os
import re
import html
import base64
from typing import Tuple, List, Dict, Any, Optional

from core.i18n import get_i18n
from core.templating import render_template_file
from core.constants import (
    DEVELOPER_NAME,
    DEVELOPER_EMAIL,
    DEVELOPER_PHONE,
    SIGNATURE_BANNER,
    FACTORY_LAUNCHER_PKG,
    ACTION_EXECUTION_ORDER
)


def get_signature_banner(lang: str = "ar") -> str:
    if lang == "ar":
        return f"""============================================================
🛡️ حماية النظام الذكية (Multi-Vehicle Safe Execution):
الفلاشة مجهزة بنظام حماية ذكي يربط العملية بسيريال الشاشة؛ حيث صُممت الفلاشة لتُنفذ مرة واحدة فقط لكل سيارة (مع إمكانية استخدامها مباشرة على سيارات متعددة)، وذلك لضمان استقرار النظام وحمايته من التكرار العرضي.
============================================================
Aero Automotive Suite — نسخة دونج فينج شاين
برمجة وتطوير:
{DEVELOPER_NAME}
✉️ {DEVELOPER_EMAIL}   📞 {DEVELOPER_PHONE}
============================================================="""
    elif lang == "ru":
        return f"""============================================================
🛡️ ЗАЩИТА СИСТЕМЫ (Безопасное выполнение на нескольких авто):
Флешка оснащена защитой по серийному номеру экрана; она рассчитана на однократное применение для каждого автомобиля (с поддержкой работы на нескольких машинах) для обеспечения стабильности системы и защиты от случайного повторного запуска.
============================================================
Aero Automotive Suite — Версия для Dongfeng Shine
Разработка и поддержка:
{DEVELOPER_NAME}
✉️ {DEVELOPER_EMAIL}   📞 {DEVELOPER_PHONE}
============================================================="""
    elif lang == "zh":
        return f"""============================================================
🛡️ 系统智能安全防护 (多车安全执行):
本 U 盘具备车机硬件序列号智能绑定保护，专为每台车执行一次设计（支持在多台车辆上直接使用），以确保车机系统稳定性并防止意外重复操作。
============================================================
Aero Automotive Suite — 东风奕炫 (Dongfeng Shine) 专属版
开发者:
{DEVELOPER_NAME}
✉️ {DEVELOPER_EMAIL}   📞 {DEVELOPER_PHONE}
============================================================="""
    else:
        return f"""============================================================
🛡️ SMART SYSTEM PROTECTION (Multi-Vehicle Safe Execution):
This USB drive is equipped with smart vehicle serial protection, designed for one-time execution per vehicle (fully supporting multi-car deployment) to safeguard system stability and prevent accidental repetition.
============================================================
{SIGNATURE_BANNER}"""


_INDIC_DIGITS = {
    '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
    '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
}


def _to_indic(num_str: str) -> str:
    return ''.join(_INDIC_DIGITS.get(c, c) for c in str(num_str))


def _apply_arabic_rtl_formatting(text: str) -> str:
    """
    Enforces native Right-To-Left (RTL) reading flow and alignment for Arabic plain text files (_Info.txt).
    """
    def swap_title(m):
        emoji = m.group(1).strip()
        arabic_title = m.group(2).strip()
        return f"{arabic_title} — Aero Suite {emoji}"

    text = re.sub(r'^(.*?)\s*Aero Suite\s*—\s*(دليل\s+[^\n]+)', swap_title, text, flags=re.MULTILINE)
    text = text.replace('Aero Automotive Suite — نسخة دونج فينج شاين', 'نسخة دونج فينج شاين — Aero Automotive Suite')
    text = text.replace('الـ USB', 'USB')

    def replace_num(m):
        nums = ''.join(_INDIC_DIGITS.get(c, c) for c in m.group(1))
        return f"{nums}. "

    text = re.sub(r'^(\d+)\.\s+', replace_num, text, flags=re.MULTILINE)
    return "\ufeff" + text


# ============================================================================
# ============================================================================
# SECTION 1: COMMON MULTILINGUAL TEMPLATES & VOCABULARY
# ============================================================================

COMMON_TEMPLATES = {
    "ar": {
        "target_vehicle": "السيارة المستهدفة: شاشة دونج فينج شاين (Dongfeng Shine / Aeolus D53)",
        "composite_title": "🚀 دليل تشغيل فلاشة الشاشة — Aero Suite ({count} مهام)",
        "sec_overview": "1. نظرة عامة وقائمة العمليات المشمولة",
        "sec_steps": "2. خطوات التشغيل في السيارة",
        "sec_verification": "3. خطوات التأكيد وفحص النتيجة",
        "step_start_car": "اضغط على زر التشغيل (الكونتاكت) ضغطة واحدة لتشغيل الشاشة فقط (وضع ACC)، وانتظر ثوانٍ حتى تفتح وتستقر على الواجهة الرئيسية.",
        "step_start_car_tweaks": "اضغط زر التشغيل (الكونتاكت) مرتين بدون الضغط على الفرامل (وضع ON الكامل) حتى تضيء لوحة العدادات، لضمان استجابة وتخزين تعديلات السيارة في كمبيوتر الـ BCM.",
        "step_insert_usb": "ركب الفلاشة في منفذ USB الخاص بالشاشة (سيقرأ النظام الفلاشة ويبدأ التنفيذ تلقائياً خلال 10 إلى 20 ثانية من تركيبها).",
        "step_executing": "سيبدأ النظام تلقائياً في تنفيذ العمليات في الخلفية. ⏱️ الوقت المتوقع: {time_est} (يُرجى عدم إطفاء الشاشة أو لمسها أثناء التنفيذ).",
        "step_executing_single": "سيبدأ النظام تلقائياً في تنفيذ العملية في الخلفية. ⏱️ الوقت المتوقع: {time_est}.",
        "step_executing_multi": "سيبدأ النظام تلقائياً في تنفيذ العمليات المحددة بالتتابع في الخلفية. ⏱️ الوقت المتوقع: {time_est}.",
        "step_reboot_finish": "نهاية العملية (تنفيذ متعدد المراحل وإعادة تشغيل): قد تقوم الشاشة بعمل إعادة تشغيل (ريستارت) مرة أو أكثر حسب العمليات المطلوبة. ⚠️ تحذير هام جداً: اترك الفلاشة موصولة طوال فترات إعادة التشغيل ولا تنزعها أبداً أثناء انطفاء الشاشة أو إقلاعها. انزع الفلاشة فقط بعد اكتمال إقلاع النظام بالكامل وظهور التطبيق النهائي أو اللانشر أمامك على الشاشة (الفلاشة مؤمنة بالكامل ضد التكرار).",
        "step_chime_finish": "نهاية العملية (بدون ريستارت): ستسمع صوت التنبيه الصيني من الشاشة فور اكتمال التنفيذ لتأكيد نجاح العملية دون الحاجة لإعادة تشغيل الشاشة. يمكنك إزالة الفلاشة بأمان فوراً والبدء في استخدام ميزاتك الجديدة (الفلاشة محمية تماماً من التكرار).",
        "step_reboot_notice": "قد تقوم الشاشة بعمل إعادة تشغيل (ريستارت) مرة أو أكثر حسب العمليات المطلوبة. ⚠️ تحذير هام: اترك الفلاشة موصولة طوال فترات إعادة التشغيل، ولا تنزعها إلا بعد اكتمال إقلاع الشاشة وظهور التطبيق النهائي أمامك.",
        "step_success_notice": "ستسمع صوت التنبيه الصيني من الشاشة فور اكتمال التنفيذ لتأكيد نجاح العملية دون الحاجة لإعادة تشغيل الشاشة. يمكنك إزالة الفلاشة بأمان فوراً والبدء في استخدام ميزاتك الجديدة (الفلاشة محمية تماماً من التكرار).",
        "reboot_badge": "يتطلب إعادة تشغيل الشاشة",
        "no_reboot_badge": "لا يتطلب إعادة تشغيل",
    },
    "en": {
        "target_vehicle": "Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System",
        "composite_title": "🚀 Smart USB Execution Guide — Aero Suite ({count} Operations)",
        "sec_overview": "1. TECHNICAL OVERVIEW & OPERATION MANIFEST",
        "sec_steps": "2. VEHICLE USAGE INSTRUCTIONS",
        "sec_verification": "3. POST-EXECUTION VERIFICATION",
        "step_start_car": "Press the start button (contact/ACC) once to power on the screen only, and wait a few seconds until it settles on the home screen.",
        "step_start_car_tweaks": "Press the start button twice without pressing the brake (full ON mode) until the cluster lights up, ensuring the vehicle's BCM accepts and saves the CAN-Bus tweaks.",
        "step_insert_usb": "Insert the USB drive into the screen's USB port (the system will read the drive and start execution automatically within 10-20 seconds).",
        "step_executing": "The system will automatically execute the operations in the background. ⏱️ Estimated Time: {time_est} (please do not turn off the screen or touch it during execution).",
        "step_executing_single": "The system will automatically execute the requested operation. ⏱️ Estimated Time: {time_est}.",
        "step_executing_multi": "The automated script will execute the configured tasks in sequence. ⏱️ Estimated Time: {time_est}.",
        "step_reboot_finish": "Completion (Multi-Stage Execution & Reboot): The screen may automatically reboot one or more times depending on the queued operations. ⚠️ CRITICAL NOTICE: KEEP THE USB DRIVE CONNECTED throughout all reboots. Do NOT remove the USB while the screen is black or booting. Only remove the USB after the final app or launcher appears and stabilizes on screen (the USB is fully locked against accidental re-execution).",
        "step_chime_finish": "Completion (No Reboot Required): You will hear the vehicle's built-in audible chime confirming successful execution without needing a reboot. You can safely remove the USB drive immediately and enjoy your new features (fully protected against repetition).",
        "step_reboot_notice": "The screen may automatically reboot one or more times. ⚠️ DO NOT UNPLUG the USB drive during reboots. Keep it connected until the final application or launcher is fully open on the screen.",
        "step_success_notice": "You will hear the vehicle's built-in audible chime confirming successful execution without needing a reboot. You can safely remove the USB drive immediately and enjoy your new features (fully protected against repetition).",
        "reboot_badge": "Requires Screen Reboot",
        "no_reboot_badge": "No Reboot Required",
    },
    "ru": {
        "target_vehicle": "Целевой автомобиль: Мультимедийная система Dongfeng Shine (Aeolus D53)",
        "composite_title": "🚀 Руководство по запуску USB-накопителя — Aero Suite ({count} операций)",
        "sec_overview": "1. ОБЩИЙ ОБЗОР И СПИСОК ОПЕРАЦИЙ",
        "sec_steps": "2. ИНСТРУКЦИЯ ПО ПРИМЕНЕНИЮ В АВТОМОБИЛЕ",
        "sec_verification": "3. ПРОВЕРКА РЕЗУЛЬТАТА И ДАЛЬНЕЙШИЕ ДЕЙСТВИЯ",
        "step_start_car": "Нажмите кнопку запуска (ACC/зажигание) один раз, чтобы включить только экран, и подождите несколько секунд до загрузки главного меню.",
        "step_start_car_tweaks": "Нажмите кнопку запуска дважды без нажатия на тормоз (полный режим зажигания ON), чтобы загорелась приборная панель — это необходимо для сохранения настроек CAN-Bus в блоке BCM.",
        "step_insert_usb": "Вставьте USB-флешку в порт USB мультимедиа (система распознает накопитель и начнет выполнение автоматически через 10-20 секунд).",
        "step_executing": "Система автоматически выполнит операции в фоновом режиме. ⏱️ Ожидаемое время: {time_est} (не выключайте экран и не трогайте его во время выполнения).",
        "step_executing_single": "Система автоматически выполнит выбранную операцию. ⏱️ Ожидаемое время: {time_est}.",
        "step_executing_multi": "Автоматический скрипт выполнит настроенные задачи по порядку. ⏱️ Ожидаемое время: {time_est}.",
        "step_reboot_finish": "Завершение (Многоэтапное выполнение и перезагрузка): Экран может автоматически перезагрузиться один или несколько раз. ⚠️ ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ: НЕ ИЗВЛЕКАЙТЕ USB-накопитель во время перезагрузок. Держите флешку подключенной до тех пор, пока система полностью не загрузится и на экране не появится целевое приложение или лаунчер (флешка защищена от повторного запуска).",
        "step_chime_finish": "Завершение (Без перезагрузки): Вы услышите звуковой сигнал мультимедиа, подтверждающий успешное завершение без перезагрузки экрана. Вы можете безопасно извлечь флешку и сразу пользоваться новыми функциями (повторный запуск исключен).",
        "step_reboot_notice": "Экран может перезагрузиться несколько раз. НЕ ИЗВЛЕКАЙТЕ флешку до полной загрузки экрана и открытия целевого приложения.",
        "step_success_notice": "Вы услышите звуковой сигнал мультимедиа, подтверждающий успешное завершение без перезагрузки экрана. Вы можете безопасно извлечь флешку и сразу пользоваться новыми функциями (повторный запуск исключен).",
        "reboot_badge": "Требуется перезагрузка экрана",
        "no_reboot_badge": "Перезагрузка не требуется",
    },
    "zh": {
        "target_vehicle": "目标车型: 东风奕炫 (Dongfeng Shine / Aeolus D53) 车机系统",
        "composite_title": "🚀 车机智能 U 盘执行指南 — Aero Suite ({count} 项操作)",
        "sec_overview": "1. 技术概述与操作清单",
        "sec_steps": "2. 车辆上车操作步骤",
        "sec_verification": "3. 结果验证与后续操作",
        "step_start_car": "轻按一次一键启动按键（开启 ACC/车机电源）仅点亮中控屏幕，等待数秒直至屏幕完全稳定在主界面。",
        "step_start_car_tweaks": "在不踩刹车的情况下按两次一键启动键（进入完整 ON 档点亮仪表盘），以确保车身电脑 (BCM) 成功接收并永久保存 CAN-Bus 车身设置。",
        "step_insert_usb": "将 U 盘插入中控屏对应的 USB 接口（系统将在插入后 10 至 20 秒内自动识别并开始执行）。",
        "step_executing": "系统将在后台全自动执行配置的操作。⏱️ 预计耗时: {time_est}（执行期间请勿关闭屏幕电源或触碰屏幕）。",
        "step_executing_single": "系统将自动开始执行设定的任务。⏱️ 预计耗时: {time_est}。",
        "step_executing_multi": "自动化脚本将按顺序执行配置的任务。⏱️ 预计耗时: {time_est}。",
        "step_reboot_finish": "执行完成 (多阶段自动化执行与重启): 车机屏幕可能会根据所选操作自动重启一次或多次。⚠️ 严正警告: 在整个重启与启动过程中请务必保持 U 盘插入，严禁拔出！只有在车机完全启动就绪、最终目标应用或新桌面完全显示在屏幕上之后，方可安全拔出 U 盘（系统已具备智能防重复锁）。",
        "step_chime_finish": "执行完成 (无需重启): 听到车机发出的提示音后，即代表操作已顺利完成，无需重启屏幕。您可以立即拔出 U 盘并开始体验新功能（系统已锁定防重复执行）。",
        "step_reboot_notice": "车机可能会自动重启一次或多次。在所有重启阶段完成且最终应用完全打开前，请切勿拔下 U 盘！",
        "step_success_notice": "听到车机发出的提示音后，即代表操作已顺利完成，无需重启屏幕。您可以立即拔出 U 盘并开始体验新功能（系统已锁定防重复执行）。",
        "reboot_badge": "需重启车机屏幕",
        "no_reboot_badge": "无需重启",
    }
}


# ============================================================================
# SECTION 2: DYNAMIC PAYLOAD DESCRIPTORS & SPECS (14 FEATURES)
# ============================================================================

def _fmt_backup_dyn(kw, lang):
    b_type = kw.get("b_type", "personal").lower()
    p_name = kw.get("preset_name", "") or "Community Preset"
    author = kw.get("author", "") or ("مطور شاين" if lang == "ar" else "Author")
    inc_media = kw.get("include_media", False)
    if lang == "ar":
        mode_str = "نمط مجتمعي للمشاركة (خالي من البيانات الشخصية)" if b_type == "community" else "نمط شخصي خاص (نسخة متطابقة 1:1)"
        media_str = "مشمولة بالنسخ" if inc_media else "مستبعدة (تطبيقات وإعدادات فقط)"
        return f"• نوع النسخة: {mode_str}\n• اسم النمط: {p_name}\n• الناشر: {author}\n• ملفات الميديا: {media_str}\n• مسار النسخ على الفلاشة: USB:/Backup/"
    elif lang == "ru":
        mode_str = "Сообщество (без личных данных)" if b_type == "community" else "Личный 1:1 клон"
        media_str = "Включены" if inc_media else "Исключены"
        return f"• Режим: {mode_str}\n• Пресет: {p_name}\n• Автор: {author}\n• Медиа: {media_str}\n• Путь: USB:/Backup/"
    elif lang == "zh":
        mode_str = "社区安全分享模式 (已脱敏)" if b_type == "community" else "个人全量 1:1 克隆"
        media_str = "包含媒体" if inc_media else "仅应用与系统设置"
        return f"• 备份模式: {mode_str}\n• 预设名称: {p_name}\n• 创作者: {author}\n• 媒体文件: {media_str}\n• 存储位置: USB:/Backup/"
    else:
        mode_str = "Community Shared (Scrubbed)" if b_type == "community" else "Personal Private 1:1"
        media_str = "Included" if inc_media else "Excluded"
        return f"• Backup Mode: {mode_str}\n• Preset Name: {p_name}\n• Author: {author}\n• Media: {media_str}\n• Destination: USB:/Backup/"


def _fmt_install_apps_dyn(kw, lang):
    selected_apks = kw.get("selected_apks", [])
    normalized_apks = []
    for a in selected_apks:
        if isinstance(a, str):
            normalized_apks.append({"filename": a, "display_name": a, "install_target": "user"})
        elif isinstance(a, dict):
            normalized_apks.append(a)
    selected_apks = normalized_apks

    auto_pkg = kw.get("auto_launch_package", "")
    sys_cnt = kw.get("system_app_count", sum(1 for a in selected_apks if a.get("install_target") == "system"))
    usr_cnt = kw.get("user_app_count", len(selected_apks) - sys_cnt)
    lines = []
    if lang == "ar":
        lines.append(f"• إجمالي التطبيقات: {len(selected_apks)} (نظام: {sys_cnt} | مستخدم: {usr_cnt})")
        if auto_pkg: lines.append(f"• التشغيل التلقائي عند الإقلاع: {auto_pkg}")
        for a in selected_apks:
            target = "نظام (/system/priv-app)" if a.get("install_target") == "system" else "مستخدم (/data/app)"
            lines.append(f"  - {a.get('display_name', a.get('filename'))} | {target}")
    elif lang == "ru":
        lines.append(f"• Всего приложений: {len(selected_apks)} (Системные: {sys_cnt} | Пользовательские: {usr_cnt})")
        if auto_pkg: lines.append(f"• Автозапуск: {auto_pkg}")
        for a in selected_apks:
            target = "Системное" if a.get("install_target") == "system" else "Пользовательское"
            lines.append(f"  - {a.get('display_name', a.get('filename'))} | {target}")
    elif lang == "zh":
        lines.append(f"• 应用总数: {len(selected_apks)} (系统应用: {sys_cnt} | 普通用户应用: {usr_cnt})")
        if auto_pkg: lines.append(f"• 开机自启: {auto_pkg}")
        for a in selected_apks:
            target = "系统应用 (/system/priv-app)" if a.get("install_target") == "system" else "普通应用 (/data/app)"
            lines.append(f"  - {a.get('display_name', a.get('filename'))} | {target}")
    else:
        lines.append(f"• Total APKs: {len(selected_apks)} (System: {sys_cnt} | User: {usr_cnt})")
        if auto_pkg: lines.append(f"• Auto-Launch Package: {auto_pkg}")
        for a in selected_apks:
            target = "System App" if a.get("install_target") == "system" else "User App"
            lines.append(f"  - {a.get('display_name', a.get('filename'))} | {target}")
    return "\n".join(lines)


def _fmt_uninstall_apps_dyn(kw, lang):
    pkgs = kw.get("vetted_packages", kw.get("packages", []))
    if not pkgs: return ""
    lbl = "• الحزم المستهدفة للحذف:" if lang == "ar" else ("• Удаляемые пакеты:" if lang == "ru" else ("• 待卸载软件包列表:" if lang == "zh" else "• Targeted Packages for Removal:"))
    return f"{lbl}\n" + "\n".join(f"  - {p}" for p in pkgs)


def _fmt_open_app_dyn(kw, lang):
    lbl = kw.get("display_label", kw.get("app_name", "Application"))
    pkg = kw.get("clean_pkg", kw.get("package_name", ""))
    if lang == "ar": return f"• اسم التطبيق: {lbl}\n• الحزمة: {pkg}"
    elif lang == "ru": return f"• Приложение: {lbl}\n• Пакет: {pkg}"
    elif lang == "zh": return f"• 目标应用名称: {lbl}\n• 软件包名: {pkg}"
    else: return f"• Target Application: {lbl}\n• Package: {pkg}"


def _fmt_gms_dyn(kw, lang):
    opts = []
    if kw.get("include_gboard"): opts.append("Gboard Keyboard (Arabic/English theme)" if lang != "ar" else "لوحة مفاتيح Gboard (مع الثيم العربي المخصص)")
    if kw.get("include_chrome"): opts.append("Google Chrome Browser" if lang != "ar" else "متصفح Google Chrome")
    if kw.get("include_maps"): opts.append("Google Maps" if lang != "ar" else "خرائط Google Maps")
    total_cnt = 7 + len(opts)
    if lang == "ar":
        lines = [
            f"• إجمالي الحزم البرمجية: {total_cnt} (7 حزم نظام أساسية + {len(opts)} تطبيقات مستخدم اختيارية)",
            "• حزم النظام الأساسية (7 حزم مدمجة في /system/priv-app):",
            "  - إطار خدمات جوجل (Google Services Framework)",
            "  - إدارة الحسابات والمزامنة (Google Account Manager)",
            "  - خدمات جوجل بلاي الأساسية (Google Play Services)",
            "  - متجر التطبيقات الرسمي (Google Play Store)",
            "  - تطبيق البحث والتعرف الصوتي (Google Search)",
            "  - محرك تحويل النص لكلام (Google Speech & TTS)",
            "  - مدير الملفات الرسمي (Files by Google)",
        ]
        if opts:
            lines.append("• تطبيقات المستخدم الاختيارية المختارة (/data/app):")
            for o in opts:
                lines.append(f"  - {o}")
        else:
            lines.append("• تطبيقات المستخدم الاختيارية: لم يتم اختيار تطبيقات إضافية (المنظومة الأساسية فقط).")
        return "\n".join(lines)
    elif lang == "ru":
        lines = [
            f"• Всего пакетов: {total_cnt} (7 системных компонентов + {len(opts)} приложений пользователя)",
            "• Базовые системные компоненты (7 пакетов в /system/priv-app):",
            "  - Google Services Framework",
            "  - Google Account Manager",
            "  - Google Play Services",
            "  - Google Play Store",
            "  - Google Search & Voice",
            "  - Google Speech & TTS",
            "  - Files by Google",
        ]
        if opts:
            lines.append("• Дополнительные приложения пользователя (/data/app):")
            for o in opts:
                lines.append(f"  - {o}")
        return "\n".join(lines)
    elif lang == "zh":
        lines = [
            f"• 软件包总计: {total_cnt} 个 (7 个系统底层核心套件 + {len(opts)} 个可选用户应用)",
            "• 系统核心服务套件 (7 个安装至 /system/priv-app):",
            "  - 谷歌服务框架 (Google Services Framework)",
            "  - 谷歌账户管理与同步 (Google Account Manager)",
            "  - 谷歌核心服务 (Google Play Services)",
            "  - 谷歌官方 Play 商店 (Google Play Store)",
            "  - 谷歌语音与全局搜索 (Google Search)",
            "  - 谷歌语音合成与识别引擎 (Google Speech & TTS)",
            "  - 官方文件管理器 (Files by Google)",
        ]
        if opts:
            lines.append("• 选中的附加普通用户应用 (/data/app):")
            for o in opts:
                lines.append(f"  - {o}")
        return "\n".join(lines)
    else:
        lines = [
            f"• Total Packages: {total_cnt} (7 Core System Packages + {len(opts)} Optional User Apps)",
            "• Core System Packages (7 integrated into /system/priv-app):",
            "  - Google Services Framework",
            "  - Google Account Manager",
            "  - Google Play Services",
            "  - Google Play Store",
            "  - Google Search & Voice",
            "  - Google Speech & TTS",
            "  - Files by Google",
        ]
        if opts:
            lines.append("• Selected Optional User Apps (/data/app):")
            for o in opts:
                lines.append(f"  - {o}")
        return "\n".join(lines)


def _fmt_restore_dyn(kw, lang):
    folder = kw.get("folder_bname", "Backup")
    is_comm = kw.get("is_community", False)
    if lang == "ar":
        m_str = "نمط مجتمعي (آمن ومحمي بدون حسابات أو شبكات واي فاي خاصة)" if is_comm else "نسخة شخصية خاصة (استعادة شاملة 1:1)"
        return f"• مجلد النسخة الاحتياطية: {folder}\n• نمط الاستعادة: {m_str}"
    elif lang == "ru":
        m_str = "Режим сообщества (без приватных аккаунтов)" if is_comm else "Личный архив 1:1"
        return f"• Папка бэкапа: {folder}\n• Тип восстановления: {m_str}"
    elif lang == "zh":
        m_str = "社区预设恢复 (保护隐私与 Wi-Fi 凭证)" if is_comm else "个人 1:1 全量还原"
        return f"• 备份来源目录: {folder}\n• 还原模式: {m_str}"
    else:
        m_str = "Community Preset (Zero-leakage, accounts preserved)" if is_comm else "Personal Private 1:1 Clone"
        return f"• Backup Source: {folder}\n• Restoration Scope: {m_str}"


def _fmt_tweaks_dyn(kw, lang):
    tweaks = kw.get("selected_tweaks", [])
    if not tweaks: return ""
    header = "• التعديلات المختارة للسيارة:" if lang == "ar" else ("• Выбранные твики:" if lang == "ru" else ("• 所选高级调教功能:" if lang == "zh" else "• Selected Vehicle Tweaks:"))
    lines = [header]
    for tw in tweaks:
        if isinstance(tw, str):
            from core.vehicle_tweaks_data import VEHICLE_TWEAKS
            found = next((t for t in VEHICLE_TWEAKS if t.get("id") == tw), None)
            t_data = found or {"id": tw, "name_ar": tw, "name_en": tw}
            action = "enable"
        elif isinstance(tw, dict):
            t_data = tw.get("tweak", tw)
            if not isinstance(t_data, dict):
                t_data = {"id": str(t_data), "name_ar": str(t_data), "name_en": str(t_data)}
            action = tw.get("action", "enable")
        else:
            continue
        name = t_data.get(f"name_{lang}", t_data.get("name_en", t_data.get("name_ar", t_data.get("id", "Tweak"))))
        act_lbl = ("تفعيل" if action == "enable" else "تعطيل") if lang == "ar" else action.upper()
        lines.append(f"  - [{act_lbl}] {name}")
    return "\n".join(lines)


FEATURE_SPECS = {
    "backup": {
        "emoji": "💾",
        "title": {
            "ar": "دليل النسخ الاحتياطي للنظام والبيانات",
            "en": "System & Data Backup Manual",
            "ru": "Руководство по резервному копированию",
            "zh": "系统与数据完整备份指南"
        },
        "overview": {
            "ar": "السكريبت هيسحب نسخة احتياطية كاملة من شاشة عربيتك ويحفظها على الفلاشة في مجلد USB:/Backup/ لتأمين التطبيقات والإعدادات والبيانات.",
            "en": "Extracts a complete vehicle snapshot into USB:/Backup/ to preserve applications, configurations, and vehicle settings.",
            "ru": "Создает полную резервную копию системы и настроек автомобиля в папку USB:/Backup/.",
            "zh": "将车机系统的所有应用程序、配置文件及系统数据完整提取并备份至 USB:/Backup/ 目录。"
        },
        "verification": {
            "ar": "بعد اكتمال النسخ في السيارة، وصّل الفلاشة بالكمبيوتر/اللابتوب وافتح برنامج Aero Suite، ثم اضغط على زر 'مزامنة النسخة للكمبيوتر (Sync)' لنقل النسخة الاحتياطية وتأمينها داخل خزينة البرنامج على جهازك.",
            "en": "After backup completes in car, plug the USB into your PC, open Aero Suite, and click 'Sync to PC' to securely transfer and archive the backup into the program vault.",
            "ru": "После завершения в автомобиле подключите флешку к ПК, откройте Aero Suite и нажмите кнопку «Синхронизировать с ПК», чтобы сохранить копию в хранилище программы.",
            "zh": "车机备份完成后，将 U 盘插回电脑并打开 Aero Suite，点击“同步至电脑”按钮，将备份数据安全归档至本地程序库。"
        },
        "requires_reboot": False,
        "dynamic_fn": _fmt_backup_dyn
    },
    "restore": {
        "emoji": "📥",
        "title": {
            "ar": "دليل استعادة النسخة الاحتياطية للشاشة (١٢ خطوة)",
            "en": "12-Step Complete Vehicle Restoration Manual",
            "ru": "Руководство по 12-этапному восстановлению системы",
            "zh": "车机系统 12 步完整恢复指南"
        },
        "overview": {
            "ar": "السكريبت هيرجع شاشة عربيتك لحالتها المحفوظة بالكامل عبر معمارية الـ 12 خطوة المتطورة مع مزامنة المعرفات UIDs وصلاحيات SELinux.",
            "en": "Restores complete vehicle state from PC Vault using the 12-step restoration engine with dynamic UID mapping and SELinux relabeling.",
            "ru": "Восстанавливает систему из архива с помощью 12-этапного алгоритма с динамическим маппингом UID и SELinux.",
            "zh": "利用 12 步恢复引擎从备份库完整还原车机系统，支持动态 UID 映射与 SELinux 自动修复。"
        },
        "verification": {
            "ar": "بعد إعادة تشغيل الشاشة، تأكد من استعادة التطبيقات، الإعدادات، وأجهزة البلوتوث المقترنة بالكامل.",
            "en": "After reboot, confirm that all restored applications, settings, and paired devices are functional.",
            "ru": "После перезагрузки убедитесь, что все приложения, настройки и устройства Bluetooth восстановлены.",
            "zh": "重启后，检查并确认所有恢复的应用、系统设置及已配对设备正常就绪。"
        },
        "requires_reboot": True,
        "dynamic_fn": _fmt_restore_dyn
    },
    "install_apps": {
        "emoji": "📦",
        "title": {
            "ar": "دليل تثبيت التطبيقات المحددة",
            "en": "Application Installation Manual",
            "ru": "Руководство по установке приложений",
            "zh": "应用程序批量安装指南"
        },
        "overview": {
            "ar": "تثبيت حزمة التطبيقات المحددة على شاشة السيارة وفك حظر التثبيت الخارجي ومعالجة الأذونات تلقائياً.",
            "en": "Deploys selected applications with OEM sideload policy unlock and optional auto-launch configuration.",
            "ru": "Устанавливает выбранные приложения с разблокировкой OEM-политик и автозапуском.",
            "zh": "批量部署所选应用，解锁原厂侧载限制并按需配置自启动。"
        },
        "verification": {
            "ar": "افتح قائمة التطبيقات على الشاشة وتأكد من ظهور وعمل التطبيقات المثبتة بسلاسة.",
            "en": "Open the apps drawer on the screen and verify the installed applications launch properly.",
            "ru": "Откройте список приложений на экране и проверьте запуск установленных программ.",
            "zh": "在车机应用列表查看并验证已安装应用能够正常启动和运行。"
        },
        "requires_reboot": lambda kw: kw.get("system_app_count", 0) > 0,
        "dynamic_fn": _fmt_install_apps_dyn
    },
    "uninstall_apps": {
        "emoji": "🧹",
        "title": {
            "ar": "دليل إزالة التطبيقات بأمان",
            "en": "Safe Application Removal Manual",
            "ru": "Руководство по безопасному удалению приложений",
            "zh": "应用软件安全卸载指南"
        },
        "overview": {
            "ar": "حذف التطبيقات المختارة من الشاشة مع تنظيف كاش الدالفيك والبيانات المؤقتة بالكامل.",
            "en": "Safely uninstalls selected third-party applications and clears Dalvik bytecode caches.",
            "ru": "Безопасно удаляет выбранные сторонние приложения и очищает кэш Dalvik.",
            "zh": "安全卸载所选第三方应用程序并彻底清理相关缓存与数据。"
        },
        "verification": {
            "ar": "تأكد من اختفاء التطبيقات المحذوفة من قائمة التطبيقات وتوفر مساحة تخزينية إضافية.",
            "en": "Confirm that the uninstalled packages no longer appear in the app drawer.",
            "ru": "Убедитесь, что удаленные приложения больше не отображаются в списке.",
            "zh": "检查车机桌面及应用列表，确认已卸载应用已被彻底清除。"
        },
        "requires_reboot": False,
        "dynamic_fn": _fmt_uninstall_apps_dyn
    },
    "open_app": {
        "emoji": "🚀",
        "title": {
            "ar": "دليل تشغيل التطبيق المباشر",
            "en": "Direct Application Launch Manual",
            "ru": "Руководство по прямому запуску приложения",
            "zh": "直接启动指定应用指南"
        },
        "overview": {
            "ar": "تشغيل التطبيق المحدد فوراً على الشاشة عبر محرك الاستدعاء الذكي ذو الـ 4 طبقات.",
            "en": "Instantly starts the specified application on the screen using the 4-tier automotive launch engine.",
            "ru": "Мгновенно запускает указанное приложение с помощью 4-уровневого механизма запуска.",
            "zh": "通过 4 级车机容错启动引擎直接拉起目标应用程序。"
        },
        "verification": {
            "ar": "سيعمل التطبيق مباشرة على شاشة السيارة أمامك.",
            "en": "The target application should now be active on the display.",
            "ru": "Целевое приложение должно запуститься на экране.",
            "zh": "目标应用程序应立即在前台正常显示。"
        },
        "requires_reboot": False,
        "dynamic_fn": _fmt_open_app_dyn
    },
    "open_settings": {
        "emoji": "⚙️",
        "title": {
            "ar": "دليل فتح الإعدادات الأصلية للشاشة",
            "en": "Open Native Android Settings Manual",
            "ru": "Руководство по открытию настроек Android",
            "zh": "调出原生 Android 系统设置说明"
        },
        "overview": {
            "ar": "السكريبت هيفتح تطبيق إعدادات الأندرويد الأصلية للشاشة (com.android.settings) مباشرة للتحكم في خيارات المطور واللغات والشبكات.",
            "en": "Directly launches native Android Settings to expose full developer options and network controls.",
            "ru": "Открывает оригинальные настройки Android для доступа к меню разработчика и сетям.",
            "zh": "直接调出原生 Android 设置菜单，解锁开发者选项与高级连接控制。"
        },
        "verification": {
            "ar": "افتح شريط الإشعارات أو قائمة التطبيقات وستجد الإعدادات الأصلية مفتوحة ومتاحة للاستخدام.",
            "en": "Native Android Settings are now open and available for configuration.",
            "ru": "Оригинальные настройки Android открыты и готовы к использованию.",
            "zh": "原生系统设置已成功打开，您可以开始进行配置。"
        },
        "requires_reboot": False
    },
    "install_gms": {
        "emoji": "🌐",
        "title": {
            "ar": "دليل تثبيت منظومة خدمات جوجل المتكاملة",
            "en": "Google Play Services & Ecosystem Suite Manual",
            "ru": "Руководство по установке экосистемы сервисов Google",
            "zh": "谷歌移动服务生态与 Play 商店安装说明书"
        },
        "overview": {
            "ar": "تثبيت المنظومة الرسمية لخدمات جوجل (7 حزم نظام أساسية مدمجة + حتى 3 تطبيقات مستخدم اختيارية) مع تنظيف شامل مسبق وزرع مكتبات الـ ARM لضمان استقرار الشاشة 100%.",
            "en": "Deploys the official Google ecosystem (7 integrated core system packages + up to 3 optional user apps) with automated pre-install deep cleanup and native ARM library injection for 100% stability.",
            "ru": "Устанавливает официальную экосистему Google (7 базовых системных пакетов + до 3 опциональных приложений пользователя) с предварительной глубокой очисткой и внедрением ARM-библиотек для 100% стабильности.",
            "zh": "部署官方谷歌服务生态（7 个底层核心系统特权套件 + 至多 3 个可选普通应用），安装前自动执行深度清理并注入原生 ARM 库，保障 100% 极速稳定。"
        },
        "verification": {
            "ar": "بعد إعادة تشغيل الشاشة، افتح متجر Google Play لتسجيل دخولك، وجرب البحث الصوتي وكتابة الصوت عبر Gboard، وتصفح ملفاتك وفلاشتك عبر تطبيق Files by Google.",
            "en": "After reboot, open Google Play Store to sign in, test voice typing/search via Gboard and Google Speech, and manage your storage and USB drives using Files by Google.",
            "ru": "После перезагрузки откройте Google Play Маркет для входа, проверьте голосовой ввод/поиск через Gboard и управляйте файлами и флешкой через Files by Google.",
            "zh": "车机重启后，打开 Google Play 商店登录账号，测试 Gboard 语音打字与谷歌语音搜索，并使用 Files by Google 管理机身存储与 U 盘。"
        },
        "requires_reboot": True,
        "dynamic_fn": _fmt_gms_dyn
    },
    "uninstall_gms": {
        "emoji": "🚫",
        "title": {
            "ar": "دليل إزالة خدمات جوجل بالكامل",
            "en": "Google Services Complete Removal Manual",
            "ru": "Руководство по полному удалению сервисов Google",
            "zh": "谷歌服务完全卸载与清理说明"
        },
        "overview": {
            "ar": "حذف خدمات جوجل وملفات الصلاحيات وتنظيف الحسابات وإعادة النظام لحالته الأصلية.",
            "en": "Deeply purges Google Play Services, framework permissions, account tokens, and restores stock system state.",
            "ru": "Полностью удаляет сервисы Google, разрешения, токены аккаунтов и возвращает систему в исходное состояние.",
            "zh": "深度清除谷歌服务框架、系统权限与已存凭证，并将系统恢复至出厂状态。"
        },
        "verification": {
            "ar": "تأكد من اختفاء تطبيقات وحزم خدمات جوجل واستقرار واجهة الشاشة.",
            "en": "Verify that Google apps and services are completely removed and the interface is stable.",
            "ru": "Убедитесь, что приложения Google удалены, а интерфейс системы работает стабильно.",
            "zh": "检查并确认所有谷歌应用已完全移除，车机系统运行正常。"
        },
        "requires_reboot": True
    },
    "install_hvac_bar": {
        "emoji": "🚀",
        "title": {
            "ar": "دليل تثبيت شريط التنقل والتكييف المطور (Aero Bar)",
            "en": "Aero Bar Navigation & Climate Dock Manual",
            "ru": "Руководство по установке дока навигации и климата Aero Bar",
            "zh": "Aero Bar 导航与智能空调栏安装说明"
        },
        "overview": {
            "ar": "استبدال شريط التكييف السفلي القديم بشريط Aero Bar الحديث المدمج مع الحفاظ التام على واجهة السيارة الأصلية (Launcher) تعمل بكامل وظائفها؛ يتضمن أزرار التنقل الأساسية (Back / Home / Recents)، وضع السكون وإطفاء الشاشة (Sleep Standby) بالضغط المطول على Home، مدير مهام فائق السرعة، ودرج تطبيقات متكامل مع تحكم ذكي بالتكييف.",
            "en": "Replaces the factory bottom HVAC bar with the modern Aero Bar while keeping the factory OEM launcher completely active; featuring hardware navigation (Back, Home, Recents), Screen Sleep Mode via Long-Press on Home, rapid task switcher, full apps drawer, and floating minimal climate controls.",
            "ru": "Заменяет заводскую нижнюю панель климата на современный док Aero Bar с сохранением заводского лаунчера; содержит кнопки навигации, режим сна экрана при удержании Home, умный переключатель задач и плавающий климат.",
            "zh": "用现代化 Aero Bar 取代原厂底部空调栏，同时保持原厂桌面正常运作；提供原生导航键、长按 Home 键熄屏睡眠（Sleep Standby）、极速多任务切换、完整应用抽屉以及悬浮式空调控制。"
        },
        "verification": {
            "ar": "بعد إعادة تشغيل الشاشة، سيعمل شريط Aero Bar تلقائياً في أسفل الشاشة مع بقاء واجهة السيارة تعمل بشكل طبيعي، مع إمكانية إطفاء الشاشة ووضعها في السكون عبر الضغط المطول على زر الرئيسية (Home).",
            "en": "After reboot, Aero Bar will run persistently at the bottom with the factory launcher intact, and long-pressing Home will put the screen into Sleep / Standby mode.",
            "ru": "После перезагрузки док Aero Bar запустится автоматически внизу экрана при сохранении штатного лаунчера, а долгое нажатие Home переведет экран в режим сна.",
            "zh": "车机重启后，Aero Bar 将在底部常驻自启，原厂桌面保持正常运行，长按主页键（Home）可使屏幕进入睡眠熄屏状态。"
        },
        "requires_reboot": True
    },
    "quick_setup": {
        "emoji": "⚡",
        "title": {
            "ar": "دليل فلاشة الإعداد السريع الشامل (Aero Quick Setup)",
            "en": "Aero Quick Setup Master Provisioning Manual",
            "ru": "Руководство по быстрой комплексной настройке Aero",
            "zh": "Aero 极速全功能初始化配置指南"
        },
        "overview": {
            "ar": "تثبيت شامل وسريع يدمج شريط Aero Bar المطور وحزمة خدمات Google Play الكاملة (مع كافة التطبيقات الأساسية)، وإعادة تشغيل الشاشة والبدء الفوري لشريط التنقل.",
            "en": "Fast comprehensive provisioning combining the enhanced Aero Bar dock and full Google Play Services suite (Chrome, Gboard, Maps, Files, Speech, Search), with automatic reboot and immediate post-boot Aero Bar launch.",
            "ru": "Быстрая комплексная настройка: док Aero Bar и полный пакет сервисов Google (Chrome, Gboard, Maps, Files, Speech, Search) с автоматической перезагрузкой и автозапуском.",
            "zh": "一键全功能极速初始化：集成 Aero Bar 智能底栏与全套谷歌服务（包含 Chrome、Gboard、Maps、Files、Speech、Search），并在自动重启后启动 Aero Bar。"
        },
        "verification": {
            "ar": "بعد إعادة التشغيل، ستعمل خدمات Google ومتجر Play بالكامل وسيفتح شريط Aero Bar تلقائياً في الأسفل.",
            "en": "After reboot, Google Services and Play Store will be fully operational, and Aero Bar will run automatically at the bottom.",
            "ru": "После перезагрузки сервисы Google и Play Маркет будут полностью активны, а Aero Bar запустится автоматически внизу экрана.",
            "zh": "车机重启后，谷歌全套服务与 Play 商店将完整就绪，Aero Bar 底栏自动启动。"
        },
        "requires_reboot": True
    },
    "restore_hvac_bar": {
        "emoji": "🔄",
        "title": {
            "ar": "دليل استعادة شريط المصنع الأصلي",
            "en": "Restore Factory Stock Bar Manual",
            "ru": "Руководство по восстановлению заводской панели",
            "zh": "恢复原厂状态栏指南"
        },
        "overview": {
            "ar": "استعادة شريط النظام والوكالة الأصلي 100% بدون أزرار التنقل الإضافية، وإعادة تطبيق SystemUI الرسمي كما استلمت السيارة.",
            "en": "Restores the untouched factory original dealership interface without extra navigation buttons, reinstating official 100% stock SystemUI.",
            "ru": "Полный откат к оригинальной заводской панели без дополнительных кнопок навигации и восстановление официального SystemUI.",
            "zh": "完全恢复原厂未修改状态栏界面（无额外导航按键），重新部署 100% 官方原始 SystemUI。"
        },
        "verification": {
            "ar": "بعد إعادة تشغيل الشاشة، سيعود شريط المصنع الأصلي كما استلمت السيارة من الوكالة بدون أزرار التنقل الإضافية.",
            "en": "After reboot, the original factory stock bar without extra navigation buttons will be fully restored at the bottom of the screen.",
            "ru": "После перезагрузки вернется оригинальная заводская панель без дополнительных кнопок навигации.",
            "zh": "车机重启后，屏幕底部将完全恢复东风官方出厂原始状态栏界面（无额外导航按键）。"
        },
        "requires_reboot": True
    },
    "disable_launcher": {
        "emoji": "🔒",
        "title": {
            "ar": "دليل تعطيل لانشر المصنع الأصلي",
            "en": "Freeze Factory Launcher Manual",
            "ru": "Руководство по отключению заводского лаунчера",
            "zh": "停用原厂默认桌面说明"
        },
        "overview": {
            "ar": "تجميد لانشر الوكالة com.qinggan.app.launcher لتسليم الشاشة بالكامل للانشر الجديد المفضل لديك.",
            "en": "Freezes the factory OEM launcher (com.qinggan.app.launcher) to enable custom home launchers.",
            "ru": "Замораживает заводской лаунчер для передачи управления стороннему лаунчеру.",
            "zh": "停用原厂主屏应用 (com.qinggan.app.launcher)，将桌面完全交由第三方桌面托管。"
        },
        "verification": {
            "ar": "اضغط زر Home أو ابدأ التشغيل وتأكد من فتح اللانشر البديل مباشرة.",
            "en": "Press the Home button to verify your custom launcher responds immediately.",
            "ru": "Нажмите кнопку Домой, чтобы убедиться в работе нового лаунчера.",
            "zh": "按下 Home 键，确认车机直接进入您自定义的桌面应用。"
        },
        "requires_reboot": False
    },
    "enable_launcher": {
        "emoji": "✅",
        "title": {
            "ar": "دليل إعادة تفعيل لانشر المصنع الأصلي",
            "en": "Restore Factory Launcher Manual",
            "ru": "Руководство по включению заводского лаунчера",
            "zh": "重新启用原厂默认桌面说明"
        },
        "overview": {
            "ar": "إلغاء تجميد لانشر الوكالة الأصلي واستعادة الشاشة الرئيسية الافتراضية للسيارة.",
            "en": "Unfreezes stock Dongfeng launcher and restores default OEM factory home activity.",
            "ru": "Размораживает оригинальный заводской лаунчер Dongfeng и возвращает его в работу.",
            "zh": "解除原厂桌面应用的停用状态，重新将原厂界面设为默认主页。"
        },
        "verification": {
            "ar": "اضغط زر Home وتأكد من ظهور واجهة المصنع الأصلية لشاشة السيارة.",
            "en": "Press Home to confirm the stock factory interface is displayed.",
            "ru": "Нажмите кнопку Домой, чтобы проверить работу заводского интерфейса.",
            "zh": "按下 Home 键，确认车机已回到原厂主界面。"
        },
        "requires_reboot": False
    },
    "reboot_screen": {
        "emoji": "🔄",
        "title": {
            "ar": "دليل إعادة تشغيل شاشة الترفيه",
            "en": "Restart Infotainment Screen Manual",
            "ru": "Руководство по перезагрузке экрана",
            "zh": "中控车机屏幕重启说明"
        },
        "overview": {
            "ar": "إصدار أمر إعادة تشغيل برمجي فوري لتفريغ الذاكرة المؤقتة وحل أي تهنيج في الشاشة دون إطفاء السيارة.",
            "en": "Issues a clean software restart command to flush volatile memory and solve system stutters.",
            "ru": "Выполняет программную перезагрузку для очистки оперативной памяти и устранения зависаний.",
            "zh": "发送软重启指令清理运行内存并解决车机卡顿问题。"
        },
        "verification": {
            "ar": "ستبدأ الشاشة في إعادة التشغيل تلقائياً وتعود للعمل بشكل سلس.",
            "en": "The screen will reboot and restart smoothly.",
            "ru": "Экран автоматически перезагрузится и вернется в нормальное состояние.",
            "zh": "中控屏将自动重启并流畅恢复就绪。"
        },
        "requires_reboot": True
    },
    "factory_reset": {
        "emoji": "⚠️",
        "title": {
            "ar": "دليل استعادة ضبط المصنع وتصفير النظام التام",
            "en": "Deep Zero-Trace Factory Purge Manual",
            "ru": "Руководство по полному сбросу к заводским настройкам",
            "zh": "深度恢复出厂设置与系统重置指南"
        },
        "overview": {
            "ar": "تصفير كامل لبارتشن البيانات /data ومسح التعديلات وتصفير البلوتوث واستشفاء تطبيقات الوكالة الأصلية.",
            "en": "Complete wipe of /data partition, clears crash logs, resets Bluetooth, and heals missing factory apps.",
            "ru": "Полная очистка раздела /data, сброс Bluetooth и автовосстановление заводских приложений.",
            "zh": "彻底重置 /data 数据分区，清理故障记录，重置蓝牙并自动修复缺失的原厂应用。"
        },
        "verification": {
            "ar": "ستفتح الشاشة على حالة المصنع الأولى تماماً كما خرجت من المعرض.",
            "en": "The infotainment screen will boot into pristine factory condition.",
            "ru": "Экран запустится в первозданном заводском состоянии.",
            "zh": "中控屏将恢复至出厂时的初始状态。"
        },
        "requires_reboot": True
    },
    "fetch_logs": {
        "emoji": "📋",
        "title": {
            "ar": "دليل سحب سجلات النظام والأعطال",
            "en": "System Diagnostic Logs Extraction Manual",
            "ru": "Руководство по сбору системных логов",
            "zh": "系统运行与故障日志提取说明"
        },
        "overview": {
            "ar": "سحب سجلات logcat وتقارير الأعطال وقوائم التطبيقات وحفظها في مجلد Logs على الفلاشة.",
            "en": "Dumps logcat, crash traces, ANR reports, and installed package inventories to USB:/Logs/.",
            "ru": "Сохраняет logcat, отчеты о сбоях и списки установленных программ в USB:/Logs/.",
            "zh": "将车机运行日志 (logcat)、崩溃记录及已安装应用清单提取至 U 盘的 USB:/Logs/ 目录。"
        },
        "verification": {
            "ar": "افحص الفلاشة على الكمبيوتر وتأكد من وجود مجلد Logs وبداخله ملفات السجلات.",
            "en": "Check the USB on your computer to view the generated logs inside Logs folder.",
            "ru": "Проверьте флешку на компьютере: в папке Logs должны появиться файлы логов.",
            "zh": "在电脑上打开 U 盘，确认 Logs 文件夹下已成功生成相关日志。"
        },
        "requires_reboot": False
    },
    "vehicle_tweaks": {
        "emoji": "⚡",
        "title": {
            "ar": "دليل تطبيق تعديلات كمبيوتر السيارة (CAN-Bus)",
            "en": "Vehicle CAN-Bus Tweaks Manual",
            "ru": "Руководство по настройке функций автомобиля (CAN-Bus)",
            "zh": "车辆 CAN-Bus 高级调教配置说明"
        },
        "overview": {
            "ar": "تطبيق التعديلات المختارة على كمبيوتر السيارة (إلغاء قفل السرعة، مزامنة الثيمات، أزرار الطارة).",
            "en": "Dispatches selected modifications to vehicle IPC controller (speed lock bypass, day/night sync, etc.).",
            "ru": "Применяет выбранные модификации к блокам управления автомобиля (снятие блокировки скорости и др.).",
            "zh": "向车辆仪表与车机通信控制器 (CAN-Bus) 写入所选高级设置（行车解除视频限制等）。"
        },
        "verification": {
            "ar": "جرب الميزات في السيارة للتأكد من تفعيلها بنجاح.",
            "en": "Test vehicle functionality to confirm the tweaks are active.",
            "ru": "Проверьте работу функций в автомобиле, чтобы убедиться в их активации.",
            "zh": "在车内测试并验证相关设定是否已按预期生效。"
        },
        "requires_reboot": False,
        "dynamic_fn": _fmt_tweaks_dyn
    }
}


# ============================================================================
# SECTION 3: UNIFIED MANUAL GENERATOR ENGINE (SINGLE & COMPOSITE)
# ============================================================================

def _estimate_execution_time(actions: list, lang: str) -> str:
    """
    Calculates realistic execution duration based on actual Dongfeng head unit performance:
    - Partition Cloning (Backup / Restore): 5-15 minutes (depends on data size).
    - Factory Reset: 30 seconds to 2 minutes (depends on data size).
    - Large batch installations (GMS + many apps): 1-2 minutes max.
    - Standard installations (GMS alone or apps): ~1 minute.
    - Diagnostic logs dump (Fetch Logs): 30 seconds to 1 minute.
    - Quick actions (Tweaks, Open App/Settings, Uninstalls, Launcher, Reboot): 10-20 seconds.
    """
    p_ids = [act.get("id") for act in actions]

    # 1. Heavy partition operations (Backup / Restore)
    if any(pid in ("backup", "restore") for pid in p_ids):
        if lang == "ar":
            return "من 5 دقائق إلى 15 دقيقة تقريباً (حسب حجم البيانات)"
        elif lang == "ru":
            return "от 5 до 15 минут (в зависимости от объема данных)"
        elif lang == "zh":
            return "约 5 至 15 分钟（取决于数据备份体积）"
        else:
            return "approx. 5 to 15 minutes (depending on data volume)"

    # 2. Factory reset
    if "factory_reset" in p_ids:
        if lang == "ar":
            return "من 30 ثانية إلى دقيقتين تقريباً (حسب حجم البيانات)"
        elif lang == "ru":
            return "от 30 секунд до 2 минут (в зависимости от объема данных)"
        elif lang == "zh":
            return "约 30 秒至 2 分钟（取决于数据体积）"
        else:
            return "approx. 30 seconds to 2 minutes (depending on data volume)"

    # 3. Installations (GMS / Apps)
    has_gms = ("install_gms" in p_ids)
    app_count = 0
    for act in actions:
        if act.get("id") == "install_apps":
            app_count += len(act.get("kwargs", {}).get("selected_apks", []))

    # Very large composite installation (GMS + 3 or more user apps, or 6+ apps)
    if (has_gms and app_count >= 3) or (app_count >= 6):
        if lang == "ar":
            return "من دقيقة إلى دقيقتين بالكتير"
        elif lang == "ru":
            return "от 1 до 2 минут максимум"
        elif lang == "zh":
            return "最多 1 至 2 分钟"
        else:
            return "approx. 1 to 2 minutes max"

    # Standard installation (GMS alone or regular apps)
    if has_gms or app_count > 0:
        if lang == "ar":
            return "خلال دقيقة واحدة تقريباً"
        elif lang == "ru":
            return "около 1 минуты"
        elif lang == "zh":
            return "约 1 分钟左右"
        else:
            return "approx. 1 minute"

    # 4. Uninstall GMS or Diagnostic Logs
    if "uninstall_gms" in p_ids or "fetch_logs" in p_ids:
        if lang == "ar":
            return "من 30 ثانية إلى دقيقة واحدة تقريباً"
        elif lang == "ru":
            return "от 30 секунд до 1 минуты"
        elif lang == "zh":
            return "约 30 秒至 1 分钟左右"
        else:
            return "approx. 30 seconds to 1 minute"

    # 5. Quick Actions (Tweaks, Open Apps/Settings, Uninstalls, Launcher, Reboot)
    if lang == "ar":
        return "خلال ثوانٍ معدودة (من 10 إلى 20 ثانية)"
    elif lang == "ru":
        return "в течение 10–20 секунд"
    elif lang == "zh":
        return "数秒之内 (约 10 至 20 秒)"
    else:
        return "within seconds (10 to 20 seconds)"


def _build_dynamic_execution_roadmap(actions: list, lang: str, tpl: dict) -> Tuple[str, str]:
    """
    Constructs a highly detailed, dynamic execution roadmap for Step 1 (Ignition)
    and Step 4 (Finishing & Multi-Stage Execution Journey).

    - Step 1 (Ignition):
      * If any action is 'vehicle_tweaks' (requires CAN-Bus communication with BCM):
        Instructs user to press engine start button TWICE without brake (full ON mode).
      * Otherwise:
        Instructs user to press ONCE (ACC mode) to power screen only.

    - Step 4 (Execution Journey & Reboot Roadmap):
      * Accurately calculates total reboots (0, 1, or 2).
      * If 0 reboots: Explains direct execution, chime signal, immediate safe USB unplug.
      * If 1 reboot: Explains preparation, primary stage (reset or install), single reboot, post-boot config, safe unplug.
      * If 2 reboots: Explains Stage 0 (Backup), Stage 1 (Reset + Reboot #1), Stage 2 (Installs + Reboot #2), Stage 3 (Post-Boot Setup), safe unplug.
    """
    p_ids = [act.get("id") for act in actions]

    # 1. Step 1: Dynamic Ignition Requirement
    has_tweaks = ("vehicle_tweaks" in p_ids)
    step_start = tpl.get("step_start_car_tweaks") if has_tweaks else tpl.get("step_start_car")

    # 2. Stage & Feature Analysis
    has_quick_setup = ("quick_setup" in p_ids)
    has_backup = ("backup" in p_ids)
    has_reset = ("factory_reset" in p_ids)
    has_gms = ("install_gms" in p_ids) or has_quick_setup
    has_hvac = any(pid in ("install_hvac_bar", "restore_hvac_bar") for pid in p_ids) or has_quick_setup
    has_uninst_gms = ("uninstall_gms" in p_ids)
    has_freeze_launcher = ("disable_launcher" in p_ids)
    has_fetch_logs = ("fetch_logs" in p_ids)
    has_standalone_reboot = ("reboot_screen" in p_ids)

    has_system_apps = False
    for act in actions:
        if act.get("id") == "install_apps":
            selected = act.get("kwargs", {}).get("selected_apks", [])
            if any(isinstance(a, dict) and a.get("install_target") == "system" for a in selected):
                has_system_apps = True
                break

    has_stage2_sys_mods = (has_gms or has_hvac or has_uninst_gms or has_system_apps or has_quick_setup)

    # Determine auto-launch target if configured
    launch_app_name = None
    for act in actions:
        kw = act.get("kwargs", {})
        if kw.get("auto_launch_package") or kw.get("package_name") or kw.get("clean_pkg"):
            launch_app_name = kw.get("display_label") or kw.get("app_name") or kw.get("auto_launch_package") or kw.get("clean_pkg")
            break
    if not launch_app_name and any(act.get("id") == "open_settings" for act in actions):
        launch_app_name = "إعدادات أندرويد الأصلية" if lang == "ar" else ("Android Settings" if lang == "en" else ("Настройки Android" if lang == "ru" else "系统原生设置"))

    # Determine exact number of reboots
    has_quick_setup_wipe = any(act.get("id") == "quick_setup" and act.get("kwargs", {}).get("wipe_factory_data") for act in actions)
    if has_quick_setup:
        total_reboots = 2 if has_quick_setup_wipe else 1
    elif has_reset and has_stage2_sys_mods:
        total_reboots = 2
    elif has_reset or has_stage2_sys_mods or has_standalone_reboot:
        total_reboots = 1
    else:
        total_reboots = 0

    # 3. Construct Dynamic Step 4 Narrative
    if lang == "ar":
        if total_reboots == 0:
            lines = [
                "نهاية العملية (تنفيذ فوري مباشر — 0 إعادة تشغيل):",
                "   • مسار التنفيذ: ستُنفذ العمليات المطلوبة مباشرة في الخلفية وسيكتمل كل شيء دون الحاجة لإعادة تشغيل الشاشة.",
                "   • إشارة الانتهاء: ستسمع صوت التنبيه المألوف من سماعات السيارة فور اكتمال كافة العمليات بنجاح.",
                "   • شرط نزع الفلاشة الآمن: يمكنك إزالة الفلاشة بأمان فوراً بعد سماع صوت التنبيه والبدء في استخدام الميزات الجديدة (الفلاشة مؤمنة بالكامل ضد التكرار)."
            ]
        elif total_reboots == 1:
            lines = [
                "خارطة مراحل التنفيذ وإعادة التشغيل (ريستارت مرة واحدة — 1 فقط):"
            ]
            if has_quick_setup:
                lines.append("   • مرحلة التثبيت والتعديل: تثبيت شريط Aero Bar وحزمة خدمات وتطبيقات Google في الخلفية، ثم تقوم الشاشة بعمل إعادة التشغيل الوحيدة (ريستارت #1) لدمج وتفعيل ملفات النظام.")
                lines.append("     ⚠️ تحذير هام: اترك الفلاشة موصولة طوال فترة انطفاء الشاشة وإقلاعها.")
            elif has_backup:
                lines.append("   • مرحلة النسخ الاحتياطي: سحب كامل للبيانات والإعدادات إلى USB:/Backup/ وحفظها بأمان (بدون ريستارت).")
            elif has_reset:
                lines.append("   • مرحلة تصفير المصنع: تطهير ومسح كامل لبارتشن /data، ثم تقوم الشاشة بعمل إعادة التشغيل الوحيدة (ريستارت #1) لتهيئة الروم النظيف.")
                lines.append("     ⚠️ تحذير هام: اترك الفلاشة موصولة طوال فترة انطفاء الشاشة وإقلاعها.")
            elif has_stage2_sys_mods:
                lines.append("   • مرحلة التثبيت والتعديل: تثبيت الحزم وملفات النظام في الخلفية، ثم تقوم الشاشة بعمل إعادة التشغيل الوحيدة (ريستارت #1) لدمج وتفعيل ملفات النظام.")
                lines.append("     ⚠️ تحذير هام: اترك الفلاشة موصولة طوال فترة انطفاء الشاشة وإقلاعها.")
            elif has_standalone_reboot:
                lines.append("   • مرحلة التنفيذ وإعادة التشغيل: تنفيذ العمليات المطلوبة ثم إعادة تشغيل برمجية لتفريغ الذاكرة وتجديد نشاط النظام.")

            post_steps = []
            if has_quick_setup:
                post_steps.append("تشغيل شريط Aero Bar تلقائياً")
                post_steps.append("تفعيل وضبط كيبورد Gboard افتراضياً")
            else:
                if has_gms: post_steps.append("تفعيل وضبط كيبورد Gboard افتراضياً")
                if has_freeze_launcher: post_steps.append("تجميد لانشر الوكالة الصيني")
                if has_fetch_logs: post_steps.append("سحب سجلات الفحص والتشخيص إلى USB:/Logs/")
                if launch_app_name: post_steps.append(f"فتح تطبيق {launch_app_name} تلقائياً")

            if post_steps:
                lines.append(f"   • ما بعد الإقلاع: بعد اكتمال فتح الشاشة، يتم إنهاء الضبط تلقائياً ({' + '.join(post_steps)}).")

            if has_quick_setup:
                lines.append("   • شرط نزع الفلاشة الآمن: لا تنزع الفلاشة أبداً أثناء انطفاء الشاشة أو ظهور لوجو السيارة. انزع الفلاشة فقط بعد اكتمال إقلاع النظام بالكامل وظهور شريط Aero Bar واستقراره أمامك على الشاشة (الفلاشة مؤمنة بالكامل ضد التكرار).")
            else:
                lines.append("   • شرط نزع الفلاشة الآمن: لا تنزع الفلاشة أبداً أثناء انطفاء الشاشة أو ظهور لوجو السيارة. انزع الفلاشة فقط بعد اكتمال إقلاع النظام بالكامل وظهور التطبيق النهائي أو اللانشر أمامك على الشاشة (الفلاشة مؤمنة بالكامل ضد التكرار).")
        else:  # total_reboots == 2
            lines = [
                "خارطة مراحل التنفيذ وإعادة التشغيل (تنفيذ متعدد المراحل — ريستارت مرتين بالتمام):"
            ]
            if has_quick_setup:
                lines.append("   • المرحلة 1 (تصفير المصنع والتهيئة): تصفير ومسح كامل لبارتشن /data، ثم تقوم الشاشة بعمل إعادة التشغيل الأولى (#1) لتهيئة الروم النظيف. ⚠️ اترك الفلاشة موصولة ولا تنزعها أبداً أثناء انطفاء الشاشة.")
                lines.append("   • المرحلة 2 (تثبيت المنظومة وحزمة Google): بعد إقلاع الشاشة، يبدأ تلقائياً تثبيت شريط Aero Bar وحزمة خدمات وتطبيقات Google وتفعيل الصلاحيات، ثم تقوم الشاشة بعمل إعادة التشغيل الثانية (#2) لدمج ملفات وصلاحيات النظام. ⚠️ اترك الفلاشة موصولة ولا تنزعها.")
                post_steps = ["تشغيل شريط Aero Bar تلقائياً", "تفعيل وضبط كيبورد Gboard افتراضياً"]
                lines.append(f"   • المرحلة 3 (ما بعد الإقلاع الثاني والتشغيل): بعد اكتمال الإقلاع الثاني، {' و'.join(post_steps)}.")
                lines.append("   • شرط نزع الفلاشة الآمن: اترك الفلاشة موصولة طوال فترات إعادة التشغيل الأولى والثانية. انزع الفلاشة فقط بعد اكتمال إقلاع النظام للمرة الثانية وظهور شريط Aero Bar واستقراره أمامك على الشاشة (الفلاشة مؤمنة بالكامل ضد التكرار).")
            else:
                if has_backup:
                    lines.append("   • المرحلة 0 (النسخ الاحتياطي المسبق): سحب كامل لبيانات النظام والتطبيقات إلى مجلد USB:/Backup/ وحفظها بأمان قبل البدء بأي مسح (بدون ريستارت).")

                lines.append("   • المرحلة 1 (تصفير المصنع والتطهير الشامل): تصفير ومسح بارتشن /data واستعادة روم الوكالة النظيف، ثم تقوم الشاشة بالريستارت الأول (#1) لتهيئة النظام الخام. ⚠️ اترك الفلاشة موصولة ولا تنزعها أبداً أثناء انطفاء الشاشة.")
                lines.append("   • المرحلة 2 (تثبيت الحزم والتعديلات): بعد إقلاع الشاشة، يبدأ تلقائياً تثبيت خدمات جوجل والتطبيقات المختارة وشريط التكييف والتعديلات، ثم تقوم الشاشة بالريستارت الثاني (#2) لدمج ملفات وصلاحيات النظام. ⚠️ اترك الفلاشة موصولة ولا تنزعها.")

                post_steps = []
                if has_gms: post_steps.append("ضبط كيبورد Gboard افتراضياً")
                if has_freeze_launcher: post_steps.append("تجميد لانشر الوكالة")
                if has_fetch_logs: post_steps.append("سحب سجلات الفحص إلى USB:/Logs/")
                if launch_app_name: post_steps.append(f"تشغيل تطبيق {launch_app_name}")

                if post_steps:
                    lines.append(f"   • المرحلة 3 (ما بعد الإقلاع والتهيئة النهائية): بعد اكتمال الإقلاع الثاني، يتولى السكريبت تلقائياً {' ثم '.join(post_steps)} وسماع صوت التنبيه لتأكيد الانتهاء.")
                else:
                    lines.append("   • المرحلة 3 (ما بعد الإقلاع والتهيئة النهائية): بعد اكتمال الإقلاع الثاني، تصدر الشاشة صوت التنبيه لتأكيد جاهزية النظام واستقراره.")

                lines.append("   • شرط نزع الفلاشة الآمن: اترك الفلاشة موصولة طوال فترات إعادة التشغيل الأولى والثانية. انزع الفلاشة فقط بعد اكتمال إقلاع النظام للمرة الثانية وظهور التطبيق النهائي أو اللانشر الجديد واستقراره أمامك على الشاشة (الفلاشة مؤمنة بالكامل ضد التكرار).")

    elif lang == "ru":
        if total_reboots == 0:
            lines = [
                "Завершение (Прямое фоновое выполнение — 0 перезагрузок):",
                "   • Ход выполнения: Задачи будут выполнены непосредственно в фоновом режиме без перезагрузки экрана.",
                "   • Сигнал завершения: Звуковой сигнал автомобиля подтвердит успешное завершение всех операций.",
                "   • Безопасное извлечение USB: Вы можете безопасно извлечь флешку сразу после звукового сигнала (защита от повторного запуска активна)."
            ]
        elif total_reboots == 1:
            lines = [
                "План выполнения и перезагрузка (1 перезагрузка экрана):"
            ]
            if has_quick_setup:
                lines.append("   • Развертывание и интеграция: Установка дока Aero Bar и сервисов Google в фоне, затем единственная перезагрузка (#1) для интеграции файлов.")
                lines.append("     ⚠️ Внимание: НЕ ИЗВЛЕКАЙТЕ флешку во время отключения и загрузки экрана.")
            elif has_backup:
                lines.append("   • Резервное копирование: Полное сохранение данных и настроек в USB:/Backup/ (без перезагрузки).")
            elif has_reset:
                lines.append("   • Заводской сброс: Очистка раздела /data и выполнение единственной перезагрузки (#1) для инициализации чистого ROM.")
                lines.append("     ⚠️ Внимание: НЕ ИЗВЛЕКАЙТЕ флешку во время отключения и загрузки экрана.")
            elif has_stage2_sys_mods:
                lines.append("   • Установка пакетов и модов: Развертывание системных компонентов в фоне, затем единственная перезагрузка (#1) для интеграции файлов.")
                lines.append("     ⚠️ Внимание: НЕ ИЗВЛЕКАЙТЕ флешку во время отключения и загрузки экрана.")
            elif has_standalone_reboot:
                lines.append("   • Выполнение и перезагрузка: Выполнение задач и программная перезагрузка для очистки оперативной памяти.")

            post_steps = []
            if has_quick_setup:
                post_steps.append("автозапуск Aero Bar")
                post_steps.append("настройка Gboard")
            else:
                if has_gms: post_steps.append("настройка Gboard")
                if has_freeze_launcher: post_steps.append("отключение заводского лаунчера")
                if has_fetch_logs: post_steps.append("экспорт логов в USB:/Logs/")
                if launch_app_name: post_steps.append(f"автозапуск {launch_app_name}")

            if post_steps:
                lines.append(f"   • Пост-загрузка: После запуска экрана автоматически завершается настройка ({', '.join(post_steps)}).")

            if has_quick_setup:
                lines.append("   • Безопасное извлечение USB: Ни в коем случае не извлекайте флешку во время черного экрана или логотипа авто. Извлекайте только после полной загрузки системы и появления Aero Bar (флешка защищена от повтора).")
            else:
                lines.append("   • Безопасное извлечение USB: Ни в коем случае не извлекайте флешку во время черного экрана или логотипа авто. Извлекайте только после полной загрузки системы и появления целевого приложения или лаунчера (флешка защищена от повтора).")
        else:  # total_reboots == 2
            lines = [
                "План выполнения и двухэтапная перезагрузка (ровно 2 перезагрузки):"
            ]
            if has_quick_setup:
                lines.append("   • Этап 1 (Заводской сброс): Очистка раздела /data и первая перезагрузка (#1) для инициализации чистого заводского ROM. ⚠️ НЕ ИЗВЛЕКАЙТЕ флешку.")
                lines.append("   • Этап 2 (Развертывание Aero Bar и сервисов Google): После загрузки экрана устанавливается Aero Bar и сервисы Google, затем вторая перезагрузка (#2) для интеграции системы. ⚠️ НЕ ИЗВЛЕКАЙТЕ флешку.")
                post_steps = ["автозапуск Aero Bar", "настройка Gboard"]
                lines.append(f"   • Этап 3 (Пост-загрузка и запуск): После второй перезагрузки автоматически выполняется {', затем '.join(post_steps)}.")
                lines.append("   • Безопасное извлечение USB: Держите флешку подключенной на протяжении обеих перезагрузок. Извлекайте только после завершения второй перезагрузки и отображения Aero Bar (защита от повтора включена).")
            else:
                if has_backup:
                    lines.append("   • Этап 0 (Резервное копирование): Сохранение данных системы и приложений в USB:/Backup/ перед очисткой (без перезагрузки).")
                lines.append("   • Этап 1 (Заводской сброс): Очистка раздела /data и первая перезагрузка (#1) для инициализации чистого заводского ROM. ⚠️ НЕ ИЗВЛЕКАЙТЕ флешку.")
                lines.append("   • Этап 2 (Установка пакетов и модов): После загрузки экрана устанавливаются сервисы Google, приложения и моды, затем вторая перезагрузка (#2) для интеграции системы. ⚠️ НЕ ИЗВЛЕКАЙТЕ флешку.")

                post_steps = []
                if has_gms: post_steps.append("активация клавиатуры Gboard")
                if has_freeze_launcher: post_steps.append("заморозка штатного лаунчера")
                if has_fetch_logs: post_steps.append("сохранение отчетов в USB:/Logs/")
                if launch_app_name: post_steps.append(f"запуск {launch_app_name}")

                if post_steps:
                    lines.append(f"   • Этап 3 (Пост-загрузка и финализация): После второй перезагрузки автоматически выполняется {', затем '.join(post_steps)} со звуковым сигналом.")
                else:
                    lines.append("   • Этап 3 (Пост-загрузка и финализация): После второй перезагрузки прозвучит звуковой сигнал подтверждения готовности системы.")

                lines.append("   • Безопасное извлечение USB: Держите флешку подключенной на протяжении обеих перезагрузок. Извлекайте только после завершения второй перезагрузки и отображения нового лаунчера или приложения (защита от повтора включена).")

    elif lang == "zh":
        if total_reboots == 0:
            lines = [
                "执行完成 (后台直接执行 — 0 次重启):",
                "   • 执行流程: 所选任务将在后台直接全自动执行，车机屏幕无需重启。",
                "   • 完成提示: 全部操作顺利完成后，车机将发出提示音。",
                "   • 拔出规则: 听到提示音后即可安全拔出 U 盘，立即体验新功能（系统已具备智能防重复锁）。"
            ]
        elif total_reboots == 1:
            lines = [
                "执行阶段规划与重启说明 (仅重启 1 次):"
            ]
            if has_quick_setup:
                lines.append("   • 部署与修改阶段: 在后台部署 Aero Bar 智能底栏与全套谷歌服务，随后执行唯一的 1 次重启 (#1) 整合系统组件。")
                lines.append("     ⚠️ 警告: 屏幕黑屏与重启期间请全程保持 U 盘插入。")
            elif has_backup:
                lines.append("   • 备份阶段: 完整备份系统数据与设置至 USB:/Backup/（不重启）。")
            elif has_reset:
                lines.append("   • 恢复出厂阶段: 清空 /data 分区并执行唯一的 1 次重启 (#1) 以初始化干净的官方 ROM。")
                lines.append("     ⚠️ 警告: 屏幕黑屏与重启期间请全程保持 U 盘插入。")
            elif has_stage2_sys_mods:
                lines.append("   • 部署与修改阶段: 在后台部署系统组件与应用，随后执行唯一的 1 次重启 (#1) 整合底层文件。")
                lines.append("     ⚠️ 警告: 屏幕黑屏与重启期间请全程保持 U 盘插入。")
            elif has_standalone_reboot:
                lines.append("   • 执行与重启: 执行任务后自动软重启清理系统运存。")

            post_steps = []
            if has_quick_setup:
                post_steps.append("自动启动 Aero Bar")
                post_steps.append("配置 Gboard 默认输入法")
            else:
                if has_gms: post_steps.append("配置 Gboard 默认输入法")
                if has_freeze_launcher: post_steps.append("停用原厂桌面")
                if has_fetch_logs: post_steps.append("提取诊断日志至 USB:/Logs/")
                if launch_app_name: post_steps.append(f"自动启动 {launch_app_name}")

            if post_steps:
                lines.append(f"   • 开机收尾: 车机完全启动后自动完成配置 ({' + '.join(post_steps)})。")

            if has_quick_setup:
                lines.append("   • 安全拔盘条件: 黑屏或显示车标期间严禁拔出 U 盘！仅在系统彻底启动完毕、Aero Bar 底栏稳定显示后方可拔出 U 盘（智能防重复锁已启用）。")
            else:
                lines.append("   • 安全拔盘条件: 黑屏或显示车标期间严禁拔出 U 盘！仅在系统彻底启动完毕、最终应用或新桌面稳定显示后方可拔出 U 盘（智能防重复锁已启用）。")
        else:  # total_reboots == 2
            lines = [
                "多阶段执行规划与重启说明 (严格执行 2 次连续重启):"
            ]
            if has_quick_setup:
                lines.append("   • 阶段 1 (深度恢复出厂): 格式化 /data 分区并执行第 1 次重启 (#1) 初始化干净系统。⚠️ 黑屏期间切勿拔出 U 盘。")
                lines.append("   • 阶段 2 (部署 Aero Bar 与全套谷歌服务): 开机后自动部署底栏与谷歌组件，随后执行第 2 次重启 (#2) 整合权限。⚠️ 切勿拔出 U 盘。")
                post_steps = ["自动启动 Aero Bar", "配置 Gboard 默认输入法"]
                lines.append(f"   • 阶段 3 (开机后置配置与启动): 第二次开机后自动执行 {' 并 '.join(post_steps)}。")
                lines.append("   • 安全拔盘条件: 在两次重启全过程中请全程保持 U 盘插入。仅在第二次重启彻底就绪、Aero Bar 底栏完全显现并稳定后方可安全拔出 U 盘（智能防重复锁已生效）。")
            else:
                if has_backup:
                    lines.append("   • 阶段 0 (前置安全备份): 完整提取系统数据与应用至 USB:/Backup/（不重启）。")
                lines.append("   • 阶段 1 (深度恢复出厂): 格式化 /data 分区并执行第 1 次重启 (#1) 初始化干净系统。⚠️ 黑屏期间切勿拔出 U 盘。")
                lines.append("   • 阶段 2 (系统组件与应用部署): 开机后自动部署谷歌服务、应用与高级设置，随后执行第 2 次重启 (#2) 整合权限。⚠️ 切勿拔出 U 盘。")

                post_steps = []
                if has_gms: post_steps.append("配置 Gboard 默认输入法")
                if has_freeze_launcher: post_steps.append("停用原厂桌面")
                if has_fetch_logs: post_steps.append("提取系统日志至 USB:/Logs/")
                if launch_app_name: post_steps.append(f"自动启动 {launch_app_name}")

                if post_steps:
                    lines.append(f"   • 阶段 3 (开机后置配置与收尾): 第二次开机后自动执行 {' 并 '.join(post_steps)}，发出提示音确认。")
                else:
                    lines.append("   • 阶段 3 (开机后置配置与收尾): 第二次开机就绪后发出提示音确认系统稳定。")

                lines.append("   • 安全拔盘条件: 在两次重启全过程中请全程保持 U 盘插入。仅在第二次重启彻底就绪、最终应用或桌面完全显现并稳定后方可安全拔出 U 盘（智能防重复锁已生效）。")

    else:  # English (default fallback)
        if total_reboots == 0:
            lines = [
                "Completion (Direct Background Execution — 0 Reboots):",
                "   • Execution Flow: Requested operations will execute directly in the background without needing a screen reboot.",
                "   • Completion Signal: You will hear the vehicle's built-in audible chime once all operations have completed successfully.",
                "   • Safe Unplug Rule: You can safely remove the USB drive immediately after hearing the chime (fully protected against repetition)."
            ]
        elif total_reboots == 1:
            lines = [
                "Execution Roadmap & Screen Reboot (Single Reboot — Exactly 1):"
            ]
            if has_quick_setup:
                lines.append("   • Installation & Modifications: Deploys Aero Bar and Google Services suite in the background, then initiates the single Reboot (#1) to integrate system packages.")
                lines.append("     ⚠️ WARNING: KEEP USB DRIVE CONNECTED during screen shutdown and boot.")
            elif has_backup:
                lines.append("   • Pre-Flight Backup: Full extraction of system data and settings to USB:/Backup/ (no reboot).")
            elif has_reset:
                lines.append("   • Factory Purge Stage: Cleans and wipes /data partition, then initiates the single Reboot (#1) to initialize clean ROM.")
                lines.append("     ⚠️ WARNING: KEEP USB DRIVE CONNECTED during screen shutdown and boot.")
            elif has_stage2_sys_mods:
                lines.append("   • Installation & Modifications: Deploys system packages and files in background, then initiates the single Reboot (#1) to integrate system changes.")
                lines.append("     ⚠️ WARNING: KEEP USB DRIVE CONNECTED during screen shutdown and boot.")
            elif has_standalone_reboot:
                lines.append("   • Execution & Reboot: Completes operations and performs a clean reboot to flush RAM.")

            post_steps = []
            if has_quick_setup:
                post_steps.append("auto-launch Aero Bar dock")
                post_steps.append("configure Gboard default IME")
            else:
                if has_gms: post_steps.append("configure Gboard default IME")
                if has_freeze_launcher: post_steps.append("freeze OEM stock launcher")
                if has_fetch_logs: post_steps.append("dump diagnostic logs to USB:/Logs/")
                if launch_app_name: post_steps.append(f"launch {launch_app_name}")

            if post_steps:
                lines.append(f"   • Post-Boot Setup: Once the screen boots up, final configurations complete automatically ({' + '.join(post_steps)}).")

            if has_quick_setup:
                lines.append("   • Safe Unplug Rule: NEVER unplug the USB while the screen is black or showing the car boot logo. Only remove the USB after the system fully boots and Aero Bar appears and stabilizes on screen (fully locked against repetition).")
            else:
                lines.append("   • Safe Unplug Rule: NEVER unplug the USB while the screen is black or showing the car boot logo. Only remove the USB after the system fully boots and the final app or launcher appears and stabilizes on screen (USB is fully locked against repetition).")
        else:  # total_reboots == 2
            lines = [
                "Execution Roadmap & Multi-Stage Reboots (Exactly 2 Consecutive Reboots):"
            ]
            if has_quick_setup:
                lines.append("   • Stage 1 (Factory Purge & Clean ROM): Wipes /data partition and initiates Reboot #1 to initialize pristine OEM ROM. ⚠️ KEEP USB CONNECTED during shutdown.")
                lines.append("   • Stage 2 (Aero Bar & Google Services Deployment): Deploys Aero Bar and Google Services suite, then initiates Reboot #2 to integrate system packages. ⚠️ KEEP USB CONNECTED.")
                post_steps = ["auto-launch Aero Bar dock", "configure Gboard default IME"]
                lines.append(f"   • Stage 3 (Post-Boot Launch): After the second reboot completes, final setup completes automatically ({' and '.join(post_steps)}).")
                lines.append("   • Safe Unplug Rule: Keep the USB plugged in through BOTH reboots. Only remove the USB after the second reboot completes and Aero Bar stabilizes on screen (fully locked against repetition).")
            else:
                if has_backup:
                    lines.append("   • Stage 0 (Pre-Flight Backup): Full extraction of system data and apps to USB:/Backup/ before wiping (no reboot).")
                lines.append("   • Stage 1 (Factory Purge & Clean ROM): Wipes /data partition and initiates Reboot #1 to initialize pristine OEM ROM. ⚠️ KEEP USB CONNECTED during shutdown.")
                lines.append("   • Stage 2 (System Packages & Apps Deployment): Automatically installs Google Services, APKs, and mods, then initiates Reboot #2 to integrate system packages. ⚠️ KEEP USB CONNECTED.")

                post_steps = []
                if has_gms: post_steps.append("configure Gboard default IME")
                if has_freeze_launcher: post_steps.append("freeze OEM stock launcher")
                if has_fetch_logs: post_steps.append("dump diagnostic logs to USB:/Logs/")
                if launch_app_name: post_steps.append(f"launch {launch_app_name}")

                if post_steps:
                    lines.append(f"   • Stage 3 (Post-Boot Setup & Finalization): After the second reboot completes, the system automatically executes {' then '.join(post_steps)} and chimes to confirm.")
                else:
                    lines.append("   • Stage 3 (Post-Boot Setup & Finalization): After the second reboot completes, an audible chime confirms the system is fully ready.")

                lines.append("   • Safe Unplug Rule: Keep the USB plugged in through BOTH reboots. Only remove the USB after the second reboot completes and the final app or launcher stabilizes on screen (fully locked against repetition).")

    step_finish = "\n".join(lines)
    return step_start, step_finish


def generate_unified_manual(actions: list, lang: str = None) -> str:
    """
    Unified engine that generates complete, localized manuals for either:
    - A single payload action
    - A composite queue of multiple payload actions (The Basket)
    """
    if not lang:
        lang = get_i18n().current_lang or "ar"
    if lang not in COMMON_TEMPLATES:
        lang = "ar"

    tpl = COMMON_TEMPLATES[lang]
    banner = get_signature_banner(lang)

    if not actions:
        content = f"Aero Suite Unified Payload\n\n{banner}"
        return _apply_arabic_rtl_formatting(content) if lang == "ar" else content

    is_single = (len(actions) == 1)

    # Normalize actions so each entry is guaranteed to be a dict {"id": ..., "kwargs": ...}
    normalized_actions = []
    for a in actions:
        if isinstance(a, str):
            normalized_actions.append({"id": a, "kwargs": {}})
        elif isinstance(a, dict):
            normalized_actions.append(a)
        else:
            p_id = getattr(a, "action_type", str(a))
            kw = getattr(a, "config", {})
            normalized_actions.append({"id": p_id, "kwargs": kw})
    # Sort strictly by vehicle execution sequence so manual matches custom_rep.sh 1:1
    normalized_actions.sort(key=lambda act: ACTION_EXECUTION_ORDER.get(act.get("id"), 50))
    actions = normalized_actions

    # 1. Header & Title Block
    if is_single:
        act = actions[0]
        p_id = act.get("id")
        spec = FEATURE_SPECS.get(p_id, {})
        emoji = spec.get("emoji", "📋")
        title_text = spec.get("title", {}).get(lang, f"Aero Suite Manual ({p_id})")
        header = f"{emoji} {title_text}\n{tpl['target_vehicle']}\n"
    else:
        cnt_str = _to_indic(len(actions)) if lang == "ar" else str(len(actions))
        comp_title = tpl["composite_title"].format(count=cnt_str)
        header = f"{comp_title}\n{tpl['target_vehicle']}\n"

    # 2. Section 1: Overview & Operations Manifest
    overview_lines = [
        "============================================================",
        tpl["sec_overview"],
        "============================================================"
    ]
    if is_single:
        act = actions[0]
        p_id = act.get("id")
        kw = act.get("kwargs", {})
        spec = FEATURE_SPECS.get(p_id, {})
        ov = spec.get("overview", {}).get(lang, "")
        if ov: overview_lines.append(ov)
        dyn_fn = spec.get("dynamic_fn")
        if dyn_fn:
            dyn_txt = dyn_fn(kw, lang)
            if dyn_txt: overview_lines.append("\n" + dyn_txt)
    else:
        for idx, act in enumerate(actions, 1):
            p_id = act.get("id")
            kw = act.get("kwargs", {})
            spec = FEATURE_SPECS.get(p_id, {})
            num_s = _to_indic(idx) if lang == "ar" else str(idx)
            emoji = spec.get("emoji", "•")
            t_name = spec.get("title", {}).get(lang, p_id)
            ov = spec.get("overview", {}).get(lang, "")
            overview_lines.append(f"{num_s}. {emoji} {t_name}")
            if ov: overview_lines.append(f"   {ov}")
            dyn_fn = spec.get("dynamic_fn")
            if dyn_fn:
                dyn_txt = dyn_fn(kw, lang)
                if dyn_txt:
                    indented = "\n".join(f"   {l}" for l in dyn_txt.splitlines())
                    overview_lines.append(indented)
            overview_lines.append("")

    # 3. Section 2: Vehicle Usage Instructions (Dynamic Roadmap)
    step_start, step_finish = _build_dynamic_execution_roadmap(actions, lang, tpl)
    time_est = _estimate_execution_time(actions, lang)
    step_exec = tpl["step_executing"].format(time_est=time_est)
    steps_lines = [
        "============================================================",
        tpl["sec_steps"],
        "============================================================",
        f"1. {step_start}",
        f"2. {tpl['step_insert_usb']}",
        f"3. {step_exec}",
        f"4. {step_finish}"
    ]

    # 4. Section 3: Verification & Follow-up
    verif_items = []
    for idx, act in enumerate(actions, 1):
        p_id = act.get("id")
        spec = FEATURE_SPECS.get(p_id, {})
        v_txt = spec.get("verification", {}).get(lang, "")
        if v_txt:
            if is_single:
                verif_items.append(v_txt)
            else:
                num_s = _to_indic(idx) if lang == "ar" else str(idx)
                t_name = spec.get("title", {}).get(lang, p_id)
                verif_items.append(f"{num_s}. {t_name}:\n   {v_txt}")

    verif_lines = []
    if verif_items:
        verif_lines = [
            "============================================================",
            tpl["sec_verification"],
            "============================================================",
            "\n".join(verif_items)
        ]

    # Combine All Parts
    parts = [header, "\n".join(overview_lines), "\n".join(steps_lines)]
    if verif_lines:
        parts.append("\n".join(verif_lines))
    parts.append(banner)

    full_text = "\n\n".join(parts) + "\n"
    if lang == "ar":
        return _apply_arabic_rtl_formatting(full_text)
    return full_text


def generate_info_content(payload_id: str, lang: str = None, **kwargs) -> str:
    """Dispatches payload manual generation in the requested or active language."""
    return generate_unified_manual([{"id": payload_id, "kwargs": kwargs}], lang=lang)


# Adapter mapping to preserve 100% backward compatibility with internal callers
_GENERATORS = {
    p_id: (lambda lang, pid=p_id, **kw: generate_info_content(pid, lang=lang, **kw))
    for p_id in FEATURE_SPECS
}


# ============================================================================
# SECTION 4: HTML RENDERING & EXPORT ENGINE
# ============================================================================

def _load_asset_base64(filename: str) -> str:
    """Loads an asset image and returns it as a base64 data URI."""
    try:
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_paths = [
            os.path.join(os.path.dirname(cur_dir), "assets", filename),
            os.path.join(os.path.dirname(os.path.dirname(cur_dir)), "assets", filename)
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    return f"data:image/png;base64,{b64}"
    except Exception:
        pass
    return ""

def manual_text_to_html(raw_text: str, lang: str = "ar", app_icon_b64: str = None) -> str:
    """
    Parses any payload manual raw text into a self-contained, luxury dark-theme HTML document.
    Strictly conforms to the Aero Suite brand identity and Unified Design System:
    - Official ⚡ AERO SUITE brand logo (matching the desktop application top-bar)
    - Depth Gradient Background: Obsidian (#1C2230) to Pure Black (#000000)
    - Accents: Electric Cyan (#00D2FF) and Sport Crimson (#FF2D55)
    - Clean header without redundant badge clutter
    - 100% standalone offline operation
    """
    is_ar = (lang == "ar")
    direction = "rtl" if is_ar else "ltr"
    align = "right" if is_ar else "left"

    # Split by separator bars
    parts = [p.strip() for p in re.split(r'={10,}', raw_text) if p.strip()]
    if not parts:
        return f"<!DOCTYPE html><html lang='{lang}' dir='{direction}'><body><pre>{html.escape(raw_text)}</pre></body></html>"

    # 1. Header & Meta (Part 0)
    part0_lines = [l.strip() for l in parts[0].splitlines() if l.strip()]
    title_line = part0_lines[0] if part0_lines else "Aero Suite Manual"

    emoji = "📋"
    clean_title = title_line
    emoji_m = re.match(r'^([^\w\s\d]+)\s*(.*)', title_line)
    if emoji_m:
        emoji = emoji_m.group(1).strip()
        clean_title = emoji_m.group(2).strip()

    # Clean heading text so it doesn't duplicate 'Aero Suite —' since the logo already has it
    clean_heading = re.sub(r'^(Aero Suite\s*—\s*|AERO SUITE\s*—\s*)', '', clean_title, flags=re.IGNORECASE)
    clean_heading = re.sub(r'\s*—\s*Aero Suite.*$', '', clean_heading, flags=re.IGNORECASE).strip()
    if not clean_heading:
        clean_heading = clean_title

    # If app icon is passed or detected from clean_pkg, generate icon html
    header_icon_html = ""
    if not app_icon_b64:
        # Auto-detect if clean_pkg in kwargs or text
        if "com.android.vending" in raw_text:
            app_icon_b64 = _load_asset_base64("google_play.png")
        elif "com.google.android.apps.nbu.files" in raw_text:
            app_icon_b64 = _load_asset_base64("documents_ui.png")
        elif "GMS" in raw_text or "Google Play Services" in raw_text or "خدمات جوجل" in raw_text:
            app_icon_b64 = _load_asset_base64("google_services_square.png")

    if app_icon_b64:
        header_icon_html = f'<img src="{app_icon_b64}" alt="App Icon" style="width: 38px; height: 38px; object-fit: contain; vertical-align: middle; border-radius: 8px; box-shadow: 0 4px 14px rgba(0,0,0,0.4); margin-inline-end: 8px;" />'

    title_display = f"{header_icon_html}{html.escape(clean_heading)}" if header_icon_html else f"{emoji} {html.escape(clean_heading)}"

    # Metadata key-value pairs
    meta_pairs = []
    for l in part0_lines[1:]:
        if ":" in l or "：" in l:
            sep = "：" if "：" in l else ":"
            k, v = l.split(sep, 1)
            meta_pairs.append((k.strip(), v.strip()))

    # 2. Process Sections (Parts 1 to N-1)
    if len(parts) >= 3 and any(sig in parts[-1] for sig in ["DEVELOPER", "برمجة", "Разработка", "开发者", DEVELOPER_NAME]):
        body_parts = parts[1:-1]
    else:
        body_parts = parts[1:]

    sections = []
    i = 0
    while i < len(body_parts):
        curr = body_parts[i]
        curr_lines = [l.strip() for l in curr.splitlines() if l.strip()]
        if len(curr_lines) == 1 and (re.match(r'^\d+\.', curr_lines[0]) or re.match(r'^[١-٩]+\.', curr_lines[0])):
            sec_title = curr_lines[0]
            sec_body = body_parts[i+1] if i + 1 < len(body_parts) else ""
            sections.append((sec_title, sec_body))
            i += 2
        else:
            if curr_lines and (re.match(r'^\d+\.', curr_lines[0]) or re.match(r'^[١-٩]+\.', curr_lines[0])):
                sec_title = curr_lines[0]
                sec_body = "\n".join(curr_lines[1:])
                sections.append((sec_title, sec_body))
            else:
                sections.append(("", curr))
            i += 1

    # Render Sections HTML
    rendered_sections = []
    for sec_title, sec_body in sections:
        sec_num = ""
        sec_clean_title = sec_title
        num_m = re.match(r'^([\d١-٩]+)\.\s*(.*)', sec_title)
        if num_m:
            sec_num = num_m.group(1)
            sec_clean_title = num_m.group(2)
            if is_ar and sec_num.isdigit():
                sec_num = _to_indic(sec_num)

        is_steps = any(kw in sec_clean_title for kw in ["خطوات", "Instructions", "Инструкция", "操作步骤", "Usage"])
        is_apps_list = any(kw in sec_clean_title for kw in ["التطبيقات", "Applications", "Приложения", "软件包", "APKS", "الخصائص", "Features", "الميزات"])

        body_html = ""
        if is_steps:
            body_html += '<div class="steps-container">'
            steps_data = []
            raw_lines = [l.strip() for l in sec_body.splitlines() if l.strip()]
            curr_num = None
            curr_lines = []
            for sl in raw_lines:
                sm = re.match(r'^([\d١-٩]+)\.\s*(.*)', sl)
                if sm:
                    if curr_num is not None:
                        steps_data.append((curr_num, curr_lines))
                    curr_num = sm.group(1)
                    curr_lines = [sm.group(2)]
                else:
                    if curr_num is not None:
                        curr_lines.append(sl)
                    else:
                        steps_data.append(("", [sl]))
            if curr_num is not None:
                steps_data.append((curr_num, curr_lines))

            for st_num, lines in steps_data:
                if st_num:
                    if is_ar and st_num.isdigit():
                        st_num = _to_indic(st_num)
                    formatted_lines = []
                    for idx, line in enumerate(lines):
                        txt = html.escape(line)
                        for kw in ["USB", "Reboot", "Unplug", "Insert", "ON", "ACC", "100%", "Home"]:
                            txt = re.sub(rf'\b({re.escape(kw)})\b', r'<mark>\1</mark>', txt, flags=re.IGNORECASE)
                        for ar_phrase in ["صوت التنبيه الصيني", "نظام الحماية الذكي", "الريستارت الأول", "الريستارت الثاني"]:
                            txt = txt.replace(ar_phrase, f"<mark>{ar_phrase}</mark>")
                        if idx == 0 and len(lines) > 1:
                            formatted_lines.append(f'<div class="step-main-title">{txt}</div>')
                        elif idx == 0:
                            formatted_lines.append(txt)
                        else:
                            formatted_lines.append(f'<div class="step-subline">{txt}</div>')
                    inner_content = "".join(formatted_lines)
                    body_html += f"""
                    <div class="step-card">
                        <div class="step-badge">{st_num}</div>
                        <div class="step-text">{inner_content}</div>
                    </div>"""
                else:
                    for l in lines:
                        body_html += f'<p class="step-extra">{html.escape(l)}</p>'
            body_html += '</div>'
        elif is_apps_list:
            body_html += '<div class="apps-grid">'
            raw_apps = [a.strip() for a in sec_body.split(" • ") if a.strip()]
            for item in raw_apps:
                lines = [l.strip() for l in item.splitlines() if l.strip()]
                if not lines:
                    continue
                header = lines[0]
                clean_header = re.sub(r'^[•\s*-]+', '', header).strip()
                details = lines[1:] if len(lines) > 1 else []
                detail_tags = ""
                for d in details:
                    d_clean = re.sub(r'^[-*•]\s*', '', d)
                    tags = [t.strip() for t in d_clean.split("|") if t.strip()]
                    for tg in tags:
                        tag_cls = "tag-default"
                        if "نظام" in tg or "System" in tg:
                            tag_cls = "tag-cyan"
                        elif "تفعيل" in tg or "Enable" in tg or "نعم" in tg or "YES" in tg:
                            tag_cls = "tag-cyan"
                        elif "تعطيل" in tg or "Disable" in tg or "حذف" in tg or "Delete" in tg or "Remove" in tg:
                            tag_cls = "tag-crimson"
                        elif "مفعل" in tg or "Enabled" in tg:
                            tag_cls = "tag-cyan"
                        detail_tags += f'<span class="app-tag {tag_cls}">{html.escape(tg)}</span>'
                has_custom_icon = any(clean_header.startswith(c) for c in ["💡", "💺", "🅿️", "🚶", "📢", "🚪", "🔒", "🚗", "📦", "🚀", "⚙️", "🌐", "🧹", "🚫", "✅", "🔄", "💾", "📥", "⚠️", "📋"])
                card_prefix = "" if has_custom_icon else "📦 "
                body_html += f"""
                <div class="app-card">
                    <div class="app-title">{card_prefix}{html.escape(clean_header)}</div>
                    {f'<div class="app-tags">{detail_tags}</div>' if detail_tags else ''}
                </div>"""
            body_html += '</div>'
        else:
            body_html += '<div class="overview-container">'
            lines = sec_body.splitlines()
            for line in lines:
                l_str = line.strip()
                if not l_str:
                    continue
                if re.match(r'^([\d١-٩]+)\.\s*(.*)', l_str):
                    nm = re.match(r'^([\d١-٩]+)\.\s*(.*)', l_str)
                    num_val = nm.group(1)
                    if is_ar and num_val.isdigit():
                        num_val = _to_indic(num_val)
                    item_txt = nm.group(2)
                    body_html += f'<div class="list-item"><span class="item-num">{num_val}</span><span class="item-text">{html.escape(item_txt)}</span></div>'
                elif l_str.startswith("-") or l_str.startswith("•") or l_str.startswith("*"):
                    clean_sub = re.sub(r'^[-*•]\s*', '', l_str)
                    body_html += f'<div class="sub-item"><span class="bullet">▪</span><span>{html.escape(clean_sub)}</span></div>'
                elif l_str.startswith("⚠️") or re.match(r'^(تحذير|تنبيه|WARNING|CAUTION|DANGER)\s*[:：]', l_str, flags=re.IGNORECASE):
                    body_html += f'<div class="callout callout-crimson"><span class="callout-icon">⚠️</span><span>{html.escape(l_str)}</span></div>'
                else:
                    body_html += f'<p class="overview-para">{html.escape(l_str)}</p>'
            body_html += '</div>'

        sec_header_html = ""
        if sec_title:
            pill_html = f'<span class="section-pill">{sec_num}</span>' if sec_num else ''
            sec_header_html = f"""
            <div class="section-header">
                {pill_html}
                <h2 class="section-title">{html.escape(sec_clean_title)}</h2>
            </div>"""

        rendered_sections.append(f"""
        <section class="card section-card">
            {sec_header_html}
            <div class="section-body">
                {body_html}
            </div>
        </section>""")

    # 3. Meta Chips HTML
    meta_chips_html = ""
    if meta_pairs:
        chips = []
        for k, v in meta_pairs:
            icon = "📌"
            if any(w in k for w in ["السيارة", "Vehicle", "车型"]):
                icon = "🚗"
            elif any(w in k for w in ["نوع", "Mode", "模式"]):
                icon = "⚙️"
            elif any(w in k for w in ["اسم", "Preset", "Name"]):
                icon = "🏷️"
            elif any(w in k for w in ["الناشر", "Author", "创作者"]):
                icon = "👤"
            elif any(w in k for w in ["ميديا", "Media", "媒体"]):
                icon = "📁"
            elif any(w in k for w in ["تطبيق", "App", "Package"]):
                icon = "📱"
            elif any(w in k for w in ["حالة", "Status", "توافق", "Architecture"]):
                icon = "🛡️"

            chips.append(f"""
            <div class="meta-chip">
                <span class="meta-label">{icon} {html.escape(k)}</span>
                <span class="meta-value">{html.escape(v)}</span>
            </div>""")
        meta_chips_html = f'<div class="meta-grid">{"".join(chips)}</div>'

    subtitle_car = "شاشة دونج فينج شاين (Dongfeng Shine / Aeolus D53)" if is_ar else "Dongfeng Shine / Aeolus D53 Infotainment"

    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "guide", "user_guide.html")
    dev_lead = "برمجة وتطوير:" if is_ar else "Developed by:"

    return render_template_file(
        template_path,
        lang=lang,
        direction=direction,
        align=align,
        clean_heading=html.escape(clean_heading),
        title_display=title_display,
        subtitle_car=subtitle_car,
        meta_chips_html=meta_chips_html,
        rendered_sections="".join(rendered_sections),
        dev_lead=dev_lead,
        dev_name=DEVELOPER_NAME,
        dev_email=DEVELOPER_EMAIL,
        dev_phone=DEVELOPER_PHONE
    )




def generate_info_html(payload_id_or_actions, lang: str = None, **kwargs) -> str:
    """Dispatches payload manual generation and renders it into rich, self-contained HTML."""
    if not lang:
        lang = get_i18n().current_lang or "ar"

    if isinstance(payload_id_or_actions, list):
        content = generate_unified_manual(payload_id_or_actions, lang=lang)
        payload_id = "composite"
    else:
        payload_id = payload_id_or_actions
        content = generate_info_content(payload_id, lang=lang, **kwargs)

    app_icon_b64 = kwargs.get("app_icon_b64")
    clean_pkg = kwargs.get("clean_pkg", "")
    if not app_icon_b64:
        if clean_pkg == "com.android.vending":
            app_icon_b64 = _load_asset_base64("google_play.png")
        elif clean_pkg == "com.google.android.apps.nbu.files":
            app_icon_b64 = _load_asset_base64("documents_ui.png")
        elif payload_id == "install_gms":
            app_icon_b64 = _load_asset_base64("google_services_square.png")

    return manual_text_to_html(content, lang=lang, app_icon_b64=app_icon_b64)


def get_localized_manual_filename(lang: str = None) -> str:
    """Returns the standardized, localized manual filename based on language."""
    if not lang:
        lang = get_i18n().current_lang or "ar"
    if lang == "ar":
        return "دليل_الاستخدام"
    elif lang == "ru":
        return "Инструкция"
    elif lang == "zh":
        return "使用说明"
    else:
        return "User_Guide"


def write_payload_manuals(usb_drive: str, base_filename: str, payload_id: str, lang: str = None, **kwargs) -> str:
    """
    Writes ONLY the rich standalone .html manual to the USB drive using localized naming.
    In Arabic: 'دليل_الاستخدام.html'
    In English: 'User_Guide.html'
    In Russian: 'Инструкция.html'
    In Chinese: '使用说明.html'
    Cleans up any legacy info files (*_Info.html, *_Info.txt).
    Returns html_path.
    """
    if not lang:
        lang = get_i18n().current_lang or "ar"

    localized_name = get_localized_manual_filename(lang)
    html_content = generate_info_html(payload_id, lang=lang, **kwargs)
    html_path = os.path.join(usb_drive, f"{localized_name}.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Clean up any legacy or english manual filenames on the drive if present
    for old_candidate in [
        f"{base_filename}.html",
        f"{base_filename}.txt",
        "Info.html",
        "Info.txt",
        "User_Guide.txt",
        "دليل_الاستخدام.txt"
    ]:
        if old_candidate != f"{localized_name}.html":
            old_p = os.path.join(usb_drive, old_candidate)
            if os.path.exists(old_p):
                try:
                    os.remove(old_p)
                except Exception:
                    pass

    return html_path


def write_composite_manual(usb_drive: str, actions: list, lang: str = None) -> str:
    """
    Writes the unified .html manual for a composite multi-command queue (the basket).
    Consolidates all planned operations into a single clear execution guide.
    """
    if not lang:
        lang = get_i18n().current_lang or "ar"

    localized_name = get_localized_manual_filename(lang)
    html_content = generate_info_html(actions, lang=lang)
    html_path = os.path.join(usb_drive, f"{localized_name}.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return html_path
