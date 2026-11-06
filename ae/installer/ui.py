from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import webbrowser

from ae.installer.core import (
    InstallError,
    installed_version,
    install_panel,
    list_backups,
    restore_backup,
    verify_backup,
    verify_payload,
)
from ae.installer.velo_installer import enable_debug_preference, resource_path

TEXT = {
    'zh': {
        'title': 'Velo 安装器', 'subtitle': 'After Effects 离线安装', 'language': 'English',
        'ready': '离线安装包已校验', 'install': '安装 Velo', 'restore': '恢复备份', 'browse': '选择…',
        'location': '安装位置', 'pathHelp': '安装到当前用户的 CEP extensions 目录，无需管理员权限。',
        'backup': '替换前完整备份旧面板（推荐）', 'debug': '允许本地未签名 CEP 面板（可选）',
        'debugHelp': '仅在 AE 阻止面板时启用。仅修改所选 CSXS 主版本的当前用户偏好。',
        'guide': '安装指南', 'open': '打开安装目录', 'release': 'Release 说明',
        'restart': '不会自动关闭 AE · 安装后请重新启动', 'working': '正在校验并写入，请稍候…',
        'success': '安装完成 · 请重新启动 AE', 'restored': '备份已恢复 · 请重新启动 AE',
        'close': '关闭', 'helpTitle': 'Velo 安装与使用指南', 'chooseBackup': '选择要恢复的备份',
        'noBackup': '此安装目录还没有可用的 Velo 备份。', 'confirmRestore': '恢复此备份？当前面板会先完整备份。',
        'notReady': '安装目录不存在，请先安装。', 'busyClose': '请等待当前文件操作完成。',
        'backupAt': '完整备份保存在：', 'settings': '保留本机设置与预设 · 失败自动回滚',
    },
    'en': {
        'title': 'Velo Installer', 'subtitle': 'Offline installation for After Effects', 'language': '中文',
        'ready': 'Offline payload verified', 'install': 'Install Velo', 'restore': 'Restore backup', 'browse': 'Browse…',
        'location': 'Install location', 'pathHelp': 'Install into your user CEP extensions directory. No administrator access needed.',
        'backup': 'Back up the previous panel before replacing it (recommended)', 'debug': 'Allow unsigned local CEP panels (optional)',
        'debugHelp': 'Use only if AE blocks the panel. Changes only the selected CSXS major version for this user.',
        'guide': 'Installation guide', 'open': 'Open install folder', 'release': 'Release notes',
        'restart': 'AE is never closed automatically · Restart after installation', 'working': 'Verifying files and installing…',
        'success': 'Installed · Restart After Effects', 'restored': 'Backup restored · Restart After Effects',
        'close': 'Close', 'helpTitle': 'Velo installation and usage guide', 'chooseBackup': 'Choose a backup to restore',
        'noBackup': 'No usable Velo backups were found in this install directory.', 'confirmRestore': 'Restore this backup? The current panel will be backed up first.',
        'notReady': 'The install directory does not exist yet. Install Velo first.', 'busyClose': 'Please wait for the current file operation to finish.',
        'backupAt': 'Full backup saved at:', 'settings': 'Local settings and presets preserved · Automatic rollback on failure',
    },
}
BG = '#202224'
CARD = '#2c2e31'
FIELD = '#3a3d41'
TEXT_COLOR = '#f0f0ec'
MUTED = '#b6bbc1'
ACCENT = '#f2b35d'
GREEN = '#72c99a'
RED = '#ef8178'


def backup_detail(backup: Path, language: str) -> str:
    path = Path(backup)
    return f'{TEXT[language]["backupAt"]}\n{path.parent.name}/{path.name}'


