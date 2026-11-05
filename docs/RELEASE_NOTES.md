# Velo 1.2.0 for After Effects

The AE release provides a local CEP panel for Bezier, Elastic and Bounce, multi-point editing, true speed derivatives, EaseCopy, full preset configuration transfer and four interface languages.

AE 版本提供本地 CEP 曲线编辑面板，支持多点位、真实速度导数、EaseCopy、完整预设配置与四语言界面。

- Installable package / 安装附件: `VeloAE_v1.2.0_macOS_Windows.zip`
- SHA-256 / 校验文件: `VeloAE_v1.2.0_SHA256SUMS.txt`
- Offline bilingual guides are included in the ZIP / ZIP 内含离线双语安装指南。
- macOS validation uses After Effects 2026 (`26.5x89`) / macOS 使用 AE 2026（`26.5x89`）验收。
- Windows receives static and archive checks only, not a Windows AE runtime claim / Windows 仅做静态与归档检查，不宣称宿主实测。
- Read [AE v1.2.0 release and verification notes](RELEASE_v1.2.0.md) for the complete scope / 完整范围见 AE 版本说明。

TouchDesigner remains a separate v1.1.0 product. The following TD release notes and its versioned download are preserved. / TD 保持独立的 v1.1.0 产品，以下 TD 发布说明和版本化下载入口继续保留。

# Velo 1.1.0

Native TouchDesigner curve editing with live CHOP output and opt-in Animation COMP keyframe authoring.

原生 TD 曲线编辑器，支持实时 CHOP 输出，并可按需写入 Animation COMP 关键帧。

## Download / 下载

- **Velo_v1.1.0_macOS_Windows.zip** — components, bilingual guides, verification notes and project context / 组件、双语指南、验证说明与项目上下文
- **Velo.tox** — direct native component / 原生组件直接下载
- **SHA256SUMS.txt** — release artifact hashes / 发布产物校验值

GitHub's automatic **Source code** archives are for source inspection; use the ZIP or TOX attachment for installation. / GitHub 自动生成的 Source code 用于源码审查，安装请使用 ZIP 或 TOX 附件。

## What's new / 本版变化

- Added **Settings → Graph → 写入关键帧**.
- Creates `velo_animation[_NN]` inside the current component with unique direct-child naming.
- Writes one `fade` channel with **258 `linear()` keys at frames 0–257, including both endpoints**.
- Preserves the live output contract: one `fade` channel, 257 samples, endpoints `0 → 1`.

新增“写入关键帧”入口，在当前组件内以唯一名称创建 Animation COMP；写入 0–257 帧共 258 个线性关键帧，同时保持原有实时 CHOP 输出不变。

## Install or upgrade / 安装或升级

Unzip and drag `Velo.tox` into TouchDesigner, then connect the first CHOP output to your downstream network. Keep a recoverable copy of an existing project before replacing an older component.

解压后将 `Velo.tox` 拖入 TouchDesigner，并将第一个 CHOP 输出接入下游。替换旧组件前，请保留可恢复的工程副本。

## Compatibility / 兼容性

- Verified host: TouchDesigner **2025.31550** on **macOS**.
- The same native TOX is provided for Windows, with no external frontend runtime or macOS-specific path.
- **Windows has not been runtime-tested in this environment.**

已在 macOS 的 TouchDesigner 2025.31550 验证；同一原生 TOX 同时提供给 Windows，**但本环境尚未进行 Windows 实测**。

## Verification / 验证

- **69 offline regressions passed / 69 项离线回归全部通过**
- Deterministic repeated builds / 重复构建哈希一致
- Native settings action, Animation COMP, `fade` channel and editable `keys` table verified / 已验证原生设置按钮、Animation COMP、`fade` 通道与可编辑 `keys` 表
- Manual keyframe dragging inside Animation Editor is not separately claimed as tested / 不单独宣称已验收 Animation Editor 内的手动拖拽
- No private paths or host-test hooks in the package / 包内无私有路径或宿主测试钩子

TOX SHA-256: `06834c4c4a1b882ba8ec4e1bea20345c1bb0bb252ebd0f417444954fcc70b2a2`

See `SHA256SUMS.txt` for the final ZIP and direct-component hashes. / 最终 ZIP 与直接组件的校验值见 `SHA256SUMS.txt`。
