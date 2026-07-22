# Tuya Cloud

<p align="center">
  <img src="IMG_2957.png" alt="Tuya Cloud 图标" width="160">
</p>

<p align="center">
  <a href="README.md">English README</a>
</p>

这是一个 Home Assistant 自定义集成，用于读取通过涂鸦 sharing API 推送
MQTT 数据的受支持设备。

当前内置的设备 profile 支持涂鸦产品 `79a7z01v3n35kytb`，在涂鸦平台中通常显示为
`Double Digital Meter` / `双路互感计量器`。后续可以通过贡献新的产品
profile 和 MQTT 数据点映射来支持更多设备。

## 功能

- 使用 Home Assistant 官方涂鸦集成同款扫码登录流程。
- 从你的涂鸦/Smart Life 账号自动发现受支持设备。
- 通过涂鸦 MQTT 推送更新传感器。
- 为当前 profile 暴露第 1 路和第 2 路的功率、电流、电压、电量传感器。
- 使用固定英文实体名，例如 `Channel 1 power` 和 `Channel 2 power`。
- 不需要涂鸦云开发 Access ID / Access Secret。
- 不使用涂鸦本地 LAN 协议。
- 不主动轮询电表数值。
- 不实现控制或写入命令。

## 效果图

配置完成后，Home Assistant 会显示受支持设备及其已映射的传感器。

![Home Assistant 电表效果图](https://github.com/Xun66/ha-tuya-cloud/releases/download/readme-assets/demo.jpg)

## 为什么走 MQ

首个受支持设备确实开放了涂鸦本地 LAN 端口，但目前测试过的公开 local Tuya
协议实现无法从这个设备返回可用数据点。涂鸦 MQTT 会为它推送可用的
`protocol=4` 数据点，包括两路功率、电流、电压和电量。

本集成只走 MQ。首次传感器数值要等第一条 MQTT 状态推送；打开涂鸦 App 中的电表页面通常可以触发更快更新。

## 安装

### HACS

1. 在 HACS 中添加此仓库为自定义仓库。
2. 类型选择 **Integration**。
3. 安装 **Tuya Cloud**。
4. 重启 Home Assistant。
5. 在 **设置 > 设备与服务** 中添加 **Tuya Cloud**。

### 手动安装

把 `custom_components/tuya_shadow_meter` 复制到 Home Assistant 的
`custom_components` 目录，然后重启 Home Assistant。

## Home Assistant 配置

1. 打开 Smart Life 或涂鸦 App。
2. 在 App 账号/设置页面找到 **User Code**。
3. 在 **设置 > 设备与服务** 中添加 **Tuya Cloud**。
4. 输入 User Code。
5. 用同一个涂鸦 App 扫描二维码。

扫码后会自动添加受支持设备。

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

- 只有内置 profile 匹配的设备才会被支持。
- 这不是通用涂鸦集成。
- 需要可用的涂鸦云连接和 MQTT。
- 初始传感器数值依赖第一条 MQTT 状态推送。
- 只读，不支持控制命令。

## 贡献

欢迎贡献。设备反馈、涂鸦 MQTT 返回样本、传感器映射修正、文档改进，以及更多兼容电表支持都很有帮助。

## 许可证

本项目使用 MIT License 发布，详见 `LICENSE`。