class InstallerApp:
    def __init__(self, payload: Path, root: Path, backup: bool = True):
        import tkinter as tk
        from tkinter import font, ttk

        self.tk = tk
        self.ttk = ttk
        self.root = tk.Tk()
        self.root.title('Velo Installer')
        self.root.geometry('620x740')
        self.root.minsize(560, 640)
        self.root.configure(bg=BG)
        self.payload = Path(payload)
        self.target = Path(root).expanduser()
        self.backup = tk.BooleanVar(value=backup)
        self.debug = tk.BooleanVar(value=False)
        self.csxs = tk.StringVar(value='7')
        self.language = 'zh'
        self.target_text = tk.StringVar(value=str(self.target))
        self.status_text = tk.StringVar()
        self.detail_text = tk.StringVar()
        self.busy = False
        self.last_result = None
        self.last_error = None
        self.events = queue.Queue()
        self.restore_path = None
        self.widgets = []
        self.action_controls = []
        self._style()
        self._build()
        self._refresh_text()
        self._refresh_status()
        self.root.protocol('WM_DELETE_WINDOW', self._close)
        self.icon = None
        icon = resource_path('assets/icon32.png')
        try:
            if icon.is_file():
                self.icon = tk.PhotoImage(file=str(icon))
        except tk.TclError:
            icon = resource_path('assets/icon32.ppm')
            if icon.is_file():
                self.icon = tk.PhotoImage(file=str(icon))
        if self.icon:
            self.root.iconphoto(True, self.icon)
        self.root.update_idletasks()

    def _style(self):
        from tkinter import font
        style = self.ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        family = 'PingFang SC' if sys.platform == 'darwin' else 'Segoe UI'
        if family not in font.families(self.root):
            family = 'TkDefaultFont'
        style.configure('TFrame', background=BG)
        style.configure('Card.TFrame', background=CARD)
        style.configure('TLabel', background=BG, foreground=TEXT_COLOR, font=(family, 11))
        style.configure('Card.TLabel', background=CARD, foreground=TEXT_COLOR, font=(family, 11))
        style.configure('Muted.Card.TLabel', background=CARD, foreground=MUTED, font=(family, 10))
        style.configure('Title.TLabel', background=BG, foreground=TEXT_COLOR, font=(family, 27, 'bold'))
        style.configure('Subtitle.TLabel', background=BG, foreground=MUTED, font=(family, 11))
        style.configure('CardTitle.TLabel', background=CARD, foreground=TEXT_COLOR, font=(family, 14, 'bold'))
        style.configure('TButton', background=FIELD, foreground=TEXT_COLOR, borderwidth=0, padding=(13, 9), font=(family, 10), focusthickness=2, focuscolor=ACCENT)
        style.map('TButton', background=[('active', '#50545a'), ('disabled', FIELD)], foreground=[('disabled', '#858b92')])
        style.configure('Accent.TButton', background=ACCENT, foreground='#29251d', padding=(16, 12), font=(family, 12, 'bold'))
        style.map('Accent.TButton', background=[('active', '#ffc778'), ('disabled', '#776b56')], foreground=[('disabled', '#d0c8b9')])
        style.configure('TCheckbutton', background=CARD, foreground=TEXT_COLOR, focuscolor=ACCENT)
        style.map('TCheckbutton', background=[('active', CARD)], foreground=[('active', TEXT_COLOR)])
        style.configure('TEntry', fieldbackground=FIELD, foreground=TEXT_COLOR, insertcolor=TEXT_COLOR, borderwidth=0, padding=9)
        style.configure('Horizontal.TProgressbar', background=ACCENT, troughcolor=FIELD, borderwidth=0)
        style.configure('TCombobox', fieldbackground=FIELD, background=FIELD, foreground=TEXT_COLOR, arrowcolor=TEXT_COLOR, borderwidth=0, padding=5)
        style.configure('Vertical.TScrollbar', background=FIELD, troughcolor=BG, borderwidth=0, arrowcolor=MUTED)

    def _card(self, row: int):
        frame = self.ttk.Frame(self.root, style='Card.TFrame', padding=18)
        frame.grid(row=row, column=0, sticky='ew', pady=(0, 12))
        frame.columnconfigure(0, weight=1)
        return frame

    def _text(self, key: str) -> str:
        return TEXT[self.language][key]

    def _register(self, widget, key: str):
        self.widgets.append((widget, key))
        return widget

    def _build(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.viewport = self.tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.scrollbar = self.ttk.Scrollbar(self.root, orient='vertical', command=self.viewport.yview)
        self.viewport.configure(yscrollcommand=self.scrollbar.set)
        self.viewport.grid(row=0, column=0, sticky='nsew')
        self.scrollbar.grid(row=0, column=1, sticky='ns')
        self.scrollbar.grid_remove()
        outer = self.ttk.Frame(self.viewport, padding=20)
        self.outer = outer
        self.outer_window = self.viewport.create_window((0, 0), window=outer, anchor='nw')
        outer.bind('<Configure>', lambda event: self._update_scroll_region())
        self.viewport.bind('<Configure>', lambda event: self.viewport.itemconfigure(self.outer_window, width=event.width))
        self.root.bind('<MouseWheel>', self._mouse_wheel)
        outer.columnconfigure(0, weight=1)

        header = self.ttk.Frame(outer)
        header.grid(row=0, column=0, sticky='ew', pady=(0, 14))
        header.columnconfigure(1, weight=1)
        brand = self.tk.Canvas(header, width=58, height=58, bg=BG, highlightthickness=0)
        brand.grid(row=0, column=0, rowspan=2, padx=(0, 14))
        points = []
        for i in range(33):
            t = i / 32
            x = 7 + 43 * t
            y = 46 - 36 * (3 * (1 - t) * t * t + t * t * t)
            points.extend((x, y))
        brand.create_line(*points, fill=ACCENT, width=3, smooth=True)
        brand.create_oval(4, 43, 10, 49, fill=TEXT_COLOR, outline='')
        brand.create_oval(47, 4, 53, 10, fill=TEXT_COLOR, outline='')
        brand.create_oval(43, 44, 53, 54, fill=GREEN, outline='')
        self.ttk.Label(header, text='Velo', style='Title.TLabel').grid(row=0, column=1, sticky='w')
        self.ttk.Label(header, text='AE 1.2.1 · OFFLINE', style='Subtitle.TLabel').grid(row=1, column=1, sticky='w')
        self.language_button = self.ttk.Button(header, command=self._toggle_language, width=9)
        self.language_button.grid(row=0, column=2, rowspan=2, sticky='e')
        self.action_controls.append(self.language_button)

        card = self.ttk.Frame(outer, style='Card.TFrame', padding=12)
        card.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        card.columnconfigure(0, weight=1)
        self.ttk.Label(card, text='After Effects', style='CardTitle.TLabel').grid(row=0, column=0, sticky='w')
        self.ttk.Label(card, text='Velo AE v1.2.1', style='Card.TLabel').grid(row=1, column=0, sticky='w', pady=(7, 0))
        self.installed_label = self.ttk.Label(card, style='Muted.Card.TLabel')
        self.installed_label.grid(row=2, column=0, sticky='w', pady=(5, 0))

        location = self.ttk.Frame(outer, style='Card.TFrame', padding=12)
        location.grid(row=2, column=0, sticky='ew', pady=(0, 10))
        location.columnconfigure(0, weight=1)
        self._register(self.ttk.Label(location, style='Card.TLabel'), 'location').grid(row=0, column=0, sticky='w')
        self.path_entry = self.ttk.Entry(location, textvariable=self.target_text)
        self.path_entry.grid(row=1, column=0, sticky='ew', pady=(9, 0), padx=(0, 8))
        self.browse_button = self._register(self.ttk.Button(location, command=self._browse), 'browse')
        self.browse_button.grid(row=1, column=1, pady=(9, 0))
        self._register(self.ttk.Label(location, style='Muted.Card.TLabel', wraplength=510), 'pathHelp').grid(row=2, column=0, columnspan=2, sticky='w', pady=(8, 0))
        self.action_controls.extend([self.path_entry, self.browse_button])

        options = self.ttk.Frame(outer, style='Card.TFrame', padding=12)
        options.grid(row=3, column=0, sticky='ew', pady=(0, 10))
        options.columnconfigure(0, weight=1)
        self.backup_check = self._register(self.ttk.Checkbutton(options, variable=self.backup), 'backup')
        self.backup_check.grid(row=0, column=0, columnspan=2, sticky='w')
        self.debug_check = self._register(self.ttk.Checkbutton(options, variable=self.debug, command=self._debug_state), 'debug')
        self.debug_check.grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.csxs_select = self.ttk.Combobox(options, textvariable=self.csxs, values=['7', '8', '9', '10', '11', '12'], state='disabled', width=4)
        self.csxs_select.grid(row=1, column=1, sticky='e', pady=(8, 0))
        self._register(self.ttk.Label(options, style='Muted.Card.TLabel', wraplength=510), 'debugHelp').grid(row=2, column=0, columnspan=2, sticky='w', pady=(7, 0))
        self.action_controls.extend([self.backup_check, self.debug_check, self.csxs_select])

        actions = self.ttk.Frame(outer)
        actions.grid(row=4, column=0, sticky='ew', pady=(2, 8))
        actions.columnconfigure(0, weight=1)
        self.install_button = self._register(self.ttk.Button(actions, command=self._install, style='Accent.TButton'), 'install')
        self.install_button.grid(row=0, column=0, columnspan=2, sticky='ew')
        self.restore_button = self._register(self.ttk.Button(actions, command=self._restore), 'restore')
        self.restore_button.grid(row=1, column=0, sticky='ew', pady=(10, 0))
        self.guide_button = self._register(self.ttk.Button(actions, command=self._guide), 'guide')
        self.guide_button.grid(row=1, column=1, sticky='ew', pady=(10, 0))
        self.action_controls.extend([self.install_button, self.restore_button, self.guide_button])

        status = self.ttk.Frame(outer)
        status.grid(row=5, column=0, sticky='ew')
        status.columnconfigure(1, weight=1)
        self.status_dot = self.tk.Canvas(status, width=12, height=12, bg=BG, highlightthickness=0)
        self.status_dot.grid(row=0, column=0, sticky='w', padx=(0, 8))
        self.status_label = self.ttk.Label(status, textvariable=self.status_text, style='Subtitle.TLabel', wraplength=520)
        self.status_label.grid(row=0, column=1, sticky='w')
        self.progress = self.ttk.Progressbar(outer, mode='indeterminate', length=160)
        self.progress.grid(row=6, column=0, sticky='ew', pady=(11, 0))
        self.progress.grid_remove()
        self.detail_label = self.ttk.Label(outer, textvariable=self.detail_text, style='Subtitle.TLabel', wraplength=530)
        self.detail_label.grid(row=7, column=0, sticky='w', pady=(7, 0))
        self.detail_label.grid_remove()

        footer = self.ttk.Frame(outer)
        footer.grid(row=8, column=0, sticky='ew', pady=(8, 0))
        footer.columnconfigure(0, weight=1)
        self._register(self.ttk.Label(footer, style='Subtitle.TLabel'), 'restart').grid(row=0, column=0, sticky='w')
        self.open_button = self._register(self.ttk.Button(footer, command=self._open_directory), 'open')
        self.open_button.grid(row=1, column=0, sticky='w', pady=(10, 0))
        self.release_button = self._register(self.ttk.Button(footer, command=lambda: webbrowser.open('https://github.com/luoboruodai/velo-curve-editor/releases/tag/v1.2.1')), 'release')
        self.release_button.grid(row=1, column=1, sticky='e', pady=(10, 0))

    def _update_scroll_region(self):
        bounds = self.viewport.bbox('all')
        if not bounds:
            return
        self.viewport.configure(scrollregion=bounds)
        if bounds[3] > self.viewport.winfo_height():
            self.scrollbar.grid()
        else:
            self.scrollbar.grid_remove()

    def _fit_height(self):
        self.root.update_idletasks()
        required = self.outer.winfo_reqheight()
        available = max(640, self.root.winfo_screenheight() - 96)
        height = max(640, min(required, available))
        width = max(560, self.root.winfo_width())
        self.root.geometry(f'{width}x{height}')
        self.root.update_idletasks()
        self._update_scroll_region()

    def _mouse_wheel(self, event):
        if self.scrollbar.winfo_ismapped():
            self.viewport.yview_scroll(-1 if event.delta > 0 else 1, 'units')
            return 'break'
        return None

    def _refresh_text(self):
        self.root.title(self._text('title'))
        self.language_button.configure(text=self._text('language'))
        for widget, key in self.widgets:
            widget.configure(text=self._text(key))
        self._fit_height()

    def _refresh_status(self):
        try:
            verify_payload(self.payload)
            version = installed_version(self.target / 'com.velo.curveeditor')
            self.installed_label.configure(text=f'{self._text("ready")} · ' + (f'v{version}' if version else '—'))
            status = self._text('success' if self.last_result and self.last_result['action'] == 'install' else 'restored') if self.last_result else self._text('ready')
            self._set_status(status, GREEN)
        except (InstallError, OSError, ValueError) as error:
            self._set_status(str(error), RED)
            self.install_button.state(['disabled'])
        self._fit_height()

    def _set_status(self, text: str, color: str):
        self.status_text.set(text)
        self.status_dot.delete('all')
        self.status_dot.create_oval(1, 1, 11, 11, fill=color, outline='')

    def _toggle_language(self):
        self.language = 'en' if self.language == 'zh' else 'zh'
        self._refresh_text()
        self._refresh_status()

    def _debug_state(self):
        self.csxs_select.configure(state='readonly' if self.debug.get() and not self.busy else 'disabled')

    def _browse(self):
        from tkinter import filedialog
        selected = filedialog.askdirectory(initialdir=self.target_text.get(), title=self._text('location'), parent=self.root)
        if selected:
            self.target_text.set(selected)
            self.target = Path(selected)
            self._refresh_status()

    def _install(self):
        self._run('install')

    def _restore(self):
        from tkinter import filedialog, messagebox
        backups = list_backups(self.target)
        if not backups:
            messagebox.showinfo(self._text('restore'), self._text('noBackup'), parent=self.root)
            return
        selected = filedialog.askdirectory(initialdir=str(self.target / 'Velo-backup'), title=self._text('chooseBackup'), parent=self.root)
        if not selected:
            return
        try:
            verify_backup(self.target, Path(selected))
        except (InstallError, OSError, ValueError) as error:
            self._set_status(str(error), RED)
            return
        if messagebox.askyesno(self._text('restore'), self._text('confirmRestore'), parent=self.root):
            self.restore_path = Path(selected)
            self._run('restore')

    def _run(self, action: str):
        if self.busy:
            return
        try:
            self.target = Path(self.target_text.get()).expanduser()
            if not str(self.target).strip():
                raise InstallError(self._text('location'))
            verify_payload(self.payload)
        except (InstallError, OSError, ValueError) as error:
            self._set_status(str(error), RED)
            return
        self.busy = True
        self.last_error = None
        self.last_result = None
        for control in self.action_controls:
            control.state(['disabled'])
        self._set_status(self._text('working'), ACCENT)
        self.detail_text.set('')
        self.detail_label.grid_remove()
        self.progress.grid()
        self.progress.start(12)

        def worker():
            try:
                if action == 'install':
                    result = install_panel(self.payload, self.target, self.backup.get())
                    if self.debug.get():
                        enable_debug_preference(self.csxs.get())
                        result['debugCsxs'] = self.csxs.get()
                else:
                    result = restore_backup(self.target, self.restore_path, self.backup.get())
                self.events.put(('success', result))
            except Exception as error:
                self.events.put(('error', error))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(80, self._poll)

    def _poll(self):
        try:
            kind, value = self.events.get_nowait()
        except queue.Empty:
            self.root.after(80, self._poll)
            return
        self.busy = False
        self.progress.stop()
        self.progress.grid_remove()
        for control in self.action_controls:
            control.state(['!disabled'])
        self._debug_state()
        if kind == 'success':
            self.last_result = value
            self._set_status(self._text('success' if value['action'] == 'install' else 'restored'), GREEN)
            backup = value.get('backup')
            self.detail_text.set(backup_detail(backup, self.language) if backup else '')
            if backup:
                self.detail_label.grid()
            else:
                self.detail_label.grid_remove()
            self._refresh_status()
        else:
            self.last_error = str(value)
            self._set_status(self.last_error, RED)
            self.detail_text.set('')

    def _open_directory(self):
        if not self.target.is_dir():
            self._set_status(self._text('notReady'), ACCENT)
            return
        if sys.platform == 'darwin':
            subprocess.Popen(['open', str(self.target)])
        elif os.name == 'nt':
            os.startfile(self.target)
        else:
            subprocess.Popen(['xdg-open', str(self.target)])

    def _guide(self):
        window = self.tk.Toplevel(self.root)
        window.title(self._text('helpTitle'))
        window.geometry('700x600')
        window.configure(bg=BG)
        text = self.tk.Text(window, wrap='word', bg=CARD, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, relief='flat', padx=22, pady=20, font=('TkTextFont', 11), spacing3=6)
        text.pack(fill='both', expand=True, padx=14, pady=(14, 8))
        guide = self.payload / 'guides' / ('README.md' if self.language == 'zh' else 'README.en.md')
        text.insert('1.0', guide.read_text(encoding='utf-8'))
        text.configure(state='disabled')
        self.ttk.Button(window, text=self._text('close'), command=window.destroy).pack(pady=(0, 14))

    def _close(self):
        if self.busy:
            self._set_status(self._text('busyClose'), ACCENT)
        else:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def launch(payload: Path, root: Path, backup: bool = True):
    InstallerApp(payload, root, backup).run()


def show_error(message: str):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror('Velo Installer', message, parent=root)
    root.destroy()
