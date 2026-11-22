#![windows_subsystem = "windows"]

mod core;
mod theme;

use std::ffi::c_void;
use std::path::PathBuf;
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex};
use std::thread;

use windows::core::{w, BOOL, PCWSTR, PWSTR};
use windows::Win32::Foundation::{
    COLORREF, HINSTANCE, HWND, LPARAM, LRESULT, RECT, TRUE, WPARAM,
};
use windows::Win32::Graphics::Dwm::{
    DwmSetWindowAttribute, DWMWA_CAPTION_COLOR, DWMWA_TEXT_COLOR, DWMWA_USE_IMMERSIVE_DARK_MODE,
};
use windows::Win32::Graphics::Gdi::{
    BeginPaint, BitBlt, CLEARTYPE_QUALITY, CLIP_DEFAULT_PRECIS, CreateCompatibleBitmap,
    CreateCompatibleDC, CreateFontW, CreateSolidBrush, DEFAULT_CHARSET, DEFAULT_PITCH, DeleteDC,
    DeleteObject, DrawTextW, EndPaint, FF_DONTCARE, FillRect, FrameRect, HBRUSH, HDC, HFONT,
    HGDIOBJ, InvalidateRect, OUT_DEFAULT_PRECIS, PAINTSTRUCT, SRCCOPY, SelectObject, SetBkMode,
    SetTextColor, TRANSPARENT, UpdateWindow, DT_CENTER, DT_END_ELLIPSIS, DT_LEFT, DT_RIGHT,
    DT_SINGLELINE, DT_VCENTER, DT_WORDBREAK, DRAW_TEXT_FORMAT,
};
use windows::Win32::System::Com::{
    CoInitializeEx, CoTaskMemFree, CoUninitialize, COINIT_APARTMENTTHREADED,
};
use windows::Win32::System::LibraryLoader::GetModuleHandleW;
use windows::Win32::System::SystemInformation::GetLocalTime;
use windows::Win32::UI::HiDpi::{
    GetDpiForWindow, SetProcessDpiAwarenessContext, DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2,
};
use windows::Win32::UI::Shell::{
    SHBrowseForFolderW, SHGetPathFromIDListW, BROWSEINFOW, BIF_NEWDIALOGSTYLE, BIF_RETURNONLYFSDIRS,
};
use windows::Win32::UI::WindowsAndMessaging::{
    CreateWindowExW, DefWindowProcW, DestroyWindow, DispatchMessageW, GetClientRect, GetMessageW,
    GetWindowLongPtrW, IDC_ARROW, IDYES, KillTimer, LoadCursorW, MB_ICONERROR, MB_ICONINFORMATION,
    MB_ICONQUESTION, MB_OK, MB_YESNO, MSG, MessageBoxW, PostQuitMessage, RegisterClassW, SW_SHOW,
    SWP_NOMOVE, SWP_NOZORDER, SetTimer, SetWindowLongPtrW, SetWindowPos, ShowWindow,
    TranslateMessage, WM_CLOSE, WM_CREATE, WM_DESTROY, WM_DPICHANGED, WM_ERASEBKGND,
    WM_GETMINMAXINFO, WM_LBUTTONUP, WM_MOUSEMOVE, WM_PAINT, WM_SIZE, WM_TIMER, WNDCLASSW,
    GWLP_USERDATA, MINMAXINFO, MESSAGEBOX_RESULT, MESSAGEBOX_STYLE, WINDOW_EX_STYLE, WINDOW_STYLE, WNDCLASS_STYLES,
};
use windows::Win32::UI::Controls::WM_MOUSELEAVE;
use windows::Win32::UI::Input::KeyboardAndMouse::{TrackMouseEvent, TME_LEAVE, TRACKMOUSEEVENT};

const WM_APP_READY: u32 = 0x8000 + 1;
const WIN_W: i32 = 1120;
const WIN_H: i32 = 680;

struct Fonts {
    head: HFONT,
    body: HFONT,
    mono: HFONT,
    small: HFONT,
}

impl Fonts {
    fn new(scale: f32) -> Self {
        Self {
            head: make_font((30.0 * scale) as i32, 600, theme::HEAD_FONT),
            body: make_font((14.0 * scale) as i32, 400, theme::BODY_FONT),
            mono: make_font((12.0 * scale) as i32, 400, theme::MONO_FONT),
            small: make_font((11.0 * scale) as i32, 400, theme::MONO_FONT),
        }
    }
}

impl Drop for Fonts {
    fn drop(&mut self) {
        unsafe {
            let _ = DeleteObject(HGDIOBJ(self.head.0));
            let _ = DeleteObject(HGDIOBJ(self.body.0));
            let _ = DeleteObject(HGDIOBJ(self.mono.0));
            let _ = DeleteObject(HGDIOBJ(self.small.0));
        }
    }
}

