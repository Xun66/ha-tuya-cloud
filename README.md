# Tuya Cloud Two-Circuit Meter

<p align="center">
  <img src="IMG_2957.png" alt="Tuya Cloud Two-Circuit Meter icon" width="160">
</p>

<p align="center">
  <a href="README.zh-Hans.md">中文说明</a>
</p>

Home Assistant custom integration for one specific Tuya two-circuit
current-transformer electricity meter.

This custom integration is intentionally limited to the two-circuit meter for
now. It currently targets the Tuya product `79a7z01v3n35kytb`, seen in Tuya as
`Double Digital Meter` / `双路互感计量器`, and exposes its Tuya Cloud shadow
properties as Home Assistant sensors.

## What It Does

- Reads the meter through Tuya Cloud OpenAPI.
- Exposes channel 1 and channel 2 power, current, voltage, and energy sensors.
- Uses fixed English entity names such as `Channel 1 power` and
  `Channel 2 power`.
- Polls every 60 seconds.
- Does not use Tuya QR-code login.
- Does not use Tuya local LAN control.
- Does not implement write/control commands.

## Why Cloud OpenAPI

This meter exposes Tuya's local LAN port, but the public local Tuya protocol
implementations tested so far did not return usable datapoints for this device.
The Tuya Cloud 2.0 shadow API exposes the values reliably, so this integration
uses OpenAPI shadow reads instead of forcing a local protocol path.

The **Device Status Notification** permission can be enabled in the Tuya Cloud
project, but this release does not consume push messages yet. It uses shadow
polling first, because that path is already verified for this meter.

## Installation

### HACS

1. In HACS, add this repository as a custom repository.
2. Select category **Integration**.
3. Install **Tuya Cloud Two-Circuit Meter**.
4. Restart Home Assistant.
5. Add **Tuya Shadow Meter** from **Settings > Devices & services**.

### Manual

Copy `custom_components/tuya_shadow_meter` into your Home Assistant
`custom_components` directory and restart Home Assistant.

## Tuya Cloud Setup

Create or use a Tuya Cloud project that can access the target meter. The flow is
similar to localTuya cloud-key setup, but this integration only needs cloud
OpenAPI credentials and the target device ID. The setup pattern below is adapted
from the Hassbian localTuya setup notes:
https://bbs.hassbian.com/thread-20247-1-1.html

The four setup screenshots are hosted as GitHub release assets and are not
stored in this repository.

### 1. Create A Cloud Project And Get Access Keys

Go to <https://iot.tuya.com>, open **Cloud Development**, create a cloud
project, and choose the data center that matches your Tuya account. For China
accounts this is usually **China Data Center**.

After the project is created, open the project overview page and copy:

- **Access ID / Client ID**: use as `Cloud Access ID`
- **Access Secret / Client Secret**: use as `Cloud Access Secret`

![Tuya Cloud project access keys](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/tuya-4.jpg)

### 2. Authorize Required APIs

Open **Service API** in the cloud project. Make sure **IoT Core** is authorized.
If available, also authorize **Device Status Notification**. The notification
permission is useful for future push-message support, while the current
integration reads the shadow API by polling.

![Tuya Cloud Service API authorization](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/tuya-3.jpg)

### 3. Link Your Tuya App Account

Open **Devices > Link App Account** in the project. Click **Add App Account**,
choose the Tuya/Smart Life app authorization option, and scan the QR code with
your Tuya app.

After linking, copy the **UID** shown in the app account table. Use this value
as `Cloud App User ID` in Home Assistant.

![Tuya Cloud link app account](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/tuya-2.jpg)

### 4. Link The Meter Device

In the linked app account, open device management and add the target meter to
the cloud project. Confirm the device is online and copy its **Device ID**.

Use this value as `Device ID` in Home Assistant.

![Tuya Cloud linked meter device](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/tuya-1.jpg)

## Home Assistant Setup

Add the integration in Home Assistant and fill in:

| Field | Description |
| --- | --- |
| Device ID | The Tuya device ID for the meter. |
| Cloud Access ID | Tuya Cloud project Access ID. |
| Cloud Access Secret | Tuya Cloud project Access Secret. |
| Cloud App User ID | The linked Tuya app account UID. |
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
`icon.png` at the repository root for HACS display and under
`custom_components/tuya_shadow_meter/brand/icon.png` for Home Assistant's local
brands endpoint.

## Limitations

- This custom integration is limited to the two-circuit meter for now.
- It is not a generic Tuya integration.
- Cloud connectivity and Tuya OpenAPI availability are required.
- The integration is read-only.
