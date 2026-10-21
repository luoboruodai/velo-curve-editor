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
