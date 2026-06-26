"""Minimal in-app localization (no external deps).

A single module-level :class:`Translator` holds the active language. Call
:func:`t` with a key to get the localized string; missing keys fall back to
English and finally to the key itself so the UI never shows blanks.
"""

from __future__ import annotations

# Display names for the language picker (value stored in config -> label).
LANGUAGES: dict[str, str] = {
    "en": "English",
    "ru": "Русский",
}

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # Tabs
        "tab_main": "Main",
        "tab_pattern": "Pattern",
        "tab_appearance": "Appearance",
        # Left panel
        "weapon_profiles": "Weapon profiles",
        "add": "Add",
        "duplicate": "Duplicate",
        "delete": "Delete",
        "new_from_template": "New from template…",
        "import": "Import…",
        "export": "Export…",
        "profiles_saved_next": "Profiles saved next to the app:\n{name}",
        "add_all_slots": "Add all {category} slots",
        "ungrouped": "Ungrouped",
        # Header
        "status_off": "OFF",
        "status_armed": "ARMED",
        "status_firing": "● FIRING",
        "arm_off": "ARM  (OFF)",
        "armed_on": "ARMED  (ON)",
        # Game / weapon selector
        "game": "Game",
        "weapon_pick": "Weapon",
        "all_games": "All games",
        "no_weapons": "(no profiles in this game)",
        # Profile settings
        "profile_settings": "Profile settings",
        "name": "Name",
        "weapon": "Weapon",
        "group": "Group",
        "activation": "Activation",
        "act_lmb": "While firing (LMB held)",
        "act_rmb": "While aiming (RMB held)",
        "act_lmb_rmb": "ADS + fire (LMB + RMB held)",
        "compensation_strength": "Compensation strength",
        "game_sensitivity": "In-game sensitivity",
        "game_sensitivity_tip": "Your sensitivity value from the game; the pattern is scaled by 1 / this value.",
        "loop_pattern": "Loop pattern while held",
        "hold_last": "Hold last step while held",
        # Randomization
        "randomization": "Randomization",
        "enable_randomization": "Enable randomization (humanize)",
        "pos_jitter": "Position jitter (px)",
        "delay_jitter": "Delay jitter (ms)",
        # Keybinds
        "keybinds": "Keybinds",
        "macro_keybind": "Macro on/off key",
        "switch_key": "Switch-to-profile key",
        "click_to_bind": "Click to bind…",
        "press_a_key": "Press a key…",
        "clear_bind": "Clear",
        # Notes
        "notes": "Notes",
        "tip_canvas": (
            "Tip: positive dy moves aim down to counter upward recoil. "
            "Click on the canvas to add points, drag to adjust, right-click to delete."
        ),
        # Pattern tab
        "recoil_pattern": "Recoil pattern",
        "zoom": "Zoom",
        "preview": "▶ Preview",
        "stop": "■ Stop",
        "clear": "Clear",
        "steps": "Steps",
        "add_step": "Add step",
        "remove_step": "Remove step",
        # Appearance tab
        "appearance": "Appearance & general",
        "language": "Language",
        "theme": "Theme",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "accent_color": "Accent color",
        "pick_color": "Pick…",
        "global_sensitivity": "Global sensitivity",
        "toggle_hotkey": "Toggle hotkey",
        "general": "General",
        # Dialogs
        "delete_profile_title": "Delete profile",
        "delete_profile_msg": "Delete the selected profile?",
        "import_profile": "Import profile",
        "export_profile": "Export profile",
        "import_failed": "Import failed",
        "export_failed": "Save failed",
        "save_failed": "Save failed: {error}",
        "input_unavailable": "Input listener unavailable: {error}",
    },
    "ru": {
        "tab_main": "Главная",
        "tab_pattern": "Паттерн",
        "tab_appearance": "Оформление",
        "weapon_profiles": "Профили оружия",
        "add": "Добавить",
        "duplicate": "Дублировать",
        "delete": "Удалить",
        "new_from_template": "Из шаблона…",
        "import": "Импорт…",
        "export": "Экспорт…",
        "profiles_saved_next": "Профили сохраняются рядом с программой:\n{name}",
        "add_all_slots": "Добавить все слоты {category}",
        "ungrouped": "Без группы",
        "status_off": "ВЫКЛ",
        "status_armed": "ГОТОВ",
        "status_firing": "● ОГОНЬ",
        "arm_off": "ВКЛЮЧИТЬ  (ВЫКЛ)",
        "armed_on": "ГОТОВ  (ВКЛ)",
        "game": "Игра",
        "weapon_pick": "Оружие",
        "all_games": "Все игры",
        "no_weapons": "(нет профилей в этой игре)",
        "profile_settings": "Настройки профиля",
        "name": "Название",
        "weapon": "Оружие",
        "group": "Группа",
        "activation": "Активация",
        "act_lmb": "При стрельбе (зажата ЛКМ)",
        "act_rmb": "При прицеливании (зажата ПКМ)",
        "act_lmb_rmb": "Прицел + огонь (ЛКМ + ПКМ)",
        "compensation_strength": "Сила компенсации",
        "game_sensitivity": "Сенса из игры",
        "game_sensitivity_tip": "Значение чувствительности из игры; паттерн масштабируется на 1 / это значение.",
        "loop_pattern": "Зациклить паттерн при удержании",
        "hold_last": "Держать последний шаг при удержании",
        "randomization": "Рандомизация",
        "enable_randomization": "Включить рандомизацию (humanize)",
        "pos_jitter": "Разброс позиции (px)",
        "delay_jitter": "Разброс задержки (мс)",
        "keybinds": "Горячие клавиши",
        "macro_keybind": "Клавиша вкл/выкл макроса",
        "switch_key": "Клавиша выбора профиля",
        "click_to_bind": "Нажми, чтобы задать…",
        "press_a_key": "Нажми клавишу…",
        "clear_bind": "Сброс",
        "notes": "Заметки",
        "tip_canvas": (
            "Подсказка: положительный dy опускает прицел, компенсируя отдачу вверх. "
            "Клик по холсту — добавить точку, перетаскивание — изменить, ПКМ — удалить."
        ),
        "recoil_pattern": "Паттерн отдачи",
        "zoom": "Масштаб",
        "preview": "▶ Превью",
        "stop": "■ Стоп",
        "clear": "Очистить",
        "steps": "Шаги",
        "add_step": "Добавить шаг",
        "remove_step": "Удалить шаг",
        "appearance": "Оформление и общее",
        "language": "Язык",
        "theme": "Тема",
        "theme_dark": "Тёмная",
        "theme_light": "Светлая",
        "accent_color": "Акцентный цвет",
        "pick_color": "Выбрать…",
        "global_sensitivity": "Глобальная сенса",
        "toggle_hotkey": "Клавиша вкл/выкл",
        "general": "Общее",
        "delete_profile_title": "Удалить профиль",
        "delete_profile_msg": "Удалить выбранный профиль?",
        "import_profile": "Импорт профиля",
        "export_profile": "Экспорт профиля",
        "import_failed": "Ошибка импорта",
        "export_failed": "Ошибка сохранения",
        "save_failed": "Не удалось сохранить: {error}",
        "input_unavailable": "Слушатель ввода недоступен: {error}",
    },
}


class Translator:
    def __init__(self, language: str = "en") -> None:
        self.language = language if language in _STRINGS else "en"

    def set_language(self, language: str) -> None:
        self.language = language if language in _STRINGS else "en"

    def t(self, key: str, **kwargs: object) -> str:
        table = _STRINGS.get(self.language, _STRINGS["en"])
        text = table.get(key) or _STRINGS["en"].get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return text
        return text


# Shared instance used across the UI.
TR = Translator()


def t(key: str, **kwargs: object) -> str:
    return TR.t(key, **kwargs)
