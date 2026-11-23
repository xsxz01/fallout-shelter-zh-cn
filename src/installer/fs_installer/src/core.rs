use md5::{Digest, Md5};
use std::ffi::OsStr;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::os::windows::ffi::OsStrExt;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use windows::core::PCWSTR;
use windows::Win32::Foundation::{CloseHandle, HANDLE};
use windows::Win32::Storage::FileSystem::{
    GetDiskFreeSpaceExW, MoveFileExW, MOVEFILE_REPLACE_EXISTING, MOVEFILE_WRITE_THROUGH,
};
use windows::Win32::System::Diagnostics::ToolHelp::{
    CreateToolhelp32Snapshot, Process32FirstW, Process32NextW, PROCESSENTRY32W,
    TH32CS_SNAPPROCESS,
};
use windows::Win32::UI::Shell::ShellExecuteW;
use windows::Win32::UI::WindowsAndMessaging::SW_SHOWNORMAL;

#[derive(Clone, Default)]
pub struct Status {
    pub game_exists: bool,
    pub data_exists: bool,
    pub data_size: u64,
    pub data_md5: Option<String>,
    pub backup_exists: bool,
    pub backup_size: u64,
    pub backup_md5: Option<String>,
    pub payload_exists: bool,
    pub payload_size: u64,
    pub payload_md5: Option<String>,
    pub patched: bool,
    pub free_space: u64,
    pub version: String,
}

#[derive(Clone, Default)]
pub struct OperationResult {
    pub ok: bool,
    pub message: String,
    pub error: Option<String>,
    pub backup_created: bool,
    pub match_ok: bool,
    pub data_md5: Option<String>,
    pub payload_md5: Option<String>,
}

fn wide(s: &OsStr) -> Vec<u16> {
    s.encode_wide().chain(std::iter::once(0)).collect()
}

pub fn md5_file(path: &Path) -> Option<String> {
    let mut f = File::open(path).ok()?;
    let mut h = Md5::new();
    let mut buf = vec![0u8; 1024 * 1024];
    loop {
        let n = f.read(&mut buf).ok()?;
        if n == 0 { break; }
        h.update(&buf[..n]);
    }
    Some(format!("{:x}", h.finalize()))
}

pub fn free_space(path: &Path) -> u64 {
    let w = wide(path.as_os_str());
    let mut free = 0u64;
    if unsafe { GetDiskFreeSpaceExW(PCWSTR(w.as_ptr()), Some(&mut free), None, None) }.is_ok() { free } else { 0 }
}

pub fn read_version(game: &Path) -> String {
    for rel in ["2.7.0", "FalloutShelter_Data/app.info"] {
        let p = game.join(rel);
        if let Ok(s) = fs::read_to_string(p) {
            for line in s.lines() {
                if let Some(v) = line.strip_prefix("PlayerSettings.bundleVersion = ") {
                    return v.trim().to_string();
                }
            }
        }
    }
    "2.7.0".into()
}

pub fn status(game: &Path, payload: &Path) -> Status {
    let data = game.join("FalloutShelter_Data").join("data.unity3d");
    let bak = game.join("FalloutShelter_Data").join("data.unity3d.en.bak");
    let data_md5 = md5_file(&data);
    let bak_md5 = md5_file(&bak);
    let payload_md5 = md5_file(payload);
    let patched = matches!((&data_md5, &payload_md5), (Some(a), Some(b)) if a == b);
    Status {
        game_exists: game.join("FalloutShelter.exe").exists(),
        data_exists: data.exists(),
        data_size: fs::metadata(&data).map(|m| m.len()).unwrap_or(0),
        data_md5,
        backup_exists: bak.exists(),
        backup_size: fs::metadata(&bak).map(|m| m.len()).unwrap_or(0),
        backup_md5: bak_md5,
        payload_exists: payload.exists(),
        payload_size: fs::metadata(payload).map(|m| m.len()).unwrap_or(0),
        payload_md5,
        patched,
        free_space: free_space(game),
        version: read_version(game),
    }
}

fn copy_with_progress<F: Fn(u64, u64)>(src: &Path, dst: &Path, cb: &F) -> std::io::Result<()> {
    let total = fs::metadata(src)?.len();
    let mut input = File::open(src)?;
    let mut output = File::create(dst)?;
    let mut buf = vec![0u8; 8 * 1024 * 1024];
    let mut done = 0u64;
    cb(0, total);
    loop {
        let n = input.read(&mut buf)?;
        if n == 0 { break; }
        output.write_all(&buf[..n])?;
        done += n as u64;
        cb(done, total);
    }
    output.flush()?;
    output.sync_all()?;
    Ok(())
}

fn replace_file(src: &Path, dst: &Path) -> std::io::Result<()> {
    let sw = wide(src.as_os_str());
    let dw = wide(dst.as_os_str());
    unsafe {
        MoveFileExW(
            PCWSTR(sw.as_ptr()),
            PCWSTR(dw.as_ptr()),
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH,
        )
    }
    .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.message()))
}

