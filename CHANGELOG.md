# Changelog

## 1.1.0 — 2026-10-21

### English

- Added **Settings → Graph → 写入关键帧** for opt-in native animation authoring.
- Exports the current curve to a uniquely named `velo_animation[_NN]` Animation COMP without overwriting existing animation nodes.
- Writes one `fade` channel with 258 `linear()` keys at frames 0–257, including both endpoints.
- Preserves the live output contract: one `fade` channel, 257 samples and endpoints `0 → 1`.
- Added offline export regressions and native TouchDesigner verification of the settings action, Animation COMP, channel and editable `keys` table.
- Added bilingual release documentation and a compact architecture / troubleshooting handoff for future maintainers.
- 69 offline regressions pass. Windows receives the same native TOX but remains runtime-unverified in this environment.

### 中文

- 新增 **设置 → 图形 → 写入关键帧**，按需创建原生动画数据。
- 将当前曲线导出为唯一命名的 `velo_animation[_NN]` Animation COMP，不覆盖已有动画节点。
- 写入一个 `fade` 通道，包含 0–257 帧共 258 个 `linear()` 关键帧（含首尾）。
- 保持实时输出契约：单通道 `fade`、257 样本、首尾 `0 → 1`。
- 新增离线导出回归，并在原生 TD 中验证设置按钮、Animation COMP、通道和可编辑 `keys` 表。
- 新增双语发布文档，以及面向后续维护者的精简架构与堵点交接。
- 69 项离线回归通过。Windows 提供同一原生 TOX，但本环境仍未进行运行实测。

## 1.0.0 — 2026-10-21

### English

First public release of Velo, a native TouchDesigner curve editor.

- Bezier, Elastic and Bounce curve models with multi-keyframe editing and synchronized speed visualization.
- Flexible monotonic-safe Bezier handles, fit-view support and a 257-sample `fade` CHOP output.
- Built-in and user presets with ordering, deletion and import/export.
- EaseCopy with range copy, integer-multiple paste, ease/value separation, passthrough preservation and buffer clearing.
- Adaptive themes, white handles and knobs, translucent view tools and redesigned settings/captions.
- 67 offline regressions, deterministic repeated builds and native macOS TouchDesigner verification.
- One native TOX package for macOS and Windows. Windows runtime verification is not claimed.

### 中文

Velo 首个公开发布版本，一款原生 TouchDesigner 曲线编辑器。

- Bezier、Elastic、Bounce 三类曲线，多关键帧编辑与同步速度显示。
- 保持时间正向的自由拉杆、视口适配，以及 257 样本的 `fade` CHOP 输出。
- 内置和用户预设，支持排序、删除与导入导出。
- EaseCopy 支持范围复制、整数倍粘贴、缓动／数值分离、保留直通及清空。
- 自适应主题、白色拉杆旋钮、半透明工具条与重新协调的设置页。
- 67 项离线回归、重复一致构建及 macOS 原生 TD 验证。
- 同一原生 TOX 同时提供 macOS 与 Windows；不宣称 Windows 已实测。
