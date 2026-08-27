import pytest
from PySide6.QtDBus import QDBusVariant

from objectsnip.capture.portal import screenshot_path_from_results, unwrap_dbus_value


def test_unwrap_dbus_variant() -> None:
    assert unwrap_dbus_value(QDBusVariant("value")) == "value"
    assert unwrap_dbus_value("value") == "value"


def test_screenshot_path_from_results() -> None:
    assert (
        screenshot_path_from_results(
            {"uri": QDBusVariant("file:///tmp/objectsnip.png")}
        )
        == "/tmp/objectsnip.png"
    )


@pytest.mark.parametrize(
    "results",
    [{}, {"uri": ""}, {"uri": "https://example.com/image.png"}],
)
def test_screenshot_path_rejects_invalid_results(results: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        screenshot_path_from_results(results)