fn make_font(height: i32, weight: i32, name: &str) -> HFONT {
    let w: Vec<u16> = name.encode_utf16().chain(std::iter::once(0)).collect();
    unsafe {
        CreateFontW(
            -height, 0, 0, 0, weight, 0, 0, 0, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
            CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, (DEFAULT_PITCH.0 | FF_DONTCARE.0) as u32,
            PCWSTR(w.as_ptr()),
        )
    }
}

#[derive(Clone, Copy, PartialEq)]
enum BtnStyle { Filled, Outline, Small }

#[derive(Clone)]
struct Button {
    id: u32,
    rect: RECT,
    label: String,
    style: BtnStyle,
    enabled: bool,
}

struct Runtime {
    status: Option<core::Status>,
    refreshing: bool,
    busy: bool,
    operation: String,
    progress: f32,
    progress_text: String,
    logs: Vec<String>,
    dirty: bool,
    last_result: Option<core::OperationResult>,
}

impl Runtime {
    fn new() -> Self {
        let mut r = Self {
            status: None, refreshing: false, busy: false,
            operation: "等待操作".into(), progress: 0.0,
            progress_text: "等待操作".into(), logs: Vec::new(),
            dirty: true, last_result: None,
        };
        r.log("PIP-BOY 3000 MK IV  //  TERMLINK READY");
        r.log("VAULT-TEC 汉化安装程序已启动，正在检测游戏目录...");
        r
    }

    fn log(&mut self, s: impl Into<String>) {
        let t = unsafe { GetLocalTime() };
        self.logs.push(format!("[{:02}:{:02}:{:02}] {}", t.wHour, t.wMinute, t.wSecond, s.into()));
        if self.logs.len() > 240 { self.logs.remove(0); }
        self.dirty = true;
    }
}

struct App {
    hwnd: HWND,
    scale: f32,
    fonts: Fonts,
    rt: Arc<Mutex<Runtime>>,
    game_path: String,
    payload: PathBuf,
    buttons: Vec<Button>,
    hover: Option<u32>,
    hand_cursor: isize,
}

impl App {
    fn new(hwnd: HWND) -> Self {
        let dpi = unsafe { GetDpiForWindow(hwnd) };
        let scale = if dpi == 0 { 1.0 } else { dpi as f32 / 96.0 };
        let hand = unsafe { LoadCursorW(None, w!("HAND")).map(|c| c.0 as isize).unwrap_or(0) };
        let app = Self {
            hwnd,
            scale,
            fonts: Fonts::new(scale),
            rt: Arc::new(Mutex::new(Runtime::new())),
            game_path: core::detect_game_path().to_string_lossy().into_owned(),
            payload: core::payload_path(),
            buttons: Vec::new(),
            hover: None,
            hand_cursor: hand,
        };
        app.refresh();
        unsafe { SetTimer(Some(hwnd), 1, 50, None); }
        app
    }

    fn s(&self, v: f32) -> i32 { (v * self.scale).round() as i32 }

    fn rect(&self, x: f32, y: f32, w: f32, h: f32) -> RECT {
        RECT { left: self.s(x), top: self.s(y), right: self.s(x + w), bottom: self.s(y + h) }
    }

    fn refresh(&self) {
        {
            let mut r = self.rt.lock().unwrap();
            if r.refreshing { return; }
            r.refreshing = true;
            r.log("检测游戏与汉化包状态...");
        }
        let rt = self.rt.clone();
        let game = self.game_path.clone();
        let payload = self.payload.clone();
        thread::spawn(move || {
            let st = core::status(std::path::Path::new(&game), &payload);
            let mut r = rt.lock().unwrap();
            r.status = Some(st);
            r.refreshing = false;
            r.dirty = true;
            r.log("检测完成。");
        });
    }

    fn msg(&self, text: &str, caption: &str, flags: MESSAGEBOX_STYLE) -> MESSAGEBOX_RESULT {
        let t: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
        let c: Vec<u16> = caption.encode_utf16().chain(std::iter::once(0)).collect();
        unsafe { MessageBoxW(Some(self.hwnd), PCWSTR(t.as_ptr()), PCWSTR(c.as_ptr()), flags | MB_OK) }
    }

    fn confirm(&self, text: &str, caption: &str) -> bool {
        let t: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
        let c: Vec<u16> = caption.encode_utf16().chain(std::iter::once(0)).collect();
        unsafe {
            MessageBoxW(Some(self.hwnd), PCWSTR(t.as_ptr()), PCWSTR(c.as_ptr()), MB_YESNO | MB_ICONQUESTION)
                == IDYES
        }
    }

