"""FastAPI application for the HomeCopy relay server."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status

from homecopy.server.auth import is_valid_token
from homecopy.server.config import get_settings
from homecopy.server.connection_manager import ConnectionManager
from homecopy.server.discovery import LanDiscoveryBroadcaster
from homecopy.server.logging_setup import setup_logging
from homecopy.server.protocol import parse_register_message, parse_send_text_message
from homecopy.shared.constants import (
    ERROR_AUTH_FAILED,
    ERROR_DEVICE_OFFLINE,
    ERROR_INTERNAL_ERROR,
    ERROR_INVALID_MESSAGE,
    ERROR_TEXT_TOO_LONG,
)
from homecopy.shared.models import ErrorMessage, IncomingTextMessage, RegisterOkMessage, SendAckMessage

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title="HomeCopy Relay Server", version="0.9.0")
manager = ConnectionManager()
discovery_broadcaster = LanDiscoveryBroadcaster(settings)


async def send_error(websocket: WebSocket, code: str, message: str) -> None:
    payload = ErrorMessage(code=code, message=message).model_dump(mode="json")
    await websocket.send_json(payload)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
async def stats() -> dict[str, int | str]:
    return {
        "status": "ok",
        "connected_clients": manager.connection_count(),
    }


@app.on_event("startup")
async def on_startup() -> None:
    await discovery_broadcaster.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await discovery_broadcaster.stop()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    registered_device_id: str | None = None

    try:
        initial_payload = await websocket.receive_json()
        register_message = parse_register_message(initial_payload)

        if not is_valid_token(settings.auth_token, register_message.token):
            await send_error(websocket, ERROR_AUTH_FAILED, "Authentication failed.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        client_host = websocket.client.host if websocket.client else "unknown"
        registered_device_id = register_message.device_id
        await manager.register(
            websocket=websocket,
            device_id=register_message.device_id,
            device_name=register_message.device_name,
            remote_addr=client_host,
        )

        logger.info(
            "Device registered device_id=%s device_name=%s remote_addr=%s",
            register_message.device_id,
            register_message.device_name,
            client_host,
        )

        await websocket.send_json(
            RegisterOkMessage(
                self=register_message.device_id,
                online_devices=manager.get_device_list(exclude_device_id=register_message.device_id),
            ).model_dump(mode="json")
        )
        await manager.broadcast_device_list()

        while True:
            payload = await websocket.receive_json()
            message_type = payload.get("type")
            if message_type != "send_text":
                await send_error(websocket, ERROR_INVALID_MESSAGE, "Only send_text is supported after register.")
                continue

            send_message = parse_send_text_message(payload)
            if len(send_message.text) > settings.max_text_length:
                await send_error(
                    websocket,
                    ERROR_TEXT_TOO_LONG,
                    f"Text exceeds max length {settings.max_text_length}.",
                )
                continue

            target = manager.get(send_message.to)
            if target is None:
                await send_error(websocket, ERROR_DEVICE_OFFLINE, "Target device is offline.")
                continue

            incoming = IncomingTextMessage.model_validate(
                {
                    "message_id": uuid4(),
                    "from": register_message.device_id,
                    "from_name": register_message.device_name,
                    "text": send_message.text,
                    "sent_at": datetime.now(timezone.utc),
                }
            )
            await target.websocket.send_json(incoming.model_dump(by_alias=True, mode="json"))

            logger.info(
                "Text relayed from=%s to=%s length=%s",
                register_message.device_id,
                send_message.to,
                len(send_message.text),
            )

            ack = SendAckMessage(request_id=send_message.request_id, status="ok")
            await websocket.send_json(ack.model_dump(mode="json"))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected device_id=%s", registered_device_id)
    except ValueError as exc:
        logger.warning("Protocol validation failed device_id=%s error=%s", registered_device_id, exc)
        try:
            await send_error(websocket, ERROR_INVALID_MESSAGE, "Invalid message payload.")
        except Exception:
            logger.debug("Failed to send protocol error before disconnect")
    except Exception:
        logger.exception("Unhandled websocket error device_id=%s", registered_device_id)
        try:
            await send_error(websocket, ERROR_INTERNAL_ERROR, "Internal server error.")
        except Exception:
            logger.debug("Failed to send internal error before disconnect")
    finally:
        removed = await manager.unregister(websocket)
        if removed is not None:
            logger.info("Device unregistered device_id=%s", removed.device_id)
            await manager.broadcast_device_list()
