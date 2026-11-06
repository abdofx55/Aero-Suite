"""
vehicle_tweaks_data.py — Master Registry of Automotive CAN-Bus Customization Features.
Dongfeng Shine / Aeolus D53 (Qinggan ICanBusService Platform).
Extensible data model allowing easy addition of new vehicle features.
"""

VEHICLE_TWEAKS = [
    {
        "id": "welcome_light",
        "icon": "💡",
        "name_ar": "إضاءة الترحيب عند الاقتراب",
        "name_en": "Welcome Light",
        "name_zh": "靠近迎宾照地灯",
        "name_ru": "Приветственная подсветка",
        "desc_ar": "تشغيل الإضاءة الخارجية الترحيبية تلقائياً بمجرد الاقتراب من السيارة بالمفتاح الذكي",
        "desc_en": "Turn on exterior courtesy lights automatically when approaching with the smart key",
        "desc_zh": "携带智能钥匙靠近车辆时自动开启外部迎宾灯光",
        "desc_ru": "Автоматическое включение внешней подсветки при приближении с умным ключом",
        "commands_enable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 40 i32 79 i32 2',
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 274 i32 334 i32 2'
        ],
        "commands_disable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 40 i32 79 i32 1',
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 274 i32 334 i32 1'
        ]
    },
    {
        "id": "seat_welcome",
        "icon": "💺",
        "name_ar": "ترحيب المقعد وتسهيل الدخول (Easy Entry)",
        "name_en": "Seat Welcome / Easy Entry",
        "name_zh": "座椅迎宾与便捷进出 (Easy Entry)",
        "name_ru": "Комфортная посадка водителя (Easy Entry)",
        "desc_ar": "إرجاع مقعد السائق للخلف تلقائياً عند فتح الباب لتسهيل الركوب، وإعادته لوضعية القيادة بعد الركوب",
        "desc_en": "Slide driver seat backward on door open for easy entry, returning to drive position",
        "desc_zh": "开门时主驾座椅自动后退方便上下车，入座关门后自动恢复驾驶位置",
        "desc_ru": "Автоматический сдвиг сиденья водителя назад при открытии двери и возврат в рабочее положение",
        "commands_enable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 176 i32 321 i32 2'
        ],
        "commands_disable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 176 i32 321 i32 1'
        ]
    },
    {
        "id": "speed_auto_lock",
        "icon": "🔒",
        "name_ar": "قفل الأبواب التلقائي مع السرعة (Speed Lock)",
        "name_en": "Speed-sensing Auto Door Lock",
        "name_zh": "行车自动落锁 (Speed Lock)",
        "name_ru": "Автоблокировка дверей при движении (Speed Lock)",
        "desc_ar": "قفل السنتر لوك لجميع الأبواب تلقائياً بمجرد تحرك السيارة وتجاوز سرعة 15 كم/س لحماية الركاب والأطفال",
        "desc_en": "Automatically lock all doors once the vehicle moves and exceeds 15 km/h for passenger safety",
        "desc_zh": "车辆起步且车速超过 15km/h 时自动锁止四门中控锁，保障乘客与儿童安全",
        "desc_ru": "Автоматическое запирание всех дверей при достижении скорости более 15 км/ч для безопасности",
        "commands_enable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 195 i32 254 i32 2'
        ],
        "commands_disable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 195 i32 254 i32 1'
        ]
    },
    {
        "id": "auto_park_engine_off",
        "icon": "🅿️",
        "name_ar": "تفعيل الهاند بريك وفتح الأقفال عند إطفاء المحرك",
        "name_en": "Auto Park & Unlock on Engine Off",
        "name_zh": "熄火自动驻车与解锁",
        "name_ru": "Авторучник и разблокировка при заглушении",
        "desc_ar": "تفعيل فرامل اليد الإلكترونية (EPB) تلقائياً وفك قفل الأبواب بمجرد إطفاء محرك السيارة",
        "desc_en": "Engage electronic parking brake and unlock doors automatically when engine stops",
        "desc_zh": "车辆熄火后自动拉起电子手刹 (EPB) 并解锁全车车门",
        "desc_ru": "Автоматическая активация стояночного тормоза (EPB) и отпирание дверей при выключении двигателя",
        "commands_enable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 13 i32 52 i32 2'
        ],
        "commands_disable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 13 i32 52 i32 1'
        ]
    },
    {
        "id": "walk_away_locking",
        "icon": "🚶‍♂️",
        "name_ar": "القفل التلقائي عند الابتعاد",
        "name_en": "Walk-away Locking",
        "name_zh": "离车自动落锁",
        "name_ru": "Автоматическое запирание при удалении",
        "desc_ar": "قفل جميع أبواب السيارة تلقائياً بمجرد نزول السائق والابتعاد عن السيارة بالمفتاح الذكي",
        "desc_en": "Lock all vehicle doors automatically when walking away with the smart key",
        "desc_zh": "驾驶员携带智能钥匙下车离开车辆感应范围时自动锁闭四门",
        "desc_ru": "Автоматическое закрытие всех дверей при удалении от автомобиля с умным ключом",
        "commands_enable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 174 i32 234 i32 2',
            'content insert --uri content://qinggan.settings/system --bind name:s:WALK_LOCK_SWITCH --bind value:i:2',
            'am broadcast -a com.qinggan.action.CONFIG_CHANGE >/dev/null 2>&1'
        ],
        "commands_disable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 174 i32 234 i32 1',
            'content insert --uri content://qinggan.settings/system --bind name:s:WALK_LOCK_SWITCH --bind value:i:1',
            'am broadcast -a com.qinggan.action.CONFIG_CHANGE >/dev/null 2>&1'
        ]
    },
    {
        "id": "horn_beep_lock",
        "icon": "📢",
        "name_ar": "صوت تأكيد القفل بالريموت (Horn Beep on Lock)",
        "name_en": "Horn Beep on Lock",
        "name_zh": "锁车喇叭鸣笛提示 (Horn Beep on Lock)",
        "name_ru": "Звуковое подтверждение блокировки (Клаксон)",
        "desc_ar": "إطلاق بوق السيارة لنقرة خفيفة لتأكيد قفل السيارة بنجاح دون الحاجة للنظر إليها",
        "desc_en": "Emit a brief horn chirp to confirm the vehicle is successfully locked with remote key",
        "desc_zh": "使用遥控钥匙锁车成功时鸣响短促喇叭音提示，无需回头确认",
        "desc_ru": "Короткий звуковой сигнал клаксона при успешном закрытии авто с брелока",
        "commands_enable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 56 i32 124 i32 0',
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 198 i32 257 i32 2'
        ],
        "commands_disable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 56 i32 124 i32 1',
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 198 i32 257 i32 1'
        ]
    },
    {
        "id": "door_ajar_lock_fail_alert",
        "icon": "🚪⚠️",
        "name_ar": "تنبيه الباب الموارب وفشل القفل (Door Ajar Alert)",
        "name_en": "Door Ajar & Lock Failure Alert",
        "name_zh": "车门未关好锁车报警 (Door Ajar Alert)",
        "name_ru": "Предупреждение о незакрытой двери",
        "desc_ar": "إطلاق بوق السيارة لنغمة تحذيرية فوراً إذا حاولت قفل السيارة بالريموت وكان أحد الأبواب أو الشنطة موارباً",
        "desc_en": "Emit an alert horn chirp if attempting to lock with remote while a door or trunk is ajar",
        "desc_zh": "车门或后备箱未关严时按锁车键，立即鸣笛报警提示锁车失败",
        "desc_ru": "Звуковой сигнал тревоги при попытке запереть авто с неплотно закрытой дверью или багажником",
        "commands_enable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 197 i32 256 i32 2'
        ],
        "commands_disable": [
            'service call qg.canbus 52 s16 "com.qinggan.canbus.ICanBusService" i32 1 i32 197 i32 256 i32 1'
        ]
    }
]


def get_all_vehicle_tweaks() -> list:
    """Returns the complete list of available vehicle tweaks."""
    return VEHICLE_TWEAKS


def get_tweak_by_id(tweak_id: str) -> dict:
    """Retrieves a specific tweak dictionary by its unique string identifier."""
    for tweak in VEHICLE_TWEAKS:
        if tweak["id"] == tweak_id:
            return tweak
    return None
