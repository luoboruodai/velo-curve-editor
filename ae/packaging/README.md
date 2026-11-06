# Velo 1.2.1 · AE 曲线编辑器

[English](README.en.md)

Velo 是一个本地 After Effects CEP 面板，用于编辑 Bezier、Elastic 和 Bounce 曲线，查看真实速度导数，并将结果应用到数值关键帧。

本 ZIP 是免安装面板包。macOS 和 Windows 使用同一组面板文件，不需要联网、Node.js、Python 或其他扩展。也可以在同一发布页选择原生 `VeloInstaller.app`（macOS）或 `VeloInstaller.exe`（Windows），离线安装、完整备份和失败回滚；Cavalry 与 TouchDesigner 安装器尚未提供。

## macOS 安装

1. 退出 After Effects。
2. 解压本 ZIP，将 `com.velo.curveeditor` 文件夹复制到：

   ```text
   ~/Library/Application Support/Adobe/CEP/extensions/
   ```

3. 重新打开 AE，在 `窗口 → 扩展 → Velo` 打开面板。

## Windows 安装

1. 退出 After Effects。
2. 解压本 ZIP，将 `com.velo.curveeditor` 文件夹复制到：

   ```text
   %APPDATA%\Adobe\CEP\extensions\
   ```

   可在资源管理器地址栏输入 `%APPDATA%`，再进入 `Adobe\CEP\extensions\`。
3. 重新打开 AE，在 `窗口 → 扩展 → Velo` 打开面板。

目标位置应包含 `com.velo.curveeditor\index.html` 和 `com.velo.curveeditor\CSXS\manifest.xml`，不要再嵌套一层同名文件夹。

## 未签名 CEP 面板

如果 AE 阻止本地未签名面板，请仅为你的 AE 所使用的 CSXS 主版本启用 `PlayerDebugMode`。不要关闭其他系统安全保护，也不要安装来源不明的扩展。

macOS 示例（将 `7` 替换为实际 CSXS 主版本）：

```bash
defaults write com.adobe.CSXS.7 PlayerDebugMode 1
```

Windows 示例（同样按实际版本替换 `7`）：

```bat
reg add "HKCU\Software\Adobe\CSXS.7" /v PlayerDebugMode /t REG_SZ /d 1 /f
```

更改后重新启动 AE。这是本地调试扩展的系统偏好，不是 Velo 的账户或在线激活流程。

## 升级与设置

- 升级前先退出 AE，再替换面板文件夹；不要保留旧的 `.debug` 文件。
- 用户曲线、设置和预设保存在本机面板存储中。重要配置可在 `设置 → 预设` 导出备份。
- 如果升级后仍显示旧页面，请重新打开面板，使 CEP 重新加载资源。
- 卸载时退出 AE 并移除该面板文件夹；是否保留本机设置由你决定。

## 基本使用

1. 在目标合成中选择一个数值属性的至少两个连续关键帧。
2. 点击“读取曲线”导入现有数值和切线；“检查目标”只检查选区，不会覆盖当前编辑器。
3. 调整曲线或选择预设；Bezier 可切换值／速度视图，再点击 `Apply`。
4. 一次 AE 撤销即可恢复本次应用前的状态。

支持多段保形插点与删除、切线吸附、整体平滑、多属性应用、EaseCopy、预设排序／导入／导出、主题与四语言界面。标量和等长数值数组的多段 Bezier 默认按可见锚点写入原生关键帧与 Temporal Ease，不再整段烘焙；含保形隐藏节点的可见区段使用明确报告的形状保留采样。共享 Position 等空间属性的负速度会被 AE 钳为零，这类情况也使用局部形状保留采样，不冒充原生负速度。Elastic／Bounce 和旧单段数组路径继续使用采样关键帧。

## 验证与平台边界

- 清单声明 AE `17.0` 及以上、CSXS `7.0`；只有实际测试过的宿主版本才会在发布说明中列为已验证。
- macOS 验收使用 After Effects 2026（`26.5x89`）。其他 AE 版本未逐一实测。
- Windows 包完成结构、路径、语法和归档检查，**尚未在 Windows AE 实机验证**。这不等同于 Windows 宿主功能认证。
- 本版本仅提供 AE 面板及 AE 一键安装器。TouchDesigner 使用仓库中独立的 TD 包；Cavalry 与 TouchDesigner 一键安装器尚未提供。

## 链接

以下链接需要联网；安装和基本使用不需要联网。

- [v1.2.1 发布说明与校验值](https://github.com/luoboruodai/velo-curve-editor/releases/tag/v1.2.1)
- [中文完整说明](https://github.com/luoboruodai/velo-curve-editor/blob/v1.2.1/README.zh-CN.md)
- [English guide](README.en.md)
- [第三方声明](THIRD_PARTY_NOTICES.md)
