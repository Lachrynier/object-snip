"""Desktop-wide shortcut integration."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from objectsnip.shortcuts.portal import PortalGlobalShortcutService

if TYPE_CHECKING:
    from objectsnip.shortcuts.windows import WindowsGlobalShortcutService


def create_global_shortcut_service(
    parent: QObject | None = None,
) -> PortalGlobalShortcutService | WindowsGlobalShortcutService:
    if sys.platform == "win32":
        from objectsnip.shortcuts.windows import WindowsGlobalShortcutService

        return WindowsGlobalShortcutService(parent)
    return PortalGlobalShortcutService(parent)
