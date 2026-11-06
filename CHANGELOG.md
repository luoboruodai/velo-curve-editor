# Changelog

## 1.2.1 for After Effects — 2026-11-06

### English

- Added a separate **Read** action for selected AE keyframes, restoring times, values and native tangents without replacing the editor during a read-only inspection.
- Multi-anchor Bezier now writes native keyframes and Temporal Ease for scalars and compatible arrays, replacing redundant selected anchors rather than baking the whole curve. Shape-preserving hidden knots and linked spatial negative speeds use explicitly reported local sampling fallbacks.
- Added the offline Velo installer for AE on macOS and Windows, with embedded payload verification, complete backups, rollback on failure and restore support. Platform version metadata is synchronized, compact backup details use a height-adaptive, scrollable layout, and the Windows ICO uses validated directory entries and complete PNG frames. Cavalry and TouchDesigner installers remain future work.
- Added 1,015 AE offline checks, 69 TD checks and installer-specific tests. Real macOS / AE 2026 validation covers 11 native-curve cases. Windows native build and CLI validation are separate from a Windows AE host test.

### 中文

- 新增独立“读取曲线”动作，读取 AE 选中关键帧的时间、数值和原生切线；“检查目标”继续只检查选区，不覆盖编辑器。
- 多点位 Bezier 为标量和兼容数组写入原生关键帧及 Temporal Ease，并替换选区内的冗余锚点，不再默认把整段曲线烘焙成采样点。保形隐藏节点与共享空间属性的负速度使用明确标注的局部采样回退。
- 新增 macOS／Windows 的 AE 离线安装器，内嵌载荷校验、完整备份、失败回滚与恢复；同步平台版本信息，以简短备份提示和自适应滚动布局保持操作可达，并校验 Windows ICO 目录项及完整 PNG 帧。Cavalry 与 TouchDesigner 安装器仍是后续工作。
- 新增 1,015 项 AE 离线检查、69 项 TD 检查及安装器专项测试；macOS / AE 2026 完成 11 组原生曲线实测。Windows 原生构建与 CLI 验证不等同于 Windows AE 宿主实测。

## 1.2.0 for After Effects — 2026-11-06

### English

- Added the local AE CEP curve editor with Bezier, Elastic and Bounce, true speed derivatives, multi-point shape-preserving editing and adaptive smoothing.
- Added scalar native Temporal Ease, sampled multi-property application, EaseCopy, full preset import/export, themes and four interface languages.
- Native save/cancel uses the system file dialog. Invalid preset files leave existing configurations untouched; clipboard permission failures reach the existing fallbacks.
- The native tab remains plain `Velo`; compact status and separate notifications do not rewrite the macOS title bar.
- Segment state-key caching removes repeated serialization while preserving correct invalidation. Package builds are deterministic, validated and documented in `docs/RELEASE_v1.2.0.md`.
- Real validation uses macOS / After Effects 2026 (`26.5x89`) and isolated data. Windows receives static and package checks, not a Windows AE host certification.
- TouchDesigner remains at v1.1.0; this AE release does not replace its TOX or history. A one-click cross-host installer is not included.

### 中文

- 新增本地 AE CEP 曲线编辑器，支持 Bezier、Elastic、Bounce、真实速度导数、多段保形编辑与自适应平滑。
- 支持标量原生 Temporal Ease、多属性采样应用、EaseCopy、完整预设导入导出、主题与四语言界面。
- 原生保存／取消使用系统文件窗口；非法预设文件不修改现有配置，剪贴板权限被拒绝时进入既有回退。
- 原生标签保持纯 `Velo`，紧凑状态与独立通知不改写 macOS 标题栏。
- 分段状态键缓存减少重复序列化并保持正确失效。构建可重复、经过校验，详见 `docs/RELEASE_v1.2.0.md`。
- 在 macOS / After Effects 2026（`26.5x89`）使用隔离数据实测；Windows 仅做静态与打包检查，不宣称 Windows AE 宿主认证。
- TouchDesigner 保持 v1.1.0，本 AE 版本不替换其 TOX 或历史，也不包含跨宿主一键安装器。


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
