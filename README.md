# Tuya Cloud

<p align="center">
  <img src="IMG_2957.png" alt="Tuya Cloud icon" width="160">
</p>

<p align="center">
  <a href="README.zh-Hans.md">中文说明</a>
</p>

Home Assistant custom integration for one currently supported Tuya meter device
that exposes useful MQTT updates through Tuya's sharing API.

For now, this integration only supports the Tuya product
`79a7z01v3n35kytb`, seen in Tuya as `Double Digital Meter` /
`双路互感计量器`. Support for other devices requires a new product profile and
MQTT datapoint mapping.

## What It Does

- Logs in with the same QR-code flow used by Home Assistant's official Tuya integration.
- Discovers the supported meter from your Tuya/Smart Life account.
- Updates sensors from Tuya MQTT push messages.
- Exposes channel 1 and channel 2 power, current, voltage, and energy sensors.
- Uses fixed English entity names such as `Channel 1 power` and
  `Channel 2 power`.
- Does not require Tuya Cloud Access ID / Access Secret.
- Does not use Tuya local LAN control.
- Does not actively poll device values.
- Does not implement write/control commands.

## Demo

After setup, Home Assistant shows the supported meter with its mapped sensors.

![Home Assistant meter demo](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/demo.jpg)

## Why MQ

The supported meter exposes Tuya's local LAN port, but the public local
Tuya protocol implementations tested so far did not return usable datapoints for
it. Tuya MQTT pushes usable `protocol=4` datapoints, including both channel
power/current/voltage and energy values.

The integration is MQ-only. Initial sensor values can remain unavailable until
the first MQTT status push arrives. Opening the device page in the Tuya app
usually triggers faster updates.

## Installation

### HACS

This integration is distributed as a HACS custom repository. It is not available
in the default HACS store search until you add the repository URL manually.

1. Open HACS.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/Xun66/ha-tuya-cloud` with category **Integration**.
4. Search for and install **Tuya Cloud** in HACS.
5. Restart Home Assistant.
6. Add **Tuya Cloud** from **Settings > Devices & services**.

### Manual

Copy `custom_components/tuya_shadow_meter` into your Home Assistant
`custom_components` directory and restart Home Assistant.

## Home Assistant Setup

1. Open the Smart Life or Tuya app.
2. Find **User Code** in the app account/settings area.
3. Add **Tuya Cloud** from **Settings > Devices & services**.
4. Enter the User Code.
5. Scan the QR code with the same Tuya app.

The supported meter is discovered automatically after login.

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

- Only one built-in device profile is supported for now:
  `79a7z01v3n35kytb` / `Double Digital Meter` / `双路互感计量器`.
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
