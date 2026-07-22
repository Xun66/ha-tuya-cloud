# 涂鸦云双路电表

<p align="center">
  <img src="IMG_2957.png" alt="涂鸦云双路电表图标" width="160">
</p>

<p align="center">
  <a href="README.md">English README</a>
</p>

这是一个 Home Assistant 自定义集成，专门用于读取一个特定的涂鸦双路互感计量器。

这个自定义集成目前只支持双路电表。当前目标产品是涂鸦产品
`79a7z01v3n35kytb`，在涂鸦平台中通常显示为 `Double Digital Meter` /
`双路互感计量器`，集成会把它的涂鸦云 shadow 属性暴露为 Home Assistant
传感器。

## 功能

- 通过涂鸦云开发 OpenAPI 读取电表。
- 暴露第 1 路和第 2 路的功率、电流、电压、电量传感器。
- 使用固定英文实体名，例如 `Channel 1 power` 和 `Channel 2 power`。
- 每 60 秒轮询一次。
- 不使用涂鸦扫码登录。
- 不使用涂鸦本地 LAN 协议。
- 不实现控制或写入命令。

## 为什么走云端 OpenAPI

这个电表确实开放了涂鸦本地 LAN 端口，但目前测试过的公开 local Tuya
协议实现无法从这个设备返回可用数据点。涂鸦云 2.0 shadow API 可以稳定读到
这些数值，所以本集成选择通过 OpenAPI 读取 shadow，而不是继续强行走本地协议。

涂鸦云项目里可以开通 **设备状态通知** 权限，但当前版本还没有消费推送消息。
现在先使用已经验证可用的 shadow 轮询读取；后续可以在这个权限基础上继续做推送优先。

## 安装

### HACS

1. 在 HACS 中添加此仓库为自定义仓库。
2. 类型选择 **Integration**。
3. 安装 **Tuya Cloud Two-Circuit Meter**。
4. 重启 Home Assistant。
5. 在 **设置 > 设备与服务** 中添加 **Tuya Shadow Meter**。

### 手动安装

把 `custom_components/tuya_shadow_meter` 复制到 Home Assistant 的
`custom_components` 目录，然后重启 Home Assistant。

## 涂鸦云开发配置

创建或使用一个能访问目标电表的涂鸦云开发项目。整体流程和 localTuya 获取云端
key 的流程类似，但本集成只需要云端 OpenAPI 凭据和目标设备 ID。下面步骤参考了
瀚思彼岸 localTuya 配置贴：
https://bbs.hassbian.com/thread-20247-1-1.html

下面 4 张设置图通过 GitHub release assets 托管，不存放在本仓库代码里。

### 1. 创建云项目并获取 Access Key

打开 <https://iot.tuya.com>，进入 **云开发**，创建云项目，并选择和你涂鸦账号匹配的数据中心。国内账号通常选择 **中国数据中心**。

项目创建后进入项目概览页，复制：

- **Access ID / Client ID**：填入 Home Assistant 的 `Cloud Access ID`
- **Access Secret / Client Secret**：填入 Home Assistant 的 `Cloud Access Secret`

![涂鸦云项目 Access Key](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/tuya-4.jpg)

### 2. 授权所需 API

进入云项目的 **服务 API** 页面，确保已经授权 **IoT Core 连接服务**。如果能看到
**设备状态通知**，也建议一起开通。当前版本读取 shadow 仍然靠轮询，设备状态通知主要为后续推送支持预留。

![涂鸦云服务 API 授权](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/tuya-3.jpg)

### 3. 关联涂鸦 App 账号

进入 **设备 > 关联 App 账号**，点击 **添加 App 账号**，选择涂鸦 App 授权方式，然后用涂鸦 App 扫码绑定。

绑定后，在 App 账号列表里复制 **UID**。这个值填入 Home Assistant 的
`Cloud App User ID`。

![涂鸦云关联 App 账号](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/tuya-2.jpg)

### 4. 关联电表设备

在已关联的 App 账号下进入设备管理，把目标双路互感计量器添加到云项目。确认设备在线，并复制它的 **设备 ID**。

这个值填入 Home Assistant 的 `Device ID`。

![涂鸦云关联电表设备](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/tuya-1.jpg)

## Home Assistant 配置

在 Home Assistant 中添加集成并填写：

| 字段 | 说明 |
| --- | --- |
| Device ID | 目标电表的涂鸦设备 ID。 |
| Cloud Access ID | 涂鸦云项目的 Access ID。 |
| Cloud Access Secret | 涂鸦云项目的 Access Secret。 |
| Cloud App User ID | 已关联涂鸦 App 账号的 UID。 |
| Cloud Region | 涂鸦数据中心，国内通常是 `cn`。 |

## 传感器

默认启用的主要传感器：

| 传感器 | 单位 |
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

另外还有诊断类传感器，用于设备状态、功率状态、告警功率阈值和云端连接状态。

## 图标

项目图标基于 `IMG_2957.png`。仓库根目录的 `icon.png` 用于 HACS 展示；
`custom_components/tuya_shadow_meter/brand/icon.png` 用于 Home Assistant 本地
brands 接口。

## 限制

- 当前只支持这个双路电表。
- 这不是通用涂鸦集成。
- 需要可用的涂鸦云连接和 OpenAPI。
- 只读，不支持控制命令。