    fn start_install(&self) {
        if self.rt.lock().unwrap().busy { return; }
        if core::is_game_running() {
            self.msg("请先完全退出 Fallout Shelter，再安装汉化。", "游戏正在运行", MB_ICONERROR);
            return;
        }
        if !self.confirm("将把汉化 data.unity3d 写入游戏目录，并保留原版备份。\n\n继续？", "安装汉化") {
            return;
        }
        let rt = self.rt.clone();
        let game = PathBuf::from(&self.game_path);
        let payload = self.payload.clone();
        {
            let mut r = rt.lock().unwrap();
            r.busy = true;
            r.progress = 0.0;
            r.progress_text = "准备中...".into();
            r.operation = "安装汉化".into();
            r.log("---------- 开始安装汉化 ----------");
            r.dirty = true;
        }
        thread::spawn(move || {
            let cancel = AtomicBool::new(false);
            let res = core::install(&game, &payload, &cancel, |done, total| {
                if let Ok(mut r) = rt.lock() {
                    r.progress = if total == 0 { 0.0 } else { done as f32 / total as f32 };
                    r.progress_text = format!("{:.1}%   {} / {}", r.progress * 100.0,
                        fmt_size(done), fmt_size(total));
                    r.dirty = true;
                }
            });
            let mut r = rt.lock().unwrap();
            r.busy = false;
            r.progress = 1.0;
            r.dirty = true;
            match res {
                Ok(v) => {
                    if v.backup_created { r.log("已创建原版备份 data.unity3d.en.bak。"); }
                    r.log(v.message.clone());
                    r.progress_text = "安装完成".into();
                }
                Err(e) => {
                    r.log(format!("ERROR: {e}"));
                    r.progress_text = "安装失败".into();
                }
            }
            if let Some(st) = Some(core::status(&game, &payload)) {
                r.status = Some(st);
            }
        });
    }

    fn start_uninstall(&self) {
        if self.rt.lock().unwrap().busy { return; }
        if core::is_game_running() {
            self.msg("请先完全退出 Fallout Shelter，再还原英文。", "游戏正在运行", MB_ICONERROR);
            return;
        }
        if !self.confirm("将用 data.unity3d.en.bak 覆盖当前汉化文件。\n\n继续？", "还原英文") {
            return;
        }
        let rt = self.rt.clone();
        let game = PathBuf::from(&self.game_path);
        {
            let mut r = rt.lock().unwrap();
            r.busy = true;
            r.progress = 0.0;
            r.operation = "还原英文".into();
            r.progress_text = "准备中...".into();
            r.log("---------- 开始还原英文 ----------");
            r.dirty = true;
        }
        thread::spawn(move || {
            let cancel = AtomicBool::new(false);
            let res = core::uninstall(&game, &cancel, |done, total| {
                if let Ok(mut r) = rt.lock() {
                    r.progress = if total == 0 { 0.0 } else { done as f32 / total as f32 };
                    r.progress_text = format!("{:.1}%   {} / {}", r.progress * 100.0,
                        fmt_size(done), fmt_size(total));
                    r.dirty = true;
                }
            });
            let mut r = rt.lock().unwrap();
            r.busy = false;
            r.progress = 1.0;
            r.dirty = true;
            match res {
                Ok(v) => { r.log(v.message); r.progress_text = "还原完成".into(); }
                Err(e) => { r.log(format!("ERROR: {e}")); r.progress_text = "还原失败".into(); }
            }
            let st = core::status(&game, &core::payload_path());
            r.status = Some(st);
        });
    }

    fn verify(&self) {
        if self.rt.lock().unwrap().busy { return; }
        let game = PathBuf::from(&self.game_path);
        let payload = self.payload.clone();
        let rt = self.rt.clone();
        {
            let mut r = rt.lock().unwrap();
            r.log("---------- 校验文件 ----------");
            r.dirty = true;
        }
        thread::spawn(move || {
            let v = core::verify(&game, &payload);
            let mut r = rt.lock().unwrap();
            if v.match_ok {
                r.log("校验通过：data.unity3d 与汉化包一致。");
            } else {
                r.log(format!("校验不一致：data {} / payload {}",
                    v.data_md5.as_deref().unwrap_or("?"), v.payload_md5.as_deref().unwrap_or("?")));
            }
            r.dirty = true;
        });
    }

