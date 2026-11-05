# Velo 1.2.0 for After Effects

[English](#english) · [中文](#中文)

## 中文

**发布日期：2026-11-06。** 本次发布以 After Effects CEP 面板为主，保留独立的 TouchDesigner 产品与历史，不包含 AE／Cavalry／TouchDesigner 一键安装器。

### 下载

- **`VeloAE_v1.2.0_macOS_Windows.zip`**：macOS／Windows 共用的可安装面板包。
- **`VeloAE_v1.2.0_SHA256SUMS.txt`**：该 ZIP 的 SHA-256。
- 安装前阅读 ZIP 内的 `README.md` 或 `README.en.md`。GitHub 自动生成的 *Source code* 是源码归档，不代替上述面板附件。

### 本版内容

- Bezier、Elastic、Bounce，真实导数速度视图，多段保形插点／删除、切线吸附与自适应整体平滑。
- 标量原生 Temporal Ease、数组与多段采样、多属性应用和一次撤销。
- 多锚点内容自适应高度；CEP 外窗无法扩大时使用内部滚动，不冒充外窗自适应。
- EaseCopy 分离粘贴缓动／数值、直通和清空。数值写入后统一恢复目标缓动，避免 AE 自动重算相邻速度。
- 22 个内置预设、用户预设、排序、隐藏、完整 v2 配置导入导出及旧格式兼容；冲突 ID 保留原项并重映射。
- 原生系统保存对话框、真实路径显示、取消不写文件、错误文件不修改现有配置。
- 剪贴板权限被拒绝时进入已有复制／手动粘贴回退路径。
- 四语言、四向布局、主题取色、网格／精度调整、紧凑模式和减少动效。
- 原生标签保持纯 `Velo`；短状态留在模式按钮旁，完整提醒使用右侧通知，不改写 macOS 标题栏。
- 分段数组按引用缓存序列化状态键，保留标量更新与分段替换的正确失效行为。

### 性能与体积

在记录的开发机上，12 段曲线的 28,000 次重复状态键读取不再重复序列化分段数组，键值、校验和与缓存失效断言一致。独立状态键路径的中位测量约由 `2.46µs` 降至 `0.92µs`。该结果不代表 AE 整体提速比例。

真实 CEP 预览复测使用同一 12 段曲线和精度：缓存前 90 个观察帧中序列化分段 90 次，缓存后为 0 次；预览清屏分别为 62 和 65 帧，曲线输出逐字节一致。该结果证明重复计算消除，不以观察帧率宣称整体性能提升。

打包保留可读源码与本地 Adobe 桥库，使用精简的离线双语指南，不增加压缩工具或运行时依赖。最终 ZIP 字节和 SHA-256 以本页附件及 `VeloAE_v1.2.0_SHA256SUMS.txt` 为准。

### 验证范围

- 947 项现有离线回归与打包检查通过，包含 234 项面板结构、388 项 i18n 和 15 项发布包检查。
- macOS / After Effects 2026（`26.5x89`）完成 13 组真实宿主检查、46 组预设／设置检查和 15 组曲线指针／预览检查；测试合成已清理。
- 真实系统保存／取消、v2 冲突导入、旧格式导入、坏文件保护及原状态恢复通过。
- CEP 指针拖动已验证目标高亮、可见顺序、持久化、空白处释放与普通点击，使用 `Input.dispatchMouseEvent` 驱动真实 DOM 输入链。浏览器 HTML5 拖放没有形成完整原生 `dragover/drop`，不记为通过；未把这条 CEP 证据扩大为全部物理输入组合。
- Windows CI 运行源码、路径、语法和归档检查；**未进行 Windows AE 实机验证**。CI 不安装 AE，也不证明所有声明版本都已实测。
- 部分原生 Escape 输入未被宿主送达；可见关闭按钮已验证，不将该键盘路径计为完整通过。360px 检查是 CSS 视口，不冒称原生窗口缩放。

### 升级与后续

退出 AE 后替换整个 `com.velo.curveeditor` 文件夹，不要将 `.debug` 带入正式安装。建议先导出重要预设。原生 AE 标签或页面缓存未刷新时，重新打开面板或重启 AE。

[TouchDesigner v1.1.0](https://github.com/luoboruodai/velo-curve-editor/releases/tag/v1.1.0) 仍是独立的 TD 原生产品。跨宿主一键安装器尚未发布。

[中文完整说明](../README.zh-CN.md) · [问题反馈](https://github.com/luoboruodai/velo-curve-editor/issues)

## English

**Released: 2026-11-06.** This release focuses on the After Effects CEP panel. The independent TouchDesigner product and its history remain intact. A one-click AE/Cavalry/TouchDesigner installer is not included.

### Download

- **`VeloAE_v1.2.0_macOS_Windows.zip`** — the installable panel for macOS and Windows file layouts.
- **`VeloAE_v1.2.0_SHA256SUMS.txt`** — the ZIP's SHA-256.
- Read `README.md` or `README.en.md` inside the ZIP before installing. GitHub's automatic *Source code* archive is not a substitute for the panel attachment.

### Highlights

- Bezier, Elastic and Bounce with true derivative views, multi-segment shape-preserving insertion/deletion, tangent snapping and adaptive smoothing.
- Native scalar Temporal Ease, sampled arrays and multi-segment output, multi-property application and one-step undo.
- Content height adapts to visible anchors, with internal scrolling when CEP cannot expand the outer window.
- EaseCopy preserves target easing after numerical writes instead of letting AE recalculate adjacent velocities.
- Complete preset configuration import/export, conflict-safe user IDs, legacy compatibility and native save/cancel behavior.
- Clipboard permission fallbacks, four interface languages, themes, adjustable layout and reduced motion.
- A plain `Velo` native tab, compact toolbar status and a separate notification for complete feedback.
- Reference-based segment-key caching with correct scalar and segment invalidation.

### Performance and size

The recorded 12-segment microbenchmark eliminates repeated segment serialization across 28,000 state-key reads, with identical keys and valid invalidation. Its median key-path timing decreased from about `2.46µs` to `0.92µs`; this is not a claim of the same improvement for AE as a whole.

The real CEP preview check used the same 12-segment curve and precision: 90 segment serializations before caching and 0 afterward, with 62 and 65 preview clears respectively and byte-identical curve output. This demonstrates removal of repeated computation, not a whole-application frame-rate improvement.

The package retains readable source and the local Adobe bridge, uses concise offline bilingual guides and adds no compression or runtime dependency. Use the actual release attachment and `VeloAE_v1.2.0_SHA256SUMS.txt` for the final bytes and digest.

### Validation and boundaries

- 947 offline regression and package checks pass, including 234 panel-structure, 388 i18n and 15 release-package checks.
- Real macOS / After Effects 2026 (`26.5x89`) checks cover 13 host groups, 46 preset/settings groups and 15 curve/preview groups; test compositions are removed.
- Native save/cancel, conflict-safe and legacy imports, invalid-file protection and original-state restoration pass.
- CEP pointer dragging verifies target highlighting, visible and persisted order, outside release and ordinary clicks through `Input.dispatchMouseEvent` and the real DOM event chain. Native HTML5 `dragover/drop` is not claimed as passing, and this CEP evidence does not claim every physical input path.
- Windows CI checks source, paths, syntax and archives. **Windows AE has not been exercised on a physical or virtual Windows host.** CI does not install AE or certify every declared version.
- Some native Escape input was not delivered by the host; visible close controls were tested instead. The 360px check is a CSS viewport, not a native-window resize claim.

### Upgrade and what comes next

Quit AE, replace the whole `com.velo.curveeditor` folder and do not carry over `.debug`. Export important presets before upgrading. Reopen the panel or AE if a cached tab or page remains.

[TouchDesigner v1.1.0](https://github.com/luoboruodai/velo-curve-editor/releases/tag/v1.1.0) remains a separate native TD product. The cross-host one-click installer has not been released.

[Full English guide](../README.md) · [Issues](https://github.com/luoboruodai/velo-curve-editor/issues)
