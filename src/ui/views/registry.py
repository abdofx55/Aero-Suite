"""
registry.py — Declarative View Registry for Aero Suite.
Provides a single source of truth for all UI views, sidebar navigation,
category grouping, and dynamic language switching.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Type, Any
from PySide6.QtWidgets import QWidget

from core.i18n import t


@dataclass
class CategoryDescriptor:
    id: str
    title_key: str
    default_title: str


@dataclass
class ViewDescriptor:
    id: str
    category_id: str
    icon: str
    title_key: str
    desc_key: str
    view_class: Type[QWidget]
    default_title: str = ""
    default_desc: str = ""
    init_kwargs_factory: Optional[Callable[[Any], Dict[str, Any]]] = None
    hide_terminal: bool = False  # e.g. for canvas views like roadmap/support/about

    def create_view(self, parent: Any) -> QWidget:
        """Instantiates the view widget with parent and any extra kwargs."""
        kwargs = {}
        if self.init_kwargs_factory:
            kwargs = self.init_kwargs_factory(parent) or {}
        return self.view_class(parent, **kwargs)

    @property
    def localized_title(self) -> str:
        return t(self.title_key, self.default_title)

    @property
    def localized_desc(self) -> str:
        return t(self.desc_key, self.default_desc)


class ViewRegistry:
    """Singleton registry holding all registered categories and view descriptors."""
    _instance = None

    def __init__(self):
        self._categories: List[CategoryDescriptor] = []
        self._views: List[ViewDescriptor] = []
        self._views_map: Dict[str, ViewDescriptor] = {}

    @classmethod
    def get_instance(cls) -> "ViewRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_default_views()
        return cls._instance

    def register_category(self, cat: CategoryDescriptor):
        self._categories.append(cat)

    def register_view(self, view: ViewDescriptor):
        self._views.append(view)
        self._views_map[view.id] = view

    def get_categories(self) -> List[CategoryDescriptor]:
        return list(self._categories)

    def get_all_views(self) -> List[ViewDescriptor]:
        return list(self._views)

    def get_view(self, view_id: str) -> Optional[ViewDescriptor]:
        alias_map = {
            "install_apps": "apps_hub",
            "uninstall_apps": "apps_hub",
            "open_app": "apps_hub",
            "install_gms": "gms_hub",
            "uninstall_gms": "gms_hub",
            "install_hvac_bar": "hvac_bar_hub",
            "restore_hvac_bar": "hvac_bar_hub",
            "disable_launcher": "launcher_control",
            "enable_launcher": "launcher_control",
        }
        mapped_id = alias_map.get(view_id, view_id)
        return self._views_map.get(mapped_id)

    def get_views_for_category(self, category_id: str) -> List[ViewDescriptor]:
        return [v for v in self._views if v.category_id == category_id]

    def _register_default_views(self):
        # 1. Import view classes lazily to avoid circular dependencies
        from core.paths import GMS_DIR, BACKUPS_DIR, FACTORY_BACKUP_DIR
        from ui.views.quick_setup_view import QuickSetupView
        from ui.views.apps_hub_view import AppsHubView
        from ui.views.open_settings_view import OpenSettingsView
        from ui.views.gms_views import GmsHubView
        from ui.views.hvac_bar_views import HvacBarHubView
        from ui.views.launcher_views import LauncherControlView
        from ui.views.reboot_view import RebootScreenView
        from ui.views.backup_view import BackupView
        from ui.views.restore_view import RestoreView
        from ui.views.factory_reset_view import FactoryResetView
        from ui.views.fetch_logs_view import FetchLogsView
        from ui.views.vehicle_tweaks_view import VehicleTweaksView
        from ui.views.roadmap_view import RoadmapView
        from ui.views.support_view import SupportView
        from ui.views.about_view import AboutView

        # Categories
        cat_apps = CategoryDescriptor("applications_control", "categories.applications_control", "APPLICATIONS & CONTROL")
        cat_tweaks = CategoryDescriptor("vehicle_controls", "categories.vehicle_controls", "VEHICLE CONTROLS & TWEAKS")
        cat_gms = CategoryDescriptor("google_services", "categories.google_services", "GOOGLE PLAY SERVICES")
        cat_launcher = CategoryDescriptor("launcher_power", "categories.launcher_power", "LAUNCHER & POWER")
        cat_backup = CategoryDescriptor("backup_maintenance", "categories.backup_maintenance", "BACKUP & MAINTENANCE")
        cat_about = CategoryDescriptor("about_system", "categories.about_system", "ABOUT & SUPPORTED SYSTEMS")
        cat_rnd = CategoryDescriptor("community_support", "categories.community_support", "AERO PARTNERS & R&D")

        for c in [cat_apps, cat_tweaks, cat_gms, cat_launcher, cat_backup, cat_about, cat_rnd]:
            self.register_category(c)

        # Views
        # 1. Applications & Control
        self.register_view(ViewDescriptor(
            id="quick_setup",
            category_id="applications_control",
            icon="⚡",
            title_key="nav.quick_setup_title",
            desc_key="nav.quick_setup_desc",
            default_title="Quick Setup",
            default_desc="Aero Bar + GMS full provision",
            view_class=QuickSetupView
        ))
        self.register_view(ViewDescriptor(
            id="apps_hub",
            category_id="applications_control",
            icon="📦",
            title_key="nav.apps_hub_title",
            desc_key="nav.apps_hub_desc",
            default_title="App Manager",
            default_desc="Install, remove & launch apps",
            view_class=AppsHubView
        ))
        self.register_view(ViewDescriptor(
            id="open_settings",
            category_id="applications_control",
            icon="⚙️",
            title_key="nav.open_settings_title",
            desc_key="nav.open_settings_desc",
            default_title="Open Settings",
            default_desc="Unlock full Android Settings",
            view_class=OpenSettingsView
        ))

        # 2. Vehicle Controls & Tweaks
        self.register_view(ViewDescriptor(
            id="vehicle_tweaks",
            category_id="vehicle_controls",
            icon="🚗",
            title_key="nav.vehicle_tweaks_title",
            desc_key="nav.vehicle_tweaks_desc",
            default_title="Vehicle Tweaks",
            default_desc="Configure advanced car comfort & lock features",
            view_class=VehicleTweaksView
        ))

        # 3. Google Play Services
        self.register_view(ViewDescriptor(
            id="gms_hub",
            category_id="google_services",
            icon="🌐",
            title_key="nav.gms_hub_title",
            desc_key="nav.gms_hub_desc",
            default_title="Google Services",
            default_desc="Install or remove Google Play",
            view_class=GmsHubView,
            init_kwargs_factory=lambda p: {"gms_dir": GMS_DIR}
        ))

        # 4. Launcher & Power
        self.register_view(ViewDescriptor(
            id="hvac_bar_hub",
            category_id="launcher_power",
            icon="❄️",
            title_key="nav.hvac_bar_hub_title",
            desc_key="nav.hvac_bar_hub_desc",
            default_title="Enhanced Navigation & Climate Bar",
            default_desc="Back, Home, Recent Apps & Installed Apps navbar",
            view_class=HvacBarHubView
        ))
        self.register_view(ViewDescriptor(
            id="launcher_control",
            category_id="launcher_power",
            icon="⚡",
            title_key="nav.launcher_control_title",
            desc_key="nav.launcher_control_desc",
            default_title="Launcher Control",
            default_desc="Freeze or restore factory dashboard",
            view_class=LauncherControlView
        ))
        self.register_view(ViewDescriptor(
            id="reboot_screen",
            category_id="launcher_power",
            icon="🔄",
            title_key="nav.reboot_screen_title",
            desc_key="nav.reboot_screen_desc",
            default_title="Restart Screen",
            default_desc="Quick safe screen restart",
            view_class=RebootScreenView
        ))

        # 5. Backup & Maintenance
        self.register_view(ViewDescriptor(
            id="backup",
            category_id="backup_maintenance",
            icon="💾",
            title_key="nav.backup_title",
            desc_key="nav.backup_desc",
            default_title="Backup",
            default_desc="Save full car backup to PC",
            view_class=BackupView,
            init_kwargs_factory=lambda p: {"backups_dir": BACKUPS_DIR}
        ))
        self.register_view(ViewDescriptor(
            id="restore",
            category_id="backup_maintenance",
            icon="📥",
            title_key="nav.restore_title",
            desc_key="nav.restore_desc",
            default_title="Restore",
            default_desc="Restore saved apps & settings",
            view_class=RestoreView,
            init_kwargs_factory=lambda p: {"backups_dir": BACKUPS_DIR}
        ))
        self.register_view(ViewDescriptor(
            id="factory_reset",
            category_id="backup_maintenance",
            icon="⚠️",
            title_key="nav.factory_reset_title",
            desc_key="nav.factory_reset_desc",
            default_title="Factory Reset",
            default_desc="100% clean dealership reset",
            view_class=FactoryResetView,
            init_kwargs_factory=lambda p: {"factory_backup_dir": FACTORY_BACKUP_DIR}
        ))
        self.register_view(ViewDescriptor(
            id="fetch_logs",
            category_id="backup_maintenance",
            icon="📋",
            title_key="nav.fetch_logs_title",
            desc_key="nav.fetch_logs_desc",
            default_title="Fetch Logs",
            default_desc="Get diagnostic error logs",
            view_class=FetchLogsView
        ))

        # 6. About & Supported Systems
        self.register_view(ViewDescriptor(
            id="about",
            category_id="about_system",
            icon="ℹ️",
            title_key="nav.about_title",
            desc_key="nav.about_desc",
            default_title="About Aero Suite",
            default_desc="Tested models & hardware specs",
            view_class=AboutView,
            hide_terminal=True
        ))

        # 7. Aero Partners & R&D
        self.register_view(ViewDescriptor(
            id="roadmap",
            category_id="community_support",
            icon="🚀",
            title_key="roadmap.nav_title",
            desc_key="roadmap.nav_desc",
            default_title="رؤية Aero القادمة 🚀",
            default_desc="خارطة طريق ومفاجآت الإصدار v2.0",
            view_class=RoadmapView,
            hide_terminal=True
        ))
        self.register_view(ViewDescriptor(
            id="support",
            category_id="community_support",
            icon="🤝",
            title_key="support.nav_title",
            desc_key="support.nav_desc",
            default_title="Aero Partners ⚡",
            default_desc="Support & invest in development",
            view_class=SupportView,
            hide_terminal=True
        ))


def get_view_registry() -> ViewRegistry:
    """Returns the singleton ViewRegistry instance."""
    return ViewRegistry.get_instance()
