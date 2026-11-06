# Velo AE v1.2.1

[English](#english) · [中文](#中文)

## 中文

### 本次修复

- **读取与检查分离**：`读取曲线`导入所选 AE 关键帧的实际时间、数值和切线；`检查目标`仍只报告选区，不覆盖正在编辑的曲线。
- **多点位不再默认整段采样**：兼容的标量、共享维度和独立数值数组按可见锚点写入原生关键帧及逐段 Temporal Ease。选区内的多余旧锚点会被替换，其他属性与外部选区保持原状，一次 UndoGroup 可撤销。
- **如实处理 AE 限制**：共享 Position 等空间属性的负速度会被 AE 钳为零，不能把负速度伪装成原生支持；这类区段与保形隐藏节点使用明确报告的局部形状保留采样。标量及支持的独立维度仍保留原生负速度。
- **数据校验**：跳帧选区、无效手柄、Hold、不同归一化维度、非法载荷均在写入前拒绝。平坦维度不会被误当作不兼容曲线。

### 原生离线安装器

- macOS：下载 `VeloInstaller_v1.2.1_macOS.zip`，解压后打开 `VeloInstaller.app`。
- Windows：下载并运行 `VeloInstaller_v1.2.1_Windows.exe`。
- 安装器内嵌面板，不需要联网下载 Python 或其他运行时。macOS 使用 ad-hoc 签名，未经过公证；Windows 没有 Authenticode 签名。系统可能显示开发者身份提示，请核对发布页的 SHA-256，不要关闭全局安全保护。
- 默认安装到当前用户的 CEP `extensions` 目录，不需要管理员权限。替换前完整备份旧面板，保留本机设置和预设；失败自动回滚。可在 `Velo-backup` 中选择备份恢复。
- 可选的 `PlayerDebugMode` 只修改所选 CSXS 主版本的当前用户偏好，**默认不启用**，也不会修改其他 Adobe 设置。
- 安装器不会自动关闭 AE；安装后请保存工程并重新启动 AE。

### 验证范围

| 层级 | 结果 |
|---|---|
| AE 离线回归与打包检查 | 1,015 项通过 |
| TouchDesigner 离线检查 | 69 项通过，TD 版本及历史保持不变 |
| 安装器事务、资源与布局测试 | 22 项通过，覆盖首次安装、升级、篡改拒绝、失败回滚、恢复、链接边界、冻结资源、备份信息布局和平台版本输入 |
| 真实 AE / macOS 2026（`26.5x89`） | 11 组原生曲线检查通过，运行错误为 0；测试合成及原设置已恢复 |
| 原生安装器 CLI | 内嵌面板安装、版本、备份和恢复验证；最终应用 ZIP 的文件、目录链接、权限、bundle 版本和签名已回读 |
| 原生安装器 / macOS | 两次键盘安装、真实目录选择恢复及备份哈希核对通过；中英文 Tk 布局与 620×640 滚动可达性通过 |
| Windows | 由 Windows runner 原生构建并执行 CLI 安装验证；**没有 Windows AE 实机或原生 UI 验收** |

真实 AE 检查覆盖读取、只读检查、Position 多点与逐段切线、回读、一次撤销、共享空间负速度回退、标量负速度、多属性、冗余锚点清理、保形隐藏节点和跳帧拒绝。既有单段、Elastic／Bounce 与 EaseCopy 路径保留。

### 附件与校验

- `VeloAE_v1.2.1_macOS_Windows.zip`：手动安装面板及双语离线指南。
- `VeloInstaller_v1.2.1_macOS.zip`：原生 macOS `.app`。
- `VeloInstaller_v1.2.1_Windows.exe`：原生 Windows 安装器。
- 对应的 `*_SHA256SUMS.txt` 与 `*.manifest.json` 提供实际校验值及验证范围。请以 Release 中最终附件为准。

### 边界

- Windows 仍需在实际 AE 中复测读取与多点写入，不能仅凭跨平台包或 CI 宣称 Windows AE 已认证。
- 其他 AE 版本、全部物理输入组合和所有窗口尺寸未逐一覆盖。
- Cavalry 与 TouchDesigner 安装器尚未开发。TD 继续使用独立的 v1.1.0 原生 TOX，不将 AE 的 CEP 技术栈套入 TD。

## English

### Fixes

- **Separate Read and Inspect:** `Read` imports actual keyframe times, values and native tangents from AE. `Inspect` only checks the selection and never replaces the editor curve.
- **Native multi-anchor output:** compatible scalar and array curves are written at visible anchors with per-span Temporal Ease instead of baking the entire shape. Redundant selected keys are replaced, outer properties are preserved, and one UndoGroup restores the operation.
- **Honest handling of AE constraints:** AE clamps negative speeds on shared spatial properties such as Position to zero. Those spans, and spans with hidden shape knots, use explicitly reported local shape-preserving samples. Scalar and supported independent dimensions keep native negative speeds.
- **Validation before writing:** non-contiguous selections, invalid handles, Hold interpolation, incompatible normalized dimensions and invalid payloads are rejected. Constant dimensions do not cause false incompatibility errors.

### Offline native installer

- macOS: extract `VeloInstaller_v1.2.1_macOS.zip` and open `VeloInstaller.app`.
- Windows: run `VeloInstaller_v1.2.1_Windows.exe`.
- The installer embeds the panel and does not download a runtime. macOS uses ad-hoc signing, not notarization; Windows has no Authenticode signature. Verify the release SHA-256 rather than disabling global security protections.
- It installs into the current user's CEP `extensions` folder without administrator privileges, backs up the complete old panel, preserves local settings and rolls back on failure. Backups in `Velo-backup` can be restored later.
- Optional `PlayerDebugMode` changes only the selected CSXS major version for the current user. It is **off by default** and never enabled silently.
- AE is never closed automatically. Save your project and restart AE after installation.

### Validation

- **1,015** AE offline/package checks and **69** TD checks pass.
- **22** installer transaction/resource/layout checks pass, including install, upgrade, tamper rejection, rollback, restore, bounded backup-path presentation, platform version inputs, link boundaries and frozen resources.
- **11** real macOS / AE 2026 (`26.5x89`) native-curve checks pass with no runtime errors; test compositions and original settings are restored.
- Native installer CLI checks cover the embedded panel, version, backup and restore. The final macOS ZIP is checked for bytes, directory links, permissions, bundle version and signature.
- Native macOS keyboard installation, repeated-upgrade backup and directory-picker restore pass with complete backup hashes. Chinese and English Tk layouts have actual screenshots and measured content fitting plus `620×640` scrolling; these synthetic layout fixtures do not certify a physical language-button click.
- Windows installers are built and CLI-tested on a native Windows runner. **This is not a Windows AE host or native-UI certification.** Cavalry and TouchDesigner installers are not included; the separate TD v1.1.0 product is unchanged.

See the checksum and manifest attachments for exact artifact identity and verified scope. Do not use GitHub's automatic source-code archive as the installer attachment.
