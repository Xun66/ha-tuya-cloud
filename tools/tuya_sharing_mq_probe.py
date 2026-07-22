#!/usr/bin/env python3
"""Probe Tuya sharing MQTT with the official QR-login flow.

This follows the same authentication family as Home Assistant's built-in Tuya
integration. It is intentionally a standalone exploration tool and does not
store tokens.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from tuya_sharing import LoginControl, Manager
except ImportError as err:
    raise SystemExit(
        "Missing dependency: tuya-device-sharing-sdk. Install with "
        "`python3 -m pip install tuya-device-sharing-sdk`."
    ) from err

TUYA_CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
TUYA_SCHEMA = "haauthorize"
QR_POLL_SECONDS = 2


class SharingMqProbe:
    """Run a QR-login Tuya sharing MQTT probe."""

    def __init__(self, user_code: str, device_id: str, duration: int) -> None:
        """Initialize the probe."""
        self.user_code = user_code
        self.device_id = device_id
        self.duration = duration
        self.done = False
        self.message_count = 0
        self.target_message_count = 0
        self.manager: Manager | None = None

    def run(self) -> None:
        """Login, subscribe to MQTT, and print messages."""
        login_info = self._login_with_qr()
        token_info = {
            "t": login_info["t"],
            "uid": login_info["uid"],
            "expire_time": login_info["expire_time"],
            "access_token": login_info["access_token"],
            "refresh_token": login_info["refresh_token"],
        }
        manager = Manager(
            TUYA_CLIENT_ID,
            self.user_code,
            login_info["terminal_id"],
            login_info["endpoint"],
            token_info,
        )
        self.manager = manager
        manager.update_device_cache()
        self._mark_target_device_for_subscription(manager)

        print("Known devices:")
        for device_id, device in manager.device_map.items():
            print(
                json.dumps(
                    {
                        "target": device_id == self.device_id,
                        "id": device_id,
                        "name": getattr(device, "name", None),
                        "category": getattr(device, "category", None),
                        "online": getattr(device, "online", None),
                        "support_local": getattr(device, "support_local", None),
                        "set_up": getattr(device, "set_up", None),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )

        manager.refresh_mq()
        if manager.mq is None:
            raise RuntimeError("Tuya sharing MQTT did not start")
        manager.mq.add_message_listener(self._on_message)

        deadline = time.time() + self.duration
        try:
            while not self.done and time.time() < deadline:
                time.sleep(0.5)
        finally:
            if manager.mq is not None:
                manager.mq.stop()

        print(
            f"Done. total_messages={self.message_count} "
            f"target_messages={self.target_message_count}"
        )

    def stop(self, *_args: Any) -> None:
        """Request shutdown."""
        self.done = True

    def _login_with_qr(self) -> dict[str, Any]:
        """Run Tuya QR login and return token info."""
        login_control = LoginControl()
        response = login_control.qr_code(TUYA_CLIENT_ID, TUYA_SCHEMA, self.user_code)
        if not response.get("success"):
            raise RuntimeError("QR code request failed: " + json.dumps(response))

        qr_token = response["result"]["qrcode"]
        qr_data = f"tuyaSmart--qrLogin?token={qr_token}"
        print("Scan this QR code with Smart Life or Tuya Smart:")
        print(qr_data)
        _try_write_qr_image(qr_data)

        while not self.done:
            ok, info = login_control.login_result(
                qr_token,
                TUYA_CLIENT_ID,
                self.user_code,
            )
            if ok:
                print("QR login succeeded.")
                return info
            print(
                "Waiting for QR login:",
                json.dumps(info, ensure_ascii=False, separators=(",", ":")),
            )
            time.sleep(QR_POLL_SECONDS)

        raise RuntimeError("QR login cancelled")

    def _mark_target_device_for_subscription(self, manager: Manager) -> None:
        """Tell the sharing SDK to subscribe to the target device topic."""
        device = manager.device_map.get(self.device_id)
        if device is None:
            print(f"Target device {self.device_id} was not found in sharing account.")
            return
        setattr(device, "set_up", True)

    def _on_message(self, msg: dict[str, Any]) -> None:
        """Print raw MQTT messages and mark target-device events."""
        self.message_count += 1
        data = msg.get("data", {})
        dev_id = data.get("devId") or data.get("dev_id")
        target = dev_id == self.device_id
        if target:
            self.target_message_count += 1

        print(
            json.dumps(
                {
                    "target_device": target,
                    "message": msg,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )


def _try_write_qr_image(qr_data: str) -> None:
    """Write a QR image when the optional qrcode package is available."""
    try:
        import qrcode
    except ImportError:
        print("Install `qrcode[pil]` to also write a PNG QR image.")
        return

    path = Path(tempfile.gettempdir()) / "tuya-sharing-mq-login.png"
    image = qrcode.make(qr_data)
    image.save(path)
    print(f"QR image: {path}")


def _load_required_env(name: str) -> str:
    """Load a required environment variable."""
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing environment variable: {name}")
    return value


def main() -> None:
    """Run the sharing MQTT probe."""
    probe = SharingMqProbe(
        user_code=_load_required_env("TUYA_USER_CODE"),
        device_id=_load_required_env("TUYA_DEVICE_ID"),
        duration=int(os.environ.get("TUYA_DURATION", "300")),
    )
    signal.signal(signal.SIGINT, probe.stop)
    signal.signal(signal.SIGTERM, probe.stop)
    probe.run()


if __name__ == "__main__":
    main()