    fn browse(&mut self) {
        unsafe {
            let mut display = [0u16; 260];
            let mut bi = BROWSEINFOW {
                hwndOwner: self.hwnd,
                pszDisplayName: PWSTR(display.as_mut_ptr()),
                lpszTitle: w!("选择 Fallout Shelter 游戏目录"),
                ulFlags: (BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE) as u32,
                ..Default::default()
            };
            let pidl = SHBrowseForFolderW(&bi);
            if pidl.is_null() { return; }
            let mut buf = [0u16; 260];
            if SHGetPathFromIDListW(pidl, &mut buf).as_bool() {
                let len = buf.iter().position(|&c| c == 0).unwrap_or(0);
                self.game_path = String::from_utf16_lossy(&buf[..len]);
                self.refresh();
            }
            CoTaskMemFree(Some(pidl as *const c_void));
        }
    }

    fn on_click(&mut self, x: i32, y: i32) {
        let id = self.buttons.iter()
            .find(|b| b.enabled && x >= b.rect.left && x <= b.rect.right && y >= b.rect.top && y <= b.rect.bottom)
            .map(|b| b.id);
        let Some(id) = id else { return; };
        match id {
            1 => self.browse(),
            2 => self.refresh(),
            10 => self.start_install(),
            11 => self.start_uninstall(),
            12 => self.verify(),
            13 => core::open_folder(std::path::Path::new(&self.game_path)),
            _ => {}
        }
    }

    fn on_mouse_move(&mut self, x: i32, y: i32) {
        let hover = self.buttons.iter()
            .find(|b| b.enabled && x >= b.rect.left && x <= b.rect.right && y >= b.rect.top && y <= b.rect.bottom)
            .map(|b| b.id);
        if hover != self.hover {
            self.hover = hover;
            unsafe { let _ = InvalidateRect(Some(self.hwnd), None, false); }
        }
        unsafe {
            let mut t = TRACKMOUSEEVENT {
                cbSize: std::mem::size_of::<TRACKMOUSEEVENT>() as u32,
                dwFlags: TME_LEAVE,
                hwndTrack: self.hwnd,
                dwHoverTime: 0,
            };
            let _ = TrackMouseEvent(&mut t);
        }
    }

    fn poll(&mut self) {
        let dirty = {
            let mut r = self.rt.lock().unwrap();
            let d = r.dirty;
            r.dirty = false;
            d
        };
        if dirty { unsafe { let _ = InvalidateRect(Some(self.hwnd), None, false); } }
    }

    fn render(&mut self, hdc: HDC, w: i32, h: i32) {
        let mem = unsafe { CreateCompatibleDC(Some(hdc)) };
        let bmp = unsafe { CreateCompatibleBitmap(hdc, w, h) };
        let old = unsafe { SelectObject(mem, HGDIOBJ(bmp.0)) };
        self.draw(mem, w, h);
        unsafe {
            let _ = BitBlt(hdc, 0, 0, w, h, Some(mem), 0, 0, SRCCOPY);
            SelectObject(mem, old);
            let _ = DeleteObject(HGDIOBJ(bmp.0));
            let _ = DeleteDC(mem);
        }
    }

