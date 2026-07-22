# Tuya Shadow Meter

<p align="center">
  <img src="IMG_2957.png" alt="Tuya Shadow Meter icon" width="160">
</p>

Home Assistant custom integration for a Tuya two-channel
current-transformer electricity meter.

This project is intentionally narrow. It targets the Tuya product
`79a7z01v3n35kytb`, seen as `Double Digital Meter` / `双路互感计量器`, and
exposes the meter's Tuya Cloud shadow properties as Home Assistant sensors.

## What It Does

- Reads the device through Tuya Cloud OpenAPI.
- Exposes channel 1 and channel 2 power, current, voltage, and energy sensors.
- Uses fixed English entity names such as `Channel 1 power` and
  `Channel 2 power`.
- Polls every 60 seconds.
- Does not use Tuya QR-code login.
- Does not use Tuya local LAN control.
- Does not implement write/control commands.

## Why Cloud OpenAPI

The meter exposes Tuya's local LAN port, but the current public local Tuya
protocol implementations did not return usable datapoints for this device.
The Tuya Cloud 2.0 shadow API does expose the meter values reliably, so this
integration uses OpenAPI shadow reads instead of trying to force a local
protocol path.

## Installation

### HACS

1. In HACS, add this repository as a custom repository.
2. Select category **Integration**.
3. Install **Tuya Shadow Meter**.
4. Restart Home Assistant.
5. Add **Tuya Shadow Meter** from **Settings > Devices & services**.

### Manual

Copy `custom_components/tuya_shadow_meter` into your Home Assistant
`custom_components` directory and restart Home Assistant.

## Setup

Create or use a Tuya Cloud project that can access the target device, then add
the integration in Home Assistant. The config flow asks for:

| Field | Description |
| --- | --- |
| Device ID | The Tuya device ID for the meter. |
| Cloud Access ID | Tuya Cloud project Access ID. |
| Cloud Access Secret | Tuya Cloud project Access Secret. |
| Cloud App User ID | The app user ID linked to the device. |
| Cloud Region | Tuya data center region, usually `cn` for China. |

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
`icon.png` at the repository root and under
`custom_components/tuya_shadow_meter/icon.png` for HACS/Home Assistant display.

## Limitations

- This is not a generic Tuya integration.
- Only the targeted two-channel electricity meter is supported.
- Cloud connectivity and Tuya OpenAPI availability are required.
- The integration is read-only.
