# Tuya Shadow Meter

Home Assistant custom integration for a Tuya two-channel current-transformer
electricity meter.

This integration is intentionally narrow. It targets the Tuya product
`79a7z01v3n35kytb` / 双路电流互感计量器（WiFi版） and exposes its cloud shadow
properties as Home Assistant sensors.

## Why Cloud Push

The meter exposes a TCP listener on Tuya's local LAN port, but current public
local protocol implementations did not return usable datapoints for this device.
The Tuya Cloud 2.0 shadow API does expose the meter values, and the official
Home Assistant Tuya integration uses Tuya's device sharing SDK with cloud push.

This integration follows that route:

- QR-code login using the Smart Life / Tuya Smart app.
- Initial state read from Tuya cloud.
- Live updates through the Tuya sharing SDK MQTT connection.
- A slow fallback refresh every six hours.

## Installation

### HACS

1. Add this repository as a custom HACS integration repository.
2. Install **Tuya Shadow Meter**.
3. Restart Home Assistant.
4. Add the integration from **Settings > Devices & services**.

### Manual

Copy `custom_components/tuya_shadow_meter` into your Home Assistant
`custom_components` directory and restart Home Assistant.

## Setup

The config flow asks for:

- **User Code**: The user code from the Smart Life / Tuya Smart app.
- **Device ID**: Optional. Leave blank to use the first supported meter found in
  the scanned account.

After submitting the user code, scan the QR code with the Tuya app and submit
the scan step in Home Assistant.

## Sensors

The integration creates sensors for:

- Channel 1 and channel 2 state
- Channel 1 and channel 2 power
- Channel 1 and channel 2 current
- Channel 1 and channel 2 voltage
- Channel 1 and channel 2 total energy
- Channel 1 and channel 2 today's energy
- Channel 1 and channel 2 power warning type/value
- Total energy
- Network state

## Notes

- This is not a generic Tuya integration.
- Local LAN control is deliberately not used.
- Control commands are not implemented; the meter is read-only in Home Assistant.
- The integration depends on `tuya-device-sharing-sdk==0.2.10`, the same family
  of SDK used by Home Assistant's official Tuya integration.