    fn draw(&mut self, dc: HDC, w: i32, h: i32) {
        unsafe {
            SetBkMode(dc, TRANSPARENT);
            fill(dc, 0, 0, w, h, theme::BG);
            let mut y = 0;
            while y < h { fill(dc, 0, y, w, 1, theme::SCAN); y += self.s(4.0); }
        }

        // header
        fill(dc, 0, 0, w, self.s(92.0), theme::PANEL_ALT);
        fill(dc, 0, self.s(91.0), w, self.s(1.0), theme::LINE);
        text(dc, "VAULT-TEC // 汉化安装程序", self.rect(24.0, 14.0, 700.0, 40.0),
             &self.fonts.head, theme::ACCENT_BRIGHT, DT_LEFT | DT_SINGLELINE | DT_VCENTER);
        text(dc, "FALLOUT SHELTER 2.7.0  ·  SIMPLIFIED CHINESE  ·  PIP-BOY 3000 MK IV",
             self.rect(24.0, 54.0, 760.0, 24.0), &self.fonts.mono, theme::MUTED,
             DT_LEFT | DT_SINGLELINE | DT_VCENTER);

        let (badge, badge_color) = {
            let r = self.rt.lock().unwrap();
            match &r.status {
                None => ("检测中".to_string(), theme::WARNING),
                Some(st) if !st.game_exists => ("未检测到游戏".into(), theme::DANGER),
                Some(st) if !st.payload_exists => ("缺少汉化包".into(), theme::DANGER),
                Some(st) if st.patched => (format!("已汉化  v{}", st.version), theme::ACCENT),
                Some(st) if st.backup_exists && st.data_md5 == st.backup_md5 => ("原版英文".into(), theme::WARNING),
                _ => ("文件状态未知".into(), theme::DANGER),
            }
        };
        let bw = self.s(230.0);
        let badge_rect = RECT { left: w - bw - self.s(24.0), top: self.s(30.0), right: w - self.s(24.0), bottom: self.s(58.0) };
        fill(dc, badge_rect.left, badge_rect.top, badge_rect.right - badge_rect.left, badge_rect.bottom - badge_rect.top, theme::PANEL);
        frame(dc, badge_rect, badge_color);
        text(dc, &badge, badge_rect, &self.fonts.mono, badge_color, DT_CENTER | DT_SINGLELINE | DT_VCENTER);

        // snapshot state
        let (status, busy, progress, progress_text, operation, logs) = {
            let r = self.rt.lock().unwrap();
            (r.status.clone(), r.busy, r.progress, r.progress_text.clone(),
             r.operation.clone(), r.logs.clone())
        };
        let (has_game, has_payload, has_backup) = match &status {
            Some(st) => (st.game_exists, st.payload_exists, st.backup_exists),
            None => (false, false, false),
        };

        // left column
        let x = 24.0;
        let lw = 520.0;
        text(dc, "SYSTEM STATUS", self.rect(x, 108.0, lw, 20.0), &self.fonts.small, theme::ACCENT, DT_LEFT | DT_SINGLELINE);
        let card = self.rect(x, 130.0, lw, 144.0);
        panel(dc, card);
        let rows = [
            ("游戏版本", status.as_ref().map(|s| s.version.clone()).unwrap_or("—".into())),
            ("data.unity3d", status.as_ref().map(|s| format!("{}  ·  {}", fmt_size(s.data_size), short_md5(s.data_md5.as_deref()))).unwrap_or("—".into())),
            ("原版备份", status.as_ref().map(|s| if s.backup_exists { format!("{}  ·  {}", fmt_size(s.backup_size), short_md5(s.backup_md5.as_deref())) } else { "无（首次安装时创建）".into() }).unwrap_or("—".into())),
            ("当前状态", status.as_ref().map(|s| if s.patched { "已安装汉化".to_string() } else if s.backup_exists && s.data_md5 == s.backup_md5 { "原版英文".to_string() } else { "未汉化 / 已修改".to_string() }).unwrap_or("—".into())),
        ];
        for (i, (k, v)) in rows.iter().enumerate() {
            let yy = 140.0 + i as f32 * 28.0;
            text(dc, k, self.rect(x + 16.0, yy, 110.0, 20.0), &self.fonts.mono, theme::MUTED, DT_LEFT | DT_SINGLELINE | DT_VCENTER);
            text(dc, v, self.rect(x + 132.0, yy, lw - 148.0, 20.0), &self.fonts.mono, theme::TEXT, DT_LEFT | DT_SINGLELINE | DT_VCENTER | DT_END_ELLIPSIS);
        }

        text(dc, "GAME DIRECTORY", self.rect(x, 286.0, lw, 20.0), &self.fonts.small, theme::ACCENT, DT_LEFT | DT_SINGLELINE);
        let path_card = self.rect(x, 306.0, lw, 54.0);
        panel(dc, path_card);
        text(dc, &self.game_path, self.rect(x + 14.0, 316.0, lw - 112.0, 34.0), &self.fonts.small, theme::TEXT, DT_LEFT | DT_SINGLELINE | DT_VCENTER | DT_END_ELLIPSIS);
        let browse_rect = self.rect(x + lw - 92.0, 317.0, 78.0, 32.0);
        self.draw_button(dc, 1, browse_rect, "浏览", BtnStyle::Small, true);

        text(dc, "OPERATIONS", self.rect(x, 372.0, lw, 20.0), &self.fonts.small, theme::ACCENT, DT_LEFT | DT_SINGLELINE);
        let bw2 = (lw - 10.0) / 2.0;
        self.draw_button(dc, 10, self.rect(x, 394.0, bw2, 38.0), "安装汉化", BtnStyle::Filled, !busy && has_game && has_payload);
        self.draw_button(dc, 11, self.rect(x + bw2 + 10.0, 394.0, bw2, 38.0), "还原英文", BtnStyle::Outline, !busy && has_backup);
        self.draw_button(dc, 12, self.rect(x, 440.0, bw2, 38.0), "校验文件", BtnStyle::Outline, !busy && has_game && has_payload);
        self.draw_button(dc, 13, self.rect(x + bw2 + 10.0, 440.0, bw2, 38.0), "打开游戏目录", BtnStyle::Outline, has_game);

        text(dc, "PROGRESS", self.rect(x, 490.0, lw, 20.0), &self.fonts.small, theme::ACCENT, DT_LEFT | DT_SINGLELINE);
        let pcard = self.rect(x, 510.0, lw, 72.0);
        panel(dc, pcard);
        text(dc, &operation, self.rect(x + 14.0, 518.0, lw - 28.0, 18.0), &self.fonts.mono, theme::TEXT, DT_LEFT | DT_SINGLELINE | DT_VCENTER);
        let bar = self.rect(x + 14.0, 544.0, lw - 28.0, 12.0);
        fill(dc, bar.left, bar.top, bar.right - bar.left, bar.bottom - bar.top, theme::PANEL_ALT);
        let fillw = ((bar.right - bar.left) as f32 * progress.clamp(0.0, 1.0)) as i32;
        if fillw > 0 { fill(dc, bar.left, bar.top, fillw, bar.bottom - bar.top, theme::ACCENT); }
        frame(dc, bar, theme::LINE);
        text(dc, &progress_text, self.rect(x + 14.0, 558.0, lw - 28.0, 18.0), &self.fonts.small, theme::MUTED, DT_LEFT | DT_SINGLELINE | DT_VCENTER);

        text(dc, "安装前会自动备份原版 data.unity3d，请先关闭游戏。",
             self.rect(x, 592.0, lw, 20.0), &self.fonts.small, theme::MUTED,
             DT_LEFT | DT_SINGLELINE | DT_VCENTER);

        // log panel
        let lx = 568.0;
        let ly = 130.0;
        let lw2 = (w as f32 / self.scale) - lx - 24.0;
        let lh = (h as f32 / self.scale) - ly - 54.0;
        let log_card = self.rect(lx, ly, lw2, lh);
        panel(dc, log_card);
        text(dc, "OPERATION LOG", self.rect(lx + 14.0, ly + 10.0, 200.0, 20.0), &self.fonts.small, theme::ACCENT, DT_LEFT | DT_SINGLELINE);
        let lines = ((lh - 44.0) / 18.0) as usize;
        let start = logs.len().saturating_sub(lines);
        unsafe {
            let clip = self.rect(lx + 10.0, ly + 36.0, lw2 - 20.0, lh - 44.0);
            let _ = windows::Win32::Graphics::Gdi::IntersectClipRect(dc, clip.left, clip.top, clip.right, clip.bottom);
        }
        for (i, line) in logs[start..].iter().enumerate() {
            let color = if line.contains("ERROR") { theme::DANGER } else { theme::ACCENT };
            text(dc, line, self.rect(lx + 14.0, ly + 38.0 + i as f32 * 18.0, lw2 - 28.0, 18.0),
                 &self.fonts.small, color, DT_LEFT | DT_SINGLELINE | DT_END_ELLIPSIS);
        }
        unsafe { let _ = windows::Win32::Graphics::Gdi::SelectClipRgn(dc, None); }

        // footer
        fill(dc, 0, h - self.s(42.0), w, self.s(1.0), theme::LINE);
        fill(dc, 0, h - self.s(41.0), w, self.s(41.0), theme::PANEL_ALT);
        text(dc, "VAULT-TEC INDUSTRIES  ·  ROBCO INDUSTRIES (TM) TERMLINK",
             self.rect(24.0, (h as f32 / self.scale) - 34.0, 700.0, 24.0),
             &self.fonts.small, theme::MUTED, DT_LEFT | DT_SINGLELINE | DT_VCENTER);
        text(dc, "github.com/xsxz01/fallout-shelter-zh-cn",
             self.rect((w as f32 / self.scale) - 360.0, (h as f32 / self.scale) - 34.0, 336.0, 24.0),
             &self.fonts.small, theme::ACCENT, DT_RIGHT | DT_SINGLELINE | DT_VCENTER);
    }

