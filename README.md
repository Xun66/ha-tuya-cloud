# Tuya Cloud

<p align="center">
  <img src="IMG_2957.png" alt="Tuya Cloud icon" width="160">
</p>

<p align="center">
  <a href="README.zh-Hans.md">中文说明</a>
</p>

Home Assistant custom integration for selected Tuya devices that expose useful
MQTT updates through Tuya's sharing API.

The current built-in device profile targets the Tuya product
`79a7z01v3n35kytb`, seen in Tuya as `Double Digital Meter` /
`双路互感计量器`. Additional devices can be added by contributing a product
profile with its MQTT datapoint mapping.

## What It Does

- Logs in with the same QR-code flow used by Home Assistant's official Tuya integration.
- Discovers supported devices from your Tuya/Smart Life account.
- Updates sensors from Tuya MQTT push messages.
- Exposes channel 1 and channel 2 power, current, voltage, and energy sensors.
- Uses fixed English entity names such as `Channel 1 power` and
  `Channel 2 power`.
- Does not require Tuya Cloud Access ID / Access Secret.
- Does not use Tuya local LAN control.
- Does not actively poll device values.
- Does not implement write/control commands.

## Demo

After setup, Home Assistant shows supported devices with their mapped sensors.

![Home Assistant meter demo](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/demo.jpg)

## Why MQ

The first supported device exposes Tuya's local LAN port, but the public local
Tuya protocol implementations tested so far did not return usable datapoints for
it. Tuya MQTT pushes usable `protocol=4` datapoints, including both channel
power/current/voltage and energy values.

The integration is MQ-only. Initial sensor values can remain unavailable until
the first MQTT status push arrives. Opening the device page in the Tuya app
usually triggers faster updates.

## Installation

### HACS

1. In HACS, add this repository as a custom repository.
2. Select category **Integration**.
3. Install **Tuya Cloud**.
4. Restart Home Assistant.
5. Add **Tuya Cloud** from **Settings > Devices & services**.

### Manual

Copy `custom_components/tuya_shadow_meter` into your Home Assistant
`custom_components` directory and restart Home Assistant.

## Home Assistant Setup

1. Open the Smart Life or Tuya app.
2. Find **User Code** in the app account/settings area.
3. Add **Tuya Cloud** from **Settings > Devices & services**.
4. Enter the User Code.
5. Scan the QR code with the same Tuya app.

Supported devices are discovered automatically after login.

## Sensors

The main enabled sensors are:

| Sensor | Unit |
| --- | --- |
| Channel 1 power | W |
| Channel 1 current | A |
| Channel 1 voltage | V |
| Channel 1 total energy | kWh |
| Channel 1 energy today | kWh |
| Channel 2 power | W |
| Channel 2 current | A |
| Channel 2 voltage | V |
| Channel 2 total energy | kWh |
| Channel 2 energy today | kWh |
| Total energy | kWh |

Diagnostic sensors are also available for device state, power state, warning
power thresholds, and cloud connection state.

## Icon

The project icon is based on `IMG_2957.png`. The same image is also included as
`icon.png` at the repository root for HACS display and under
`custom_components/tuya_shadow_meter/brand/icon.png` for Home Assistant's local
brands endpoint.

## Limitations

- Only devices with a matching built-in profile are supported.
- It is not a generic Tuya integration.
- Tuya cloud connectivity and MQTT availability are required.
- Initial sensor values depend on the first MQTT status push.
- The integration is read-only.

## Contributing

Contributions are welcome. Device reports, Tuya MQTT payload samples, sensor
mapping fixes, documentation improvements, and support for additional compatible
devices are all appreciated.

## License

This project is released under the MIT License. See `LICENSE` for details.
