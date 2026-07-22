#!/usr/bin/env python3
"""Probe Tuya OpenMQ messages for the two-circuit meter.

This script is intentionally standalone and reads credentials only from
environment variables. It is for exploration, not for Home Assistant runtime
use.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import hmac
import json
import os
import signal
import sys
import time
import uuid
from typing import Any
from urllib.parse import urlsplit

try:
    from Crypto.Cipher import AES
except ImportError as err:
    raise SystemExit(
        "Missing dependency: pycryptodome. Install with "
        "`python3 -m pip install pycryptodome`."
    ) from err

try:
    import paho.mqtt.client as mqtt
except ImportError as err:
    raise SystemExit(
        "Missing dependency: paho-mqtt. Install with "
        "`python3 -m pip install paho-mqtt`."
    ) from err

try:
    import requests
except ImportError as err:
    raise SystemExit(
        "Missing dependency: requests. Install with "
        "`python3 -m pip install requests`."
    ) from err


ENDPOINTS = {
    "cn": "https://openapi.tuyacn.com",
    "us": "https://openapi.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "in": "https://openapi.tuyain.com",
}

TOKEN_PATH = "/v1.0/token?grant_type=1"
CUSTOM_OPEN_HUB_PATH = "/v1.0/iot-03/open-hub/access-config"
SMART_HOME_OPEN_HUB_PATH = "/v1.0/open-hub/access/config"
GCM_TAG_LENGTH = 16


@dataclass
class ProbeConfig:
    """Probe configuration."""

    access_id: str
    access_secret: str
    app_user_id: str
    device_id: str
    region: str
    duration: int

    @property
    def base_url(self) -> str:
        """Return the Tuya OpenAPI base URL."""
        return ENDPOINTS[self.region]


@dataclass
class OpenHubConfig:
    """Tuya OpenMQ access configuration."""

    url: str
    client_id: str
    username: str
    password: str
    source_topic: dict[str, str]
    encrypted_version: str


class TuyaProjectOpenApi:
    """Small OpenAPI client for project-token OpenMQ probing."""

    def __init__(self, config: ProbeConfig) -> None:
        """Initialize the client."""
        self.config = config
        self.access_token = ""
        self.expire_at = 0.0
        self.session = requests.Session()

    def ensure_token(self) -> None:
        """Ensure a project access token is available."""
        if self.access_token and self.expire_at - 60 > time.time():
            return

        response = self.request("GET", TOKEN_PATH, use_token=False)
        result = response.get("result", {})
        self.access_token = result["access_token"]
        self.expire_at = time.time() + int(result.get("expire_time", 0))

    def open_hub_config(self) -> OpenHubConfig:
        """Try to obtain OpenMQ access configuration."""
        self.ensure_token()
        body = {
            "uid": self.config.app_user_id,
            "link_id": f"ha-tuya-cloud-probe.{uuid.uuid4()}",
            "link_type": "mqtt",
            "topics": "device",
            "msg_encrypted_version": "2.0",
        }

        response = self.request("POST", CUSTOM_OPEN_HUB_PATH, body=body)
        if response.get("success"):
            return _parse_open_hub_config(response, "2.0")

        print(
            "Custom OpenHub config failed:",
            json.dumps(_redact_response(response), ensure_ascii=False),
            file=sys.stderr,
        )

        fallback_body = dict(body)
        fallback_body["msg_encrypted_version"] = "1.0"
        response = self.request("POST", SMART_HOME_OPEN_HUB_PATH, body=fallback_body)
        if response.get("success"):
            return _parse_open_hub_config(response, "1.0")

        raise RuntimeError(
            "Unable to obtain OpenMQ config: "
            + json.dumps(_redact_response(response), ensure_ascii=False)
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        use_token: bool = True,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a signed Tuya OpenAPI request."""
        body_json = "" if body is None else json.dumps(body, separators=(",", ":"))
        token = self.access_token if use_token else ""
        timestamp = str(int(time.time() * 1000))
        payload = (
            self.config.access_id
            + token
            + timestamp
            + method
            + "\n"
            + hashlib.sha256(body_json.encode("utf-8")).hexdigest()
            + "\n\n/"
            + path.lstrip("/")
        )
        signature = hmac.new(
            self.config.access_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()
        headers = {
            "client_id": self.config.access_id,
            "sign": signature,
            "t": timestamp,
            "sign_method": "HMAC-SHA256",
        }
        if token:
            headers["access_token"] = token
        if body is not None:
            headers["Content-Type"] = "application/json"

        response = self.session.request(
            method,
            self.config.base_url + path,
            data=body_json if body is not None else None,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()


class MqProbe:
    """MQTT probe for Tuya OpenMQ."""

    def __init__(self, config: ProbeConfig, mq_config: OpenHubConfig) -> None:
        """Initialize the probe."""
        self.config = config
        self.mq_config = mq_config
        self.message_count = 0
        self.device_message_count = 0
        self.done = False
        self.client: mqtt.Client | None = None

    def run(self) -> None:
        """Connect and listen for the requested duration."""
        url = urlsplit(self.mq_config.url)
        print(f"Connecting to {url.hostname}:{url.port} ({url.scheme})")
        print("Subscribing to:", ", ".join(self.mq_config.source_topic.values()))

        client = mqtt.Client(client_id=self.mq_config.client_id)
        self.client = client
        client.username_pw_set(self.mq_config.username, self.mq_config.password)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect

        if url.scheme == "ssl":
            client.tls_set()

        client.connect(url.hostname, url.port)
        client.loop_start()

        deadline = time.time() + self.config.duration
        try:
            while not self.done and time.time() < deadline:
                time.sleep(0.5)
        finally:
            client.loop_stop()
            client.disconnect()

        print(
            f"Done. total_messages={self.message_count} "
            f"device_messages={self.device_message_count}"
        )

    def stop(self, *_args: Any) -> None:
        """Request probe shutdown."""
        self.done = True

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: Any,
        _flags: Any,
        reason_code: Any,
        *_args: Any,
    ) -> None:
        rc = int(reason_code)
        if rc != 0:
            print(f"MQTT connect failed rc={rc}", file=sys.stderr)
            self.done = True
            return

        print("MQTT connected")
        for topic in self.mq_config.source_topic.values():
            client.subscribe(topic)

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        reason_code: Any,
        *_args: Any,
    ) -> None:
        rc = int(reason_code)
        if rc:
            print(f"MQTT disconnected rc={rc}", file=sys.stderr)

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: Any) -> None:
        self.message_count += 1
        raw = json.loads(msg.payload.decode("utf-8"))
        decoded = decode_message(raw, self.mq_config)
        data = decoded.get("data", {})
        dev_id = data.get("devId") or data.get("dev_id")
        is_target = dev_id == self.config.device_id
        if is_target:
            self.device_message_count += 1

        print(
            json.dumps(
                {
                    "topic": msg.topic,
                    "target_device": is_target,
                    "message": decoded,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )


def decode_message(raw: dict[str, Any], mq_config: OpenHubConfig) -> dict[str, Any]:
    """Decode a Tuya OpenMQ payload."""
    encrypted_data = raw.get("data")
    if not isinstance(encrypted_data, str):
        return raw

    key = mq_config.password[8:24].encode("utf-8")
    if mq_config.encrypted_version == "1.0":
        cipher = AES.new(key, AES.MODE_ECB)
        decrypted = cipher.decrypt(base64.b64decode(encrypted_data))
        padding = decrypted[-1]
        raw["data"] = json.loads(decrypted[:-padding])
        return raw

    buffer = base64.b64decode(encrypted_data)
    iv_length = int.from_bytes(buffer[0:4], byteorder="big")
    iv = buffer[4 : iv_length + 4]
    ciphertext = buffer[iv_length + 4 : len(buffer) - GCM_TAG_LENGTH]
    tag = buffer[len(buffer) - GCM_TAG_LENGTH :]
    aad = str(raw.get("t", "")).encode("utf-8")
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    cipher.update(aad)
    raw["data"] = json.loads(cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8"))
    return raw


def _parse_open_hub_config(response: dict[str, Any], encrypted_version: str) -> OpenHubConfig:
    result = response.get("result", {})
    return OpenHubConfig(
        url=result["url"],
        client_id=result["client_id"],
        username=result["username"],
        password=result["password"],
        source_topic=result.get("source_topic", {}),
        encrypted_version=encrypted_version,
    )


def _redact_response(response: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(response)
    result = redacted.get("result")
    if isinstance(result, dict):
        redacted["result"] = {
            key: "***" if key in {"password", "username", "client_id"} else value
            for key, value in result.items()
        }
    return redacted


def load_config() -> ProbeConfig:
    """Load probe configuration from environment variables."""
    missing = [
        key
        for key in (
            "TUYA_ACCESS_ID",
            "TUYA_ACCESS_SECRET",
            "TUYA_APP_USER_ID",
            "TUYA_DEVICE_ID",
        )
        if not os.environ.get(key)
    ]
    if missing:
        raise SystemExit("Missing environment variables: " + ", ".join(missing))

    region = os.environ.get("TUYA_REGION", "cn")
    if region not in ENDPOINTS:
        raise SystemExit(f"Unsupported TUYA_REGION={region!r}")

    return ProbeConfig(
        access_id=os.environ["TUYA_ACCESS_ID"],
        access_secret=os.environ["TUYA_ACCESS_SECRET"],
        app_user_id=os.environ["TUYA_APP_USER_ID"],
        device_id=os.environ["TUYA_DEVICE_ID"],
        region=region,
        duration=int(os.environ.get("TUYA_DURATION", "300")),
    )


def main() -> None:
    """Run the probe."""
    config = load_config()
    api = TuyaProjectOpenApi(config)
    mq_config = api.open_hub_config()
    probe = MqProbe(config, mq_config)
    signal.signal(signal.SIGINT, probe.stop)
    signal.signal(signal.SIGTERM, probe.stop)
    probe.run()


if __name__ == "__main__":
    main()