    fn draw_button(&mut self, dc: HDC, id: u32, rect: RECT, label: &str, style: BtnStyle, enabled: bool) {
        self.buttons.push(Button { id, rect, label: label.into(), style, enabled });
        let hovered = self.hover == Some(id) && enabled;
        let (bg, fg, border) = if !enabled {
            (theme::PANEL, theme::MUTED, theme::LINE)
        } else {
            match style {
                BtnStyle::Filled => (if hovered { theme::ACCENT_BRIGHT } else { theme::ACCENT }, theme::BG, theme::ACCENT_BRIGHT),
                BtnStyle::Outline => (if hovered { theme::PANEL_ALT } else { theme::PANEL }, theme::TEXT, theme::LINE),
                BtnStyle::Small => (if hovered { theme::PANEL_ALT } else { theme::PANEL }, theme::TEXT, theme::LINE),
            }
        };
        unsafe {
            let brush = CreateSolidBrush(COLORREF(theme::BG));
            let _ = FillRect(dc, &rect, brush);
            let _ = DeleteObject(HGDIOBJ(brush.0));
        }
        fill(dc, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top, bg);
        frame(dc, rect, border);
        text(dc, label, rect, &self.fonts.body, fg,
             DT_CENTER | DT_SINGLELINE | DT_VCENTER);
    }
}

