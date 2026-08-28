import pytest
from dbus_next.constants import MessageType
from dbus_next.message import Message
from dbus_next.signature import Variant

from objectsnip.shortcuts.portal import (
    PREFERRED_TRIGGER,
    request_path,
    response_results,
)


def test_preferred_trigger_uses_xdg_shortcut_syntax() -> None:
    assert PREFERRED_TRIGGER == "LOGO+SHIFT+o"


def test_request_path_uses_dbus_sender_name() -> None:
    assert (
        request_path(":1.42", "objectsnip_token")
        == "/org/freedesktop/portal/desktop/request/1_42/objectsnip_token"
    )


def test_response_results_returns_success_values() -> None:
    results = {"session_handle": Variant("s", "/session/path")}
    message = Message.new_signal(
        "/request", "test.Interface", "Response", "ua{sv}", [0, results]
    )

    assert response_results(message) == results


def test_response_results_rejects_cancelled_request() -> None:
    message = Message.new_signal(
        "/request", "test.Interface", "Response", "ua{sv}", [1, {}]
    )

    with pytest.raises(RuntimeError):
        response_results(message)


def test_response_results_rejects_non_signal() -> None:
    message = Message(message_type=MessageType.METHOD_RETURN, reply_serial=1)

    with pytest.raises(ValueError):
        response_results(message)
