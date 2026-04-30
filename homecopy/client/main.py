"""Command-line client for validating the HomeCopy protocol."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone

from homecopy.client.config import ClientConfig
from homecopy.client.network.client import HomeCopyClient
from homecopy.client.services.clipboard_service import ClipboardService
from homecopy.client.services.history_service import HistoryService
from homecopy.client.services.notification_service import NotificationService
from homecopy.shared.models import ErrorMessage, HistoryRecord, IncomingTextMessage, SendAckMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def interactive_shell(client: HomeCopyClient, history_service: HistoryService, config: ClientConfig) -> None:
    clipboard = ClipboardService()
    notifier = NotificationService()
    online_devices: list[dict] = []

    async def handle_device_list(devices: list[dict]) -> None:
        nonlocal online_devices
        online_devices = [item for item in devices if item["device_id"] != config.device_id]
        print("\n[device_list]")
        if not online_devices:
            print("  No other devices online.")
            return
        for item in online_devices:
            print(f"  {item['device_id']}: {item['device_name']}")

    async def handle_incoming_text(message: IncomingTextMessage) -> None:
        print(f"\n[incoming] from={message.from_} text={message.text}")
        if config.auto_copy_on_receive:
            try:
                clipboard.copy_text(message.text)
                print("  Clipboard updated.")
            except Exception as exc:
                print(f"  Clipboard update failed: {exc}")

        if config.show_notification:
            notifier.notify("HomeCopy", f"New text from {message.from_name}")

        history_service.append(
            HistoryRecord(
                direction="received",
                peer_device_id=message.from_,
                peer_device_name=message.from_name,
                text=message.text,
                created_at=datetime.now(timezone.utc),
            )
        )

    async def handle_ack(message: SendAckMessage) -> None:
        print(f"\n[ack] request_id={message.request_id} status={message.status}")

    async def handle_error(message: ErrorMessage) -> None:
        print(f"\n[error] code={message.code} message={message.message}")

    async def handle_status(status: str) -> None:
        print(f"\n[status] {status}")

    client.on_device_list = handle_device_list
    client.on_incoming_text = handle_incoming_text
    client.on_ack = handle_ack
    client.on_error = handle_error
    client.on_status = handle_status

    connection_task = asyncio.create_task(client.connect_forever())

    print("Commands: devices | send <device_id> <text> | history | quit")

    try:
        while True:
            raw = await asyncio.to_thread(input, "\n> ")
            command = raw.strip()
            if not command:
                continue
            if command == "quit":
                break
            if command == "devices":
                if not online_devices:
                    print("No devices online.")
                else:
                    for item in online_devices:
                        print(f"{item['device_id']}: {item['device_name']}")
                continue
            if command == "history":
                records = history_service.load()
                if not records:
                    print("No history.")
                else:
                    for item in records:
                        print(
                            f"{item.created_at.isoformat()} {item.direction} "
                            f"{item.peer_device_id} {item.text}"
                        )
                continue
            if command.startswith("send "):
                _, remainder = command.split(" ", 1)
                try:
                    target_device_id, text = remainder.split(" ", 1)
                except ValueError:
                    print("Usage: send <device_id> <text>")
                    continue
                await client.send_text(target_device_id=target_device_id, text=text)
                peer_name = next(
                    (item["device_name"] for item in online_devices if item["device_id"] == target_device_id),
                    target_device_id,
                )
                history_service.append(
                    HistoryRecord(
                        direction="sent",
                        peer_device_id=target_device_id,
                        peer_device_name=peer_name,
                        text=text,
                        created_at=datetime.now(timezone.utc),
                    )
                )
                continue
            print("Unknown command.")
    finally:
        await client.close()
        connection_task.cancel()
        try:
            await connection_task
        except asyncio.CancelledError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HomeCopy CLI client")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ClientConfig.load(args.config)
    history_service = HistoryService(config.history_path, config.history_limit)
    client = HomeCopyClient(config)
    asyncio.run(interactive_shell(client, history_service, config))


if __name__ == "__main__":
    main()