pub fn install<F: Fn(u64, u64)>(
    game: &Path,
    payload: &Path,
    cancel: &AtomicBool,
    cb: F,
) -> Result<OperationResult, String> {
    if !game.join("FalloutShelter.exe").exists() {
        return Err("未找到 FalloutShelter.exe，请选择正确的游戏目录。".into());
    }
    if !payload.exists() {
        return Err("未找到汉化包 data.unity3d。".into());
    }
    let data = game.join("FalloutShelter_Data").join("data.unity3d");
    let bak = game.join("FalloutShelter_Data").join("data.unity3d.en.bak");
    if !data.exists() {
        return Err("未找到游戏 data.unity3d。".into());
    }
    let payload_size = fs::metadata(payload).map(|m| m.len()).unwrap_or(0);
    let data_size = fs::metadata(&data).map(|m| m.len()).unwrap_or(0);
    let need = payload_size + if bak.exists() { 0 } else { data_size };
    if free_space(game) < need + 64 * 1024 * 1024 {
        return Err("磁盘剩余空间不足（需要约 1 GB）。".into());
    }
    let mut backup_created = false;
    if !bak.exists() {
        cb(0, data_size);
        copy_with_progress(&data, &bak, &cb).map_err(|e| format!("备份失败：{e}"))?;
        backup_created = true;
    }
    if cancel.load(Ordering::Relaxed) {
        return Err("已取消".into());
    }
    let tmp = game.join("FalloutShelter_Data").join("data.unity3d.zhnew");
    let _ = fs::remove_file(&tmp);
    let r = copy_with_progress(payload, &tmp, &cb);
    if let Err(e) = r {
        let _ = fs::remove_file(&tmp);
        return Err(format!("复制汉化文件失败：{e}"));
    }
    replace_file(&tmp, &data).map_err(|e| {
        let _ = fs::remove_file(&tmp);
        format!("替换 data.unity3d 失败：{e}")
    })?;
    Ok(OperationResult {
        ok: true,
        message: "汉化安装完成".into(),
        backup_created,
        ..Default::default()
    })
}

pub fn uninstall<F: Fn(u64, u64)>(
    game: &Path,
    cancel: &AtomicBool,
    cb: F,
) -> Result<OperationResult, String> {
    let data = game.join("FalloutShelter_Data").join("data.unity3d");
    let bak = game.join("FalloutShelter_Data").join("data.unity3d.en.bak");
    if !bak.exists() {
        return Err("未找到原版备份 data.unity3d.en.bak，无法卸载。".into());
    }
    let tmp = game.join("FalloutShelter_Data").join("data.unity3d.ennew");
    let _ = fs::remove_file(&tmp);
    let size = fs::metadata(&bak).map(|m| m.len()).unwrap_or(0);
    cb(0, size);
    copy_with_progress(&bak, &tmp, &cb).map_err(|e| format!("读取备份失败：{e}"))?;
    if cancel.load(Ordering::Relaxed) {
        let _ = fs::remove_file(&tmp);
        return Err("已取消".into());
    }
    replace_file(&tmp, &data).map_err(|e| format!("还原失败：{e}"))?;
    Ok(OperationResult { ok: true, message: "已还原英文原版".into(), ..Default::default() })
}

pub fn verify(game: &Path, payload: &Path) -> OperationResult {
    let data = game.join("FalloutShelter_Data").join("data.unity3d");
    let dm = md5_file(&data);
    let pm = md5_file(payload);
    let ok = matches!((&dm, &pm), (Some(a), Some(b)) if a == b);
    OperationResult {
        ok: true,
        match_ok: ok,
        data_md5: dm,
        payload_md5: pm,
        message: if ok { "校验通过：data.unity3d 与汉化包一致".into() }
                 else { "校验不一致".into() },
        ..Default::default()
    }
}

pub fn is_game_running() -> bool {
    unsafe {
        let snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        let Ok(snap) = snap else { return false; };
        let mut pe = PROCESSENTRY32W {
            dwSize: std::mem::size_of::<PROCESSENTRY32W>() as u32,
            ..Default::default()
        };
        let mut found = false;
        if Process32FirstW(snap, &mut pe).is_ok() {
            loop {
                let name = String::from_utf16_lossy(
                    &pe.szExeFile[..pe.szExeFile.iter().position(|&c| c == 0).unwrap_or(0)],
                );
                if name.eq_ignore_ascii_case("FalloutShelter.exe") {
                    found = true;
                    break;
                }
                if Process32NextW(snap, &mut pe).is_err() {
                    break;
                }
            }
        }
        let _ = CloseHandle(HANDLE(snap.0));
        found
    }
}

pub fn open_folder(path: &Path) {
    let w = wide(path.as_os_str());
    unsafe {
        ShellExecuteW(
            None,
            windows::core::w!("open"),
            PCWSTR(w.as_ptr()),
            PCWSTR::null(),
            PCWSTR::null(),
            SW_SHOWNORMAL,
        );
    }
}

pub fn payload_path() -> PathBuf {
    let local = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.join("payload").join("data.unity3d")));
    if let Some(ref p) = local {
        if p.exists() { return p.clone(); }
    }
    let dev = PathBuf::from(r"D:\FS_localization_work\build\patch_data.unity3d");
    if dev.exists() { return dev; }
    local.unwrap_or(dev)
}

pub fn detect_game_path() -> PathBuf {
    let candidates = [
        r"D:\Program Files (x86)\Steam\steamapps\common\Fallout Shelter",
        r"C:\Program Files (x86)\Steam\steamapps\common\Fallout Shelter",
    ];
    for c in candidates {
        let p = PathBuf::from(c);
        if p.join("FalloutShelter.exe").exists() {
            return p;
        }
    }
    PathBuf::from(candidates[0])
}