fn short_md5(md5: Option<&str>) -> String {
    match md5 {
        Some(s) if s.len() > 12 => format!("{}…", &s[..12]),
        Some(s) => s.to_string(),
        None => "—".into(),
    }
}

fn fmt_size(bytes: u64) -> String {
    let mut v = bytes as f64;
    let units = ["B", "KB", "MB", "GB"];
    let mut i = 0;
    while v >= 1024.0 && i < units.len() - 1 { v /= 1024.0; i += 1; }
    format!("{v:.1} {}", units[i])
}

fn text(dc: HDC, s: &str, rc: RECT, font: &HFONT, color: u32, flags: DRAW_TEXT_FORMAT) {
    unsafe {
        SelectObject(dc, HGDIOBJ(font.0));
        SetTextColor(dc, COLORREF(color));
        let mut w: Vec<u16> = s.encode_utf16().collect();
        let mut r = rc;
        let _ = DrawTextW(dc, &mut w, &mut r, flags);
    }
}

fn fill(dc: HDC, x: i32, y: i32, w: i32, h: i32, color: u32) {
    unsafe {
        let brush = CreateSolidBrush(COLORREF(color));
        let r = RECT { left: x, top: y, right: x + w, bottom: y + h };
        let _ = FillRect(dc, &r, brush);
        let _ = DeleteObject(HGDIOBJ(brush.0));
    }
}

fn frame(dc: HDC, r: RECT, color: u32) {
    unsafe {
        let brush = CreateSolidBrush(COLORREF(color));
        let _ = FrameRect(dc, &r, brush);
        let _ = DeleteObject(HGDIOBJ(brush.0));
    }
}

fn panel(dc: HDC, r: RECT) {
    fill(dc, r.left, r.top, r.right - r.left, r.bottom - r.top, theme::PANEL);
    frame(dc, r, theme::LINE);
    // corner ticks
    let t = 8;
    fill(dc, r.left, r.top, t, 2, theme::ACCENT);
    fill(dc, r.left, r.top, 2, t, theme::ACCENT);
    fill(dc, r.right - t, r.bottom - 2, t, 2, theme::ACCENT);
    fill(dc, r.right - 2, r.bottom - t, 2, t, theme::ACCENT);
}

