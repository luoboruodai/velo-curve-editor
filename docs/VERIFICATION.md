# Verification / 验证说明

## After Effects 1.2.1 / AE 曲线与离线安装器

- AE manifest and host engine are **1.2.1**. `readCurve()` imports selected keyframe times, values and native tangents; `Inspect` remains read-only.
- **1,015 AE offline/package checks and 69 TD checks pass.** Installer transaction/resource/layout checks total **23**, including tamper rejection, rollback, backup restore, bounded backup-path presentation, platform version inputs, ICO directory and PNG frame boundaries, exact resource hashes and the standard PyInstaller payload link versus unsafe links.
- Multi-anchor Bezier writes native keys and per-span easing where supported, including linked and independent dimensional easing. Constant dimensions are handled explicitly. Hidden shape knots and linked spatial negative speeds use disclosed local sampling; scalar and supported independent negative speeds remain native.
- **11 real macOS / AE 2026 (`26.5x89`) native-curve checks pass with `runtimeErrors=[]`.** Test compositions are removed and original settings restored. These checks cover read/inspect behavior, Position anchors and easing, roundtrip, undo, spatial fallback, scalar negative speed, multi-property undo, redundant-key replacement, hidden knots and non-contiguous rejection.
- Native installer CLI validates embedded payload and installation. The macOS ZIP is checked against the original bundle for file bytes, directory symlinks, link targets, permissions, bundle version and signature. `VeloInstaller.app` uses ad-hoc signing, not notarization; Windows has no Authenticode signature.
- Native macOS keyboard installation, repeated-upgrade backup and directory-picker restore were exercised with complete backup-hash checks. Chinese and English Tk layouts have actual screenshots and geometry checks at content-fitted height and at `620×640`, where scrolling reaches all footer actions. Synthetic layout fixtures are not evidence of a physical language-button click.
- Windows installers are built and CLI-tested on Windows runners. **Windows AE and native-UI verification remain unclaimed.** Cavalry and TouchDesigner installers are future work; the separate TD v1.1.0 output and history remain unchanged. See `docs/RELEASE_v1.2.1.md`.

## After Effects 1.2.0 / AE 曲线编辑器

- The AE manifest and host engine are version **1.2.0**. The installable attachment is `VeloAE_v1.2.0_macOS_Windows.zip`; its digest is provided separately as `VeloAE_v1.2.0_SHA256SUMS.txt`.
- **947 offline regression and package checks pass**, including 234 panel-structure, 388 i19n and 15 release-package checks. The CI matrix runs these checks on macOS, Windows and Ubuntu without installing AE.
- Real macOS / After Effects 2026 (`26.5x89`) checks cover 13 host groups, 46 preset/settings groups and 15 curve/preview groups. Native save/cancel, complete and legacy imports, invalid-file protection and original-state restoration also pass.
- Segment state-key caching preserves identical keys and checksums while eliminating repeated segment serialization after warmup in the 28,000-read microbenchmark. Its measured median key-path timing changed from approximately `2.46µs` to `0.92µs`; this does not represent the whole AE application.
- A real CEP preview check with the same 12-segment curve recorded 90 segment serializations before caching and 0 afterward, with 62 and 65 preview clears respectively and identical curve bytes. This is not a whole-application frame-rate claim.
- CEP pointer preset dragging verified target highlighting, visible and persisted order, ordinary click behavior and no reorder on outside release. Native HTML5 `dragover/drop` did not complete and is not claimed as passing. Evidence distinguishes CEP input from unverified physical input paths.
- The package uses explicit members, portable paths, offline bilingual guides and a candidate-then-replace build. Rebuilding identical reviewed inputs produces identical bytes; failed candidates do not replace the previous valid archive.
- **Windows receives structural, path, syntax and archive checks, not a Windows AE runtime certification.** Native CEP behavior and macOS host evidence are not interchangeable with Windows verification. See `docs/RELEASE_v1.2.0.md` for the detailed scope and remaining input boundaries.
- TD remains a separate product at version **1.1.0**. Its native TOX, output contract and verification below are unchanged by the AE release.


## Artifact identity / 产物身份

- Version / 版本: **1.1.0**
- `dist/Velo.tox` and `dist/Velo_Demo.tox` are byte-identical / 两个文件逐字节一致。
- TOX SHA-256: `06834c4c4a1b882ba8ec4e1bea20345c1bb0bb252ebd0f417444954fcc70b2a2`
- Repeated builds produced the same hash / 重复构建哈希一致。

## Automated checks / 自动检查

- **69 offline regressions passed / 69 项离线回归全部通过**.
- The two keyframe-export regressions cover unique naming, all sample writes, linear interpolation and failure status / 两项关键帧导出回归覆盖唯一命名、全样本写入、线性插值和失败状态。
- Package scan found no private paths, QA markers or host-test hooks / 包扫描未发现私有路径、QA 标记或宿主测试钩子。
- Live output: one `fade` channel, 257 samples, first `0.0`, last `1.0` / 实时输出为单通道、257 样本、首尾 `0→1`。

## Native keyframe authoring / 原生关键帧写入

- The real **Settings → Graph → 写入关键帧** action was dispatched in TouchDesigner / 已在 TD 中触发真实设置按钮动作。
- A native Animation COMP was created inside the current component with unique `velo_animation[_NN]` naming / 已在当前组件内创建唯一命名的原生 Animation COMP。
- The `fade` channel contains **258 keys at frames 0–257**, all using `linear()` / `fade` 通道包含 0–257 帧共 258 个关键帧，全部使用 `linear()`。
- The editable `keys` table was opened and inspected / 已打开并检查可编辑 `keys` 表。
- Existing real user presets remained unchanged / 真实用户预设保持不变。
- **Manual keyframe dragging inside Animation Editor was not separately verified / 尚未单独验证 Animation Editor 内的手动拖拽。**

## Other native host checks / 其他原生宿主检查

- Prior v1.0.0 validation confirmed actual TD parameter evaluation and rendered alpha control over time; v1.1.0 preserves that output path / 此前 v1.0.0 已验证真实 TD 参数求值和随时间变化的渲染透明度控制，v1.1.0 保持该输出链路。
- Settings captions, curve output, presets, EaseCopy, flexible handles, theme roles and multi-size layouts have separate native evidence / 设置标题、曲线输出、预设、EaseCopy、自由拉杆、主题角色与多尺寸布局均有对应原生证据。

## Platform boundary / 平台边界

- Verified on **macOS with TouchDesigner 2025.31550** / 已在 macOS 的 TouchDesigner 2025.31550 验证。
- The same native TOX is packaged for Windows / 同一原生 TOX 同时提供给 Windows。
- **Windows has not been runtime-tested in this environment / 本环境尚未对 Windows 进行运行实测。**
