from PySide6.QtWidgets import QApplication

from objectsnip.app import application_icon

_APP = QApplication.instance() or QApplication([])


def test_packaged_application_icon_loads() -> None:
    icon = application_icon()

    assert not icon.isNull()
    assert icon.actualSize(icon.availableSizes()[0]).width() == 512
