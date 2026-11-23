pub const fn rgb(r: u8, g: u8, b: u8) -> u32 {
    (r as u32) | ((g as u32) << 8) | ((b as u32) << 16)
}

pub const BG: u32 = rgb(14, 18, 14);
pub const SCAN: u32 = rgb(17, 23, 17);
pub const PANEL: u32 = rgb(23, 29, 23);
pub const PANEL_ALT: u32 = rgb(31, 38, 31);
pub const LINE: u32 = rgb(58, 74, 58);
pub const TEXT: u32 = rgb(214, 224, 214);
pub const MUTED: u32 = rgb(140, 153, 140);
pub const ACCENT: u32 = rgb(143, 224, 138);
pub const ACCENT_BRIGHT: u32 = rgb(200, 255, 192);
pub const WARNING: u32 = rgb(255, 204, 102);
pub const DANGER: u32 = rgb(255, 107, 94);
pub const BLACK: u32 = rgb(0, 0, 0);

pub const HEAD_FONT: &str = "Bahnschrift SemiCondensed";
pub const BODY_FONT: &str = "Microsoft YaHei UI";
pub const MONO_FONT: &str = "Consolas";
