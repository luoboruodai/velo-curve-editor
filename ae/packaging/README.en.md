# Velo 1.2.1 · Curve Editor for After Effects

[中文说明](README.md)

Velo is a local After Effects CEP panel for Bezier, Elastic and Bounce curves, true derivative views and numerical keyframe application.

This ZIP contains a portable panel. The same files work at the file-structure level on macOS and Windows, with no network access, Node.js, Python or additional extensions required. The release also includes native `VeloInstaller.app` for macOS and `VeloInstaller.exe` for Windows, with offline payload verification, complete backup and rollback. Cavalry and TouchDesigner installers are not included yet.

## Install on macOS

1. Quit After Effects.
2. Extract the ZIP and copy the `com.velo.curveeditor` folder to:

   ```text
   ~/Library/Application Support/Adobe/CEP/extensions/
   ```

3. Reopen AE and choose `Window → Extensions → Velo`.

## Install on Windows

1. Quit After Effects.
2. Extract the ZIP and copy the `com.velo.curveeditor` folder to:

   ```text
   %APPDATA%\Adobe\CEP\extensions\
   ```

   You can enter `%APPDATA%` in Explorer, then open `Adobe\CEP\extensions\`.
3. Reopen AE and choose `Window → Extensions → Velo`.

The destination must contain `com.velo.curveeditor\index.html` and `com.velo.curveeditor\CSXS\manifest.xml`. Avoid an extra nested folder with the same name.

## Unsigned CEP panels

If AE blocks this local unsigned panel, enable `PlayerDebugMode` only for the CSXS major version used by your AE installation. Do not disable other system security protections or install extensions from untrusted sources.

macOS example — replace `7` with your CSXS major version:

```bash
defaults write com.adobe.CSXS.7 PlayerDebugMode 1
```

Windows example — replace `7` in the same way:

```bat
reg add "HKCU\Software\Adobe\CSXS.7" /v PlayerDebugMode /t REG_SZ /d 1 /f
```

Restart AE after changing this preference. It enables local debug extensions; it is not an online activation or account requirement.

## Upgrades and settings

- Quit AE before replacing the panel folder. Do not carry over a `.debug` file.
- Curves, preferences and presets are stored locally. Export important preset configurations from `Settings → Presets` before upgrading.
- If the previous page remains visible, reopen the panel so CEP loads the new resources.
- To uninstall, quit AE and remove the panel folder. You can choose whether to keep local preferences.

## Basic use

1. Select at least two consecutive keyframes of a numerical property in the target composition.
2. Choose `Read` to import existing values and tangents. `Inspect` only checks the selection and never replaces the editor curve.
3. Adjust the curve or choose a preset. Bezier supports value and speed views; then choose `Apply`.
4. One AE undo restores the state before that application.

Features include multi-segment shape-preserving insertion and deletion, tangent snapping, adaptive smoothing, multi-property application, EaseCopy, preset ordering/import/export, themes and four interface languages. Multi-segment Bezier now writes native keyframes and Temporal Ease at visible anchors for scalars and equal-length arrays rather than baking the whole curve. Visible spans containing shape-preserving hidden anchors use explicitly reported shape-preserving samples. AE clamps negative speeds on shared spatial properties such as Position to zero, so those spans also use local sampling instead of claiming unsupported native negative speeds. Elastic/Bounce and the legacy single-segment array path retain sampled keyframes.

## Validation and platform boundaries

- The manifest declares AE `17.0` and later with CSXS `7.0`. Only hosts exercised by real tests are listed as verified in the release notes.
- macOS validation uses After Effects 2026 (`26.5x89`). Other AE versions have not all been tested.
- The Windows package has structural, path, syntax and archive checks, **not a Windows AE host validation**. This is not a claim of full Windows verification.
- This release provides the AE panel and its one-click installer. TouchDesigner has a separate TD package in the repository; Cavalry and TouchDesigner installers are not included yet.

## Links

These links require internet access; installation and normal use do not.

- [v1.2.1 release notes and checksums](https://github.com/luoboruodai/velo-curve-editor/releases/tag/v1.2.1)
- [Full English guide](https://github.com/luoboruodai/velo-curve-editor/blob/v1.2.1/README.md)
- [中文指南](README.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)
