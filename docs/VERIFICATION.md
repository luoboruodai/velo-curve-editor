# Verification / 验证说明

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
