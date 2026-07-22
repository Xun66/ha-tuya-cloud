# Tuya MQ Exploration

This branch explores whether Tuya Message Service/OpenMQ can improve the
current cloud polling path.

## Current Baseline

The `main` branch reads the meter by polling:

```text
GET /v2.0/cloud/thing/{device_id}/shadow/properties
```

That path is already verified for the two-circuit meter and exposes the channel
power/current/voltage/energy values.

## Why MQ Is Not In Main Yet

Tuya's message service can push device status changes, but this meter still
needs to be tested against the real message stream. The important unknowns are:

- Whether `cur_power1`, `cur_power2`, current, voltage, and energy datapoints
  are actually pushed for this device.
- Whether a Tuya Cloud project token plus the linked app user ID is enough to
  obtain OpenMQ access configuration.
- Whether Home Assistant should depend on Tuya's old Python SDK, use direct
  OpenMQ calls, or keep MQ as an optional fast path.

The likely production design is:

- Read shadow once on startup.
- Listen to MQ for faster updates.
- Keep slow shadow polling as a fallback and reconciliation path.

## Probe Script

Use `tools/tuya_mq_probe.py` to test the direct OpenMQ route without committing
credentials.

Required environment variables:

```text
TUYA_ACCESS_ID
TUYA_ACCESS_SECRET
TUYA_APP_USER_ID
TUYA_DEVICE_ID
```

Optional environment variables:

```text
TUYA_REGION=cn
TUYA_DURATION=300
```

Install probe-only dependencies:

```bash
python3 -m pip install requests paho-mqtt pycryptodome
```

Run:

```bash
TUYA_ACCESS_ID=... \
TUYA_ACCESS_SECRET=... \
TUYA_APP_USER_ID=... \
TUYA_DEVICE_ID=... \
TUYA_REGION=cn \
python3 tools/tuya_mq_probe.py
```

Watch for messages whose payload `data.devId` matches the meter device ID. A
useful result should contain pushed status entries for the same codes already
read from shadow, for example `cur_power1`, `cur_power2`, `cur_current1`, or
`cur_voltage2`.

## References

- Tuya Service SDK list: https://developer.tuya.com/en/docs/iot/server-sdk?id=Kbw09frvx48db
- Tuya Message Service integration: https://developer.tuya.com/en/docs/iot/integrate-mq?id=Kavqdgattt1y2
- Tuya Python SDK message subscription example: https://developer.tuya.com/cn/docs/iot/device-control-best-practice?id=Ka72202tz4m67
- Tuya IoT Python SDK: https://pypi.org/project/tuya-iot-py-sdk/
