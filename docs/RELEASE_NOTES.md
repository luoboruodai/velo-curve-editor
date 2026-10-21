# Velo 1.0.0

Native TouchDesigner curve editor with Bezier, Elastic and Bounce models, multi-keyframe editing, synchronized speed visualization, presets, EaseCopy and adaptive themes.

原生 TD 曲线编辑器，支持多关键帧、速度背景、预设、EaseCopy、自适应主题、白色拉杆旋钮和半透明工具条。

## Download / 下载

- **Velo_v1.0.0_macOS_Windows.zip** — component and bilingual documentation / 组件与中英文文档
- **Velo.tox** — direct native component / 原生组件直接下载
- **SHA256SUMS.txt** — artifact hashes / 产物校验

## Install / 安装

Unzip and drag `Velo.tox` into TouchDesigner, then connect the first CHOP output to your downstream network.

解压后将 `Velo.tox` 拖入 TouchDesigner，并将第一个 CHOP 输出接入下游。

## Compatibility / 兼容性

- Host used for verification: TouchDesigner **2025.31550** on **macOS**.
- The same native TOX is provided for Windows. It contains no external frontend runtime or macOS-specific path.
- **Windows has not been runtime-tested in this environment.**

macOS 已完成原生验证；同一原生 TOX 同时提供给 Windows，不含外部前端运行时或 macOS 专用路径，**但本环境尚未进行 Windows 实测**。

## Verification / 验证

- **67 offline regressions passed / 67 项离线回归全部通过**
- Deterministic repeated builds / 重复构建哈希一致
- Native TouchDesigner checks for curve output, presets, EaseCopy, flexible handles, adaptive themes and settings / 原生检查覆盖输出、预设、EaseCopy、自由拉杆、主题与设置
- Output: one `fade` channel, 257 samples, endpoints `0 → 1` / 单通道 `fade`、257 样本、首尾 `0→1`
- No private paths or host-test hooks in the package / 包内无私有路径或宿主测试钩子

TOX SHA-256: `2659852c973d8d36c5d7eabc39367afada60fc33a3a655463f5be2da143abc06`

ZIP SHA-256: `87a30a2e51e9dda9f3cc4c32512e7e58f0c798b3ffd3bdf422134ef36e18dd8d`