unsafe extern "system" fn wndproc(hwnd: HWND, msg: u32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
    let app_ptr = GetWindowLongPtrW(hwnd, GWLP_USERDATA) as *mut App;
    match msg {
        WM_CREATE => LRESULT(0),
        WM_PAINT => {
            let mut ps = PAINTSTRUCT::default();
            let hdc = BeginPaint(hwnd, &mut ps);
            if app_ptr.is_null() {
                let mut r = RECT::default();
                let _ = GetClientRect(hwnd, &mut r);
                fill(hdc, 0, 0, r.right, r.bottom, theme::BG);
            } else {
                let app = &mut *app_ptr;
                let mut r = RECT::default();
                let _ = GetClientRect(hwnd, &mut r);
                app.render(hdc, r.right, r.bottom);
            }
            let _ = EndPaint(hwnd, &ps);
            LRESULT(0)
        }
        WM_SIZE => { if !app_ptr.is_null() { let _ = InvalidateRect(Some(hwnd), None, false); } LRESULT(0) }
        WM_ERASEBKGND => LRESULT(1),
        WM_TIMER => { if !app_ptr.is_null() { (&mut *app_ptr).poll(); } LRESULT(0) }
        WM_MOUSEMOVE => {
            if !app_ptr.is_null() {
                let x = (lparam.0 & 0xFFFF) as i16 as i32;
                let y = ((lparam.0 >> 16) & 0xFFFF) as i16 as i32;
                (&mut *app_ptr).on_mouse_move(x, y);
            }
            LRESULT(0)
        }
        WM_MOUSELEAVE => { if !app_ptr.is_null() { (&mut *app_ptr).hover = None; let _ = InvalidateRect(Some(hwnd), None, false); } LRESULT(0) }
        WM_LBUTTONUP => {
            if !app_ptr.is_null() {
                let x = (lparam.0 & 0xFFFF) as i16 as i32;
                let y = ((lparam.0 >> 16) & 0xFFFF) as i16 as i32;
                (&mut *app_ptr).on_click(x, y);
            }
            LRESULT(0)
        }
        WM_CLOSE => {
            if !app_ptr.is_null() {
                let busy = (&*app_ptr).rt.lock().unwrap().busy;
                if busy {
                    (&*app_ptr).msg("正在复制文件，请等待完成。", "操作进行中", MB_ICONINFORMATION);
                    return LRESULT(0);
                }
            }
            let _ = DestroyWindow(hwnd);
            LRESULT(0)
        }
        WM_DESTROY => { PostQuitMessage(0); LRESULT(0) }
        WM_GETMINMAXINFO => {
            let mm = &mut *(lparam.0 as *mut MINMAXINFO);
            let scale = if app_ptr.is_null() { 1.0 } else { (&*app_ptr).scale };
            mm.ptMinTrackSize.x = (900.0 * scale) as i32;
            mm.ptMinTrackSize.y = (640.0 * scale) as i32;
            LRESULT(0)
        }
        WM_DPICHANGED => {
            if !app_ptr.is_null() {
                let dpi = (wparam.0 & 0xFFFF) as u32;
                let app = &mut *app_ptr;
                app.scale = dpi as f32 / 96.0;
                app.fonts = Fonts::new(app.scale);
                let r = &*(lparam.0 as *const RECT);
                let _ = SetWindowPos(hwnd, None, r.left, r.top, r.right - r.left, r.bottom - r.top, SWP_NOZORDER);
                let _ = InvalidateRect(Some(hwnd), None, false);
            }
            LRESULT(0)
        }
        _ => DefWindowProcW(hwnd, msg, wparam, lparam),
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--selftest" || a == "--toggle") {
        let game = core::detect_game_path();
        let payload = core::payload_path();
        let toggle = args.iter().any(|a| a == "--toggle");
        let mut out = String::new();
        let st = core::status(&game, &payload);
        out += &format!("status: game={} data={} backup={} patched={} version={} data_md5={:?} payload_md5={:?}\n",
            st.game_exists, st.data_exists, st.backup_exists, st.patched, st.version, st.data_md5, st.payload_md5);
        if toggle {
            let cancel = std::sync::atomic::AtomicBool::new(false);
            let u = core::uninstall(&game, &cancel, |_, _| {});
            out += &format!("uninstall: {:?}\n", u.map(|v| v.message));
            let i = core::install(&game, &payload, &cancel, |_, _| {});
            out += &format!("install: {:?}\n", i.map(|v| v.message));
        }
        let v = core::verify(&game, &payload);
        out += &format!("verify: match={} data={:?} payload={:?}\n", v.match_ok, v.data_md5, v.payload_md5);
        std::fs::write("selftest.txt", out).ok();
        return;
    }
    unsafe {
        let _ = SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        let _ = CoInitializeEx(None, COINIT_APARTMENTTHREADED);
    }
    let hinstance = unsafe { GetModuleHandleW(None).expect("GetModuleHandleW") };
    let hinst = HINSTANCE(hinstance.0);
    let class_name = w!("FsInstallerWindow");
    let wc = WNDCLASSW {
        style: WNDCLASS_STYLES(0),
        lpfnWndProc: Some(wndproc),
        cbClsExtra: 0,
        cbWndExtra: 0,
        hInstance: hinst,
        hIcon: Default::default(),
        hCursor: unsafe { LoadCursorW(None, IDC_ARROW).unwrap_or_default() },
        hbrBackground: HBRUSH(std::ptr::null_mut()),
        lpszMenuName: PCWSTR::null(),
        lpszClassName: class_name,
    };
    unsafe { RegisterClassW(&wc) };

    let hwnd = unsafe {
        CreateWindowExW(
            WINDOW_EX_STYLE(0),
            class_name,
            w!("Fallout Shelter 汉化安装程序"),
            WINDOW_STYLE(0x00CF0000),
            0, 0, WIN_W, WIN_H,
            None, None, Some(hinst), None,
        )
    }.expect("CreateWindowExW");

    unsafe {
        let dark: BOOL = TRUE;
        let _ = DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            &dark as *const _ as *const c_void, 4);
        let cap: u32 = theme::PANEL_ALT;
        let txt: u32 = theme::TEXT;
        let _ = DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR,
            &cap as *const _ as *const c_void, 4);
        let _ = DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR,
            &txt as *const _ as *const c_void, 4);

        let scale = GetDpiForWindow(hwnd) as f32 / 96.0;
        let _ = SetWindowPos(hwnd, None, 0, 0,
            (WIN_W as f32 * scale) as i32, (WIN_H as f32 * scale) as i32,
            SWP_NOZORDER);
    }

    let app = Box::new(App::new(hwnd));
    let app_ptr = Box::into_raw(app);
    unsafe { SetWindowLongPtrW(hwnd, GWLP_USERDATA, app_ptr as isize); }

    unsafe {
        let _ = ShowWindow(hwnd, SW_SHOW);
        let _ = UpdateWindow(hwnd);
        let mut msg = MSG::default();
        while GetMessageW(&mut msg, None, 0, 0).as_bool() {
            let _ = TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        let _ = KillTimer(Some(hwnd), 1);
        let _ = CoUninitialize();
    }
}
