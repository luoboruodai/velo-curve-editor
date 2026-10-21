# Velo — 原生 TouchDesigner 曲线编辑器

Velo 是原生 TD COMP，用于编辑 **Bezier、Elastic 和 Bounce** 曲线。全部界面与输出均使用原生 Panel、Text、Button、Script CHOP、Script SOP、Geometry 和 Render TOP，不使用 WebRender、HTML 浏览器、外部前端运行时，也不修改 TD 全局主题。

![Velo 主界面](docs/images/velo-main.png)

## 主要功能

### 曲线编辑

- 多关键帧值曲线编辑，并在同一画布显示同步速度背景。
- Bezier 可切换独立速度编辑视图，与值曲线共享同一个三次模型。
- 拉杆支持有限范围内的自由坐标，同时用真实导数保持时间正向。
- Elastic / Bounce 使用带标签和数值读数的原生滑杆。
- 显示、编辑、复制和 CHOP 输出使用同一采样模型。

### 原生动画关键帧

- 通过 **设置 → 图形 → 写入关键帧**，将当前曲线导出为原生 Animation COMP。
- 新节点在当前组件的直接子节点中以 `velo_animation[_NN]` 唯一命名，重复导出不会覆盖已有动画。
- `fade` 通道包含 **0–257 帧共 258 个 `linear()` 关键帧（含首尾）**。
- 实时 CHOP 输出仍保持单通道 `fade`、257 样本和首尾 `0 → 1`。

### 预设与 EaseCopy

- 内置和用户预设、拖拽排序、删除、导入导出及卡片尺寸调整。
- 单关键帧或范围复制、整数倍粘贴、仅缓动或仅数值粘贴。
- 支持保留直通与清空缓冲区。
- EaseCopy 使用独立的标题／计数行和功能按钮行，清晰易读。

### 界面与主题

- 曲线、缩略图、选中态和功能图标随主题色调整。
- Bezier 拉杆、锚点与旋钮保持白色，不受主题色影响。
- 浮动半透明毛玻璃适配工具与协调的速度分段控件。
- 设置页具有可见开关／滑杆轨道，以及透明的分区内 caption。

## 安装

1. 从 [Releases](https://github.com/luoboruodai/velo-curve-editor/releases/latest) 下载 `Velo_v1.1.0_macOS_Windows.zip`。
2. 解压后将 `Velo.tox` 拖入 TouchDesigner 网络。
3. 将第一个 CHOP 输出接入需要渐暗信号的下游节点。

`Velo_Demo.tox` 是同一组件的评估副本，并非功能删减版或不同构建。

## 输出与兼容性

- 第一输出：CHOP 通道 `fade`。
- 样本数：257。
- 首尾值：`0.0` 与 `1.0`。
- 已验证宿主：macOS 上的 TouchDesigner **2025.31550**。
- Windows：提供同一原生 TOX，不含 macOS 专用路径或外部运行时依赖；**尚未在本环境对 Windows 进行运行实测**。

## 使用说明

- 直接拖动关键帧与拉杆；拉杆释放到原视口外时会自动扩展视野。
- 点击“适配”可将全部 Bezier 锚点与手柄纳入视口。
- 值／速度编辑共享采样契约，不会通过两套近似模型分别显示。
- EaseCopy 需要有效缓冲区；清空后不能继续粘贴。
- 只有需要独立原生动画节点时才使用“写入关键帧”；实时 CHOP 控制不需要先导出。

## 开发与验证

```bash
for test in tools/test_*.py; do python3 "$test"; done
bash tools/build_tox.sh
```

本版本通过 69 项离线回归、重复一致构建和原生 TD 检查。关键帧导出已验证真实设置按钮、Animation COMP、`fade` 通道与可编辑 `keys` 表；不单独宣称已验收 Animation Editor 内的手动拖拽。

详见[验证说明](docs/VERIFICATION.md)、[更新日志](CHANGELOG.md)与[发布说明](docs/RELEASE_NOTES.md)。后续维护者可先读 [AGENTS.md](AGENTS.md) 和 [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)。
