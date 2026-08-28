from __future__ import annotations

import asyncio
from concurrent.futures import Future
from threading import Thread
from uuid import uuid4

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType, MessageType
from dbus_next.message import Message
from dbus_next.signature import Variant
from PySide6.QtCore import QObject, Signal, Slot

PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
GLOBAL_SHORTCUTS_INTERFACE = "org.freedesktop.portal.GlobalShortcuts"
REQUEST_INTERFACE = "org.freedesktop.portal.Request"
SESSION_INTERFACE = "org.freedesktop.portal.Session"
SHORTCUT_ID = "capture-region"
PREFERRED_TRIGGER = "LOGO+SHIFT+o"


def request_path(unique_name: str, token: str) -> str:
    sender = unique_name.removeprefix(":").replace(".", "_")
    return f"{PORTAL_PATH}/request/{sender}/{token}"


def response_results(message: Message) -> dict[str, Variant]:
    if message.message_type is not MessageType.SIGNAL or len(message.body) != 2:
        raise ValueError("invalid desktop portal response")
    response, results = message.body
    if response != 0 or not isinstance(results, dict):
        raise RuntimeError("desktop shortcut registration was not approved")
    return results


class PortalGlobalShortcutService(QObject):
    activated = Signal()
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_future: Future[None] | None = None
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_future = Future()
        self._thread = Thread(target=self._run, name="objectsnip-shortcut", daemon=True)
        self._thread.start()

    @Slot()
    def stop(self) -> None:
        if (
            self._loop is not None
            and self._stop_future is not None
            and not self._stop_future.done()
        ):
            self._loop.call_soon_threadsafe(self._stop_future.set_result, None)

    def _run(self) -> None:
        try:
            asyncio.run(self._serve())
        except Exception as exc:  # the portal is optional platform infrastructure
            self.failed.emit(str(exc))
        finally:
            self._loop = None
            self._thread = None

    async def _serve(self) -> None:
        self._loop = asyncio.get_running_loop()
        bus = await MessageBus(bus_type=BusType.SESSION).connect()
        session_path: str | None = None
        responses: dict[str, asyncio.Future[Message]] = {}

        def handle_message(message: Message) -> None:
            if message.interface == REQUEST_INTERFACE and message.member == "Response":
                future = responses.get(message.path)
                if future is not None and not future.done():
                    future.set_result(message)
                return
            if (
                message.interface == GLOBAL_SHORTCUTS_INTERFACE
                and message.member == "Activated"
                and len(message.body) >= 2
                and message.body[0] == session_path
                and message.body[1] == SHORTCUT_ID
            ):
                self.activated.emit()

        bus.add_message_handler(handle_message)
        try:
            await self._add_signal_match(bus, REQUEST_INTERFACE)
            await self._add_signal_match(bus, GLOBAL_SHORTCUTS_INTERFACE)
            session_path = await self._create_session(bus, responses)
            await self._bind_shortcut(bus, session_path, responses)
            if self._stop_future is not None:
                await asyncio.wrap_future(self._stop_future)
        finally:
            if session_path is not None:
                await bus.call(
                    Message(
                        destination=PORTAL_SERVICE,
                        path=session_path,
                        interface=SESSION_INTERFACE,
                        member="Close",
                    )
                )
            bus.disconnect()

    async def _create_session(
        self,
        bus: MessageBus,
        responses: dict[str, asyncio.Future[Message]],
    ) -> str:
        token = f"objectsnip_{uuid4().hex}"
        response = await self._portal_request(
            bus,
            responses,
            token,
            "CreateSession",
            "a{sv}",
            [
                {
                    "handle_token": Variant("s", token),
                    "session_handle_token": Variant("s", f"session_{token}"),
                }
            ],
        )
        session = response_results(response).get("session_handle")
        if session is None or not isinstance(session.value, str):
            raise RuntimeError("the shortcut portal returned an invalid session")
        return session.value

    async def _bind_shortcut(
        self,
        bus: MessageBus,
        session_path: str,
        responses: dict[str, asyncio.Future[Message]],
    ) -> None:
        token = f"objectsnip_{uuid4().hex}"
        await self._portal_request(
            bus,
            responses,
            token,
            "BindShortcuts",
            "oa(sa{sv})sa{sv}",
            [
                session_path,
                [
                    [
                        SHORTCUT_ID,
                        {
                            "description": Variant("s", "Capture region"),
                            "preferred_trigger": Variant("s", PREFERRED_TRIGGER),
                        },
                    ]
                ],
                "",
                {"handle_token": Variant("s", token)},
            ],
        )

    async def _portal_request(
        self,
        bus: MessageBus,
        responses: dict[str, asyncio.Future[Message]],
        token: str,
        member: str,
        signature: str,
        body: list[object],
    ) -> Message:
        if bus.unique_name is None:
            raise RuntimeError("the desktop portal session bus is unavailable")
        path = request_path(bus.unique_name, token)
        future = asyncio.get_running_loop().create_future()
        responses[path] = future
        reply = await bus.call(
            Message(
                destination=PORTAL_SERVICE,
                path=PORTAL_PATH,
                interface=GLOBAL_SHORTCUTS_INTERFACE,
                member=member,
                signature=signature,
                body=body,
            )
        )
        if reply is None or reply.message_type is MessageType.ERROR:
            error = reply.body[0] if reply is not None and reply.body else member
            raise RuntimeError(str(error))
        try:
            return await future
        finally:
            responses.pop(path, None)

    @staticmethod
    async def _add_signal_match(bus: MessageBus, interface: str) -> None:
        reply = await bus.call(
            Message(
                destination="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                interface="org.freedesktop.DBus",
                member="AddMatch",
                signature="s",
                body=[
                    f"type='signal',sender='{PORTAL_SERVICE}',interface='{interface}'"
                ],
            )
        )
        if reply is None or reply.message_type is MessageType.ERROR:
            raise RuntimeError("could not subscribe to the shortcut portal")
