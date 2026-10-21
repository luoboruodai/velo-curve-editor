# Verification / 验证说明

## Artifact identity / 产物身份

- Version / 版本: **1.0.0**
- `dist/Velo.tox` and `dist/Velo_Demo.tox` are byte-identical / 两个文件逐字节一致。
- TOX SHA-256: `2659852c973d8d36c5d7eabc39367afada60fc33a3a655463f5be2da143abc06`
- Repeated builds produced the same hash / 重复构建哈希一致。

## Automated checks / 自动检查

- **67 offline regressions passed / 67 项离线回归全部通过**.
- Package scan found no private paths, QA markers or host-test hooks / 包扫描未发现私有路径、QA 标记或宿主测试钩子。
- Output: one `fade` channel, 257 samples, first `0.0`, last `1.0` / 单通道、257 样本、首尾 `0→1`。

## Native host checks / 原生宿主检查

- Transparent in-section captions and their content spacing were checked in all four settings pages / 四个设置页的透明 caption 与内容间距均已检查。
- Settings interface was visually reviewed in TouchDesigner / 设置·界面页已进行原生目检。
- Prior native checks cover curve output, EaseCopy, free handles, theme roles and multi-size layouts / 此前原生检查覆盖输出、EaseCopy、自由拉杆、主题角色与多尺寸布局。

## Platform boundary / 平台边界

- Verified on **macOS with TouchDesigner 2025.31550** / 已在 macOS 的 TouchDesigner 2025.31550 验证。
- The same native TOX is packaged for Windows / 同一原生 TOX 同时提供给 Windows。
- **Windows has not been runtime-tested in this environment / 本环境尚未对 Windows 进行运行实测。**
