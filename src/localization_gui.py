#!/usr/bin/env python3
"""Fallout Shelter 2.7.0 zh-CN localization editor (Tkinter GUI)."""
import os, queue, shutil, subprocess, sys, threading, tkinter as tk
from tkinter import messagebox, ttk

import loc_core
from project_paths import GAME_DATA, PATCH_DATA, PATCH_DIR, SRC, VERSION_FILE
FONT = ("Microsoft YaHei UI", 10)
FONT_SMALL = ("Microsoft YaHei UI", 9)
FONT_MONO = ("Consolas", 10)


def version():
    try:
        return open(VERSION_FILE, encoding="utf-8").read().strip() or "1.0.0"
    except OSError:
        return "1.0.0"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("辐射：避难所 汉化编辑器")
        self.geometry("1500x900")
        self.minsize(1100, 700)
        self.option_add("*Font", FONT)
        self.rows, self.counts = loc_core.build_rows()
        self.overrides = loc_core.load_json(loc_core.OVERRIDES, {})
        self.by_iid = {}
        self.current = None
        self.out_q = queue.Queue()
        self.busy = False
        self.last_rc = None
        self._build_ui()
        self._refresh_tree()

    # ---------- UI ----------
    def _build_ui(self):
        top = ttk.Frame(self, padding=(8, 6))
        top.pack(fill="x")
        ttk.Label(top, text="搜索").pack(side="left")
        self.search_var = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.search_var, width=32)
        ent.pack(side="left", padx=(4, 10))
        ent.bind("<KeyRelease>", lambda e: self._refresh_tree())
        ttk.Label(top, text="来源").pack(side="left")
        self.filter_var = tk.StringVar(value="全部")
        cb = ttk.Combobox(top, textvariable=self.filter_var, width=16, state="readonly",
                          values=["全部", "人工UI覆盖", "机翻+术语处理", "术语表",
                                  "未翻译，保留英文", "原文为空", "非英文，保留"])
        cb.pack(side="left", padx=(4, 10))
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_tree())
        self.count_label = ttk.Label(top, text="")
        self.count_label.pack(side="left")
        ttk.Button(top, text="导出清单", command=self.export_list).pack(side="right", padx=3)
        ttk.Button(top, text="生成发布包", command=self.make_package).pack(side="right", padx=3)
        ttk.Button(top, text="构建补丁", command=self.build_patch).pack(side="right", padx=3)

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=4)

        left = ttk.Frame(paned)
        paned.add(left, weight=3)
        cols = ("no", "key", "en", "zh", "src")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width, anchor in [
            ("no", "序号", 56, "e"), ("key", "Term Key", 220, "w"),
            ("en", "英文原文", 300, "w"), ("zh", "中文译文", 300, "w"),
            ("src", "来源", 110, "w"),
        ]:
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, anchor=anchor, stretch=(c in ("en", "zh")))
        ysb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")
        self.tree.tag_configure("manual", background="#fff4d6")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        right = ttk.Frame(paned, padding=(10, 0, 0, 0))
        paned.add(right, weight=2)
        ttk.Label(right, text="Term Key", font=FONT_SMALL).pack(anchor="w")
        self.key_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.key_var, state="readonly").pack(fill="x", pady=(0, 8))
        ttk.Label(right, text="英文原文").pack(anchor="w")
        self.en_text = tk.Text(right, height=5, wrap="word", font=FONT_MONO)
        self.en_text.pack(fill="x", pady=(0, 8))
        ttk.Label(right, text="中文译文（保存后写入 overrides.json）").pack(anchor="w")
        self.zh_text = tk.Text(right, height=10, wrap="word", font=FONT)
        self.zh_text.pack(fill="both", expand=True, pady=(0, 6))
        self.meta_label = ttk.Label(right, text="", font=FONT_SMALL, foreground="#666")
        self.meta_label.pack(anchor="w", pady=(0, 6))
        btn = ttk.Frame(right)
        btn.pack(fill="x")
        ttk.Button(btn, text="保存修改 (Ctrl+S)", command=self.save_current).pack(side="left")
        ttk.Button(btn, text="恢复机翻", command=self.revert_current).pack(side="left", padx=6)
        ttk.Button(btn, text="下一条", command=lambda: self.step(1)).pack(side="right")
        ttk.Button(btn, text="上一条", command=lambda: self.step(-1)).pack(side="right", padx=6)
        ttk.Label(right, text="其他语言（只读）").pack(anchor="w", pady=(10, 2))
        self.other_text = tk.Text(right, height=4, wrap="word", font=FONT_MONO, state="disabled")
        self.other_text.pack(fill="x")

        status = ttk.Frame(self, padding=(8, 4))
        status.pack(fill="x")
        self.status_var = tk.StringVar(value=f"版本 v{version()}  |  已加载 {len(self.rows)} 条")
        ttk.Label(status, textvariable=self.status_var, font=FONT_SMALL).pack(side="left")

        self.bind("<Control-s>", lambda e: self.save_current())

    # ---------- data ----------
    def _visible(self):
        q = self.search_var.get().strip().lower()
        f = self.filter_var.get()
        out = []
        for r in self.rows:
            if f != "全部" and r["src"] != f:
                continue
            if q and q not in r["key"].lower() and q not in r["en"].lower() and q not in r["zh"].lower():
                continue
            out.append(r)
        return out

    def _refresh_tree(self):
        vis = self._visible()
        self.tree.delete(*self.tree.get_children())
        self.by_iid.clear()
        for r in vis:
            iid = str(r["no"])
            self.by_iid[iid] = r
            tags = ("manual",) if r["manual"] else ()
            self.tree.insert("", "end", iid=iid, tags=tags,
                             values=(r["no"], r["key"], r["en"].replace("\n", " "),
                                     r["zh"].replace("\n", " "), r["src"]))
        self.count_label.config(text=f"显示 {len(vis)} / {len(self.rows)}")
        if vis and self.current is None:
            self.tree.selection_set(str(vis[0]["no"]))
            self.tree.focus(str(vis[0]["no"]))

    def _row_by_key(self, key):
        for r in self.rows:
            if r["key"] == key:
                return r
        return None

    def _update_row(self, r):
        key = r["key"]
        en = r["en"]
        zh, src, manual = loc_core.effective(en, key, loc_core.load_json(loc_core.CACHE, {}),
                                             self.overrides)
        r.update(zh=zh, src=src, manual=manual)
        iid = str(r["no"])
        if iid in self.by_iid:
            self.tree.item(iid, values=(r["no"], key, en.replace("\n", " "),
                                        zh.replace("\n", " "), src),
                           tags=("manual",) if manual else ())

    def on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        r = self.by_iid.get(sel[0])
        if not r:
            return
        self.current = r
        self.key_var.set(r["key"])
        self.en_text.delete("1.0", "end")
        self.en_text.insert("1.0", r["en"])
        self.zh_text.delete("1.0", "end")
        self.zh_text.insert("1.0", r["zh"])
        self.meta_label.config(text=f"来源：{r['src']}    TermType：{r['term_type']}")
        self.other_text.config(state="normal")
        self.other_text.delete("1.0", "end")
        names = ["Spanish", "French", "Italian", "German", "Russian"]
        for n, v in zip(names, r["others"]):
            if v:
                self.other_text.insert("end", f"{n}: {v}\n")
        self.other_text.config(state="disabled")

    def save_current(self):
        if not self.current:
            return
        key = self.current["key"]
        text = self.zh_text.get("1.0", "end-1c").strip()
        old = loc_core.load_json(loc_core.CACHE, {}).get(self.current["en"], "")
        if text == old:
            self.overrides.pop(key, None)
        else:
            self.overrides[key] = text
        loc_core.save_json(loc_core.OVERRIDES, self.overrides)
        self._update_row(self.current)
        self.on_select()
        self.status_var.set(f"已保存 {key}  |  人工覆盖 {len(self.overrides)} 条")

    def revert_current(self):
        if not self.current:
            return
        key = self.current["key"]
        self.overrides.pop(key, None)
        loc_core.save_json(loc_core.OVERRIDES, self.overrides)
        self._update_row(self.current)
        self.on_select()
        self.status_var.set(f"已恢复机翻：{key}")

    def step(self, delta):
        if not self.current:
            return
        children = self.tree.get_children()
        if not children:
            return
        iid = str(self.current["no"])
        if iid not in children:
            return
        i = children.index(iid) + delta
        if 0 <= i < len(children):
            self.tree.selection_set(children[i])
            self.tree.focus(children[i])
            self.tree.see(children[i])

    # ---------- actions ----------
    def export_list(self):
        try:
            n, counts = loc_core.export_csv()
            shutil.copyfile(loc_core.LIST_CSV, os.path.join(PATCH_DIR, "翻译清单.csv"))
            self.status_var.set(f"已导出 {n} 条：{loc_core.LIST_CSV}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _run(self, args, title):
        if self.busy:
            messagebox.showinfo("请稍候", "已有任务在执行")
            return
        self.busy = True
        self.last_rc = None
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("900x480")
        txt = tk.Text(win, font=FONT_MONO, bg="#111", fg="#ddd")
        txt.pack(fill="both", expand=True)
        txt.insert("end", f"$ {' '.join(args)}\n\n")
        txt.see("end")

        def worker():
            try:
                p = subprocess.Popen(args, cwd=SRC, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True,
                                     encoding="utf-8", errors="replace")
                for line in p.stdout:
                    self.out_q.put(("log", txt, line))
                p.wait()
                self.out_q.put(("done", txt, p.returncode))
            except Exception as e:
                self.out_q.put(("log", txt, f"\nERROR: {e}\n"))
                self.out_q.put(("done", txt, 1))

        threading.Thread(target=worker, daemon=True).start()

        def poll():
            try:
                while True:
                    kind, widget, val = self.out_q.get_nowait()
                    if kind == "log":
                        widget.insert("end", val)
                        widget.see("end")
                    elif kind == "done":
                        self.busy = False
                        self.last_rc = val
                        widget.insert("end", f"\n[退出码 {val}]\n")
                        widget.see("end")
                        self.status_var.set(f"{title} 完成，退出码 {val}")
                        return
            except queue.Empty:
                pass
            self.after(120, poll)

        poll()

    def build_patch(self):
        if not messagebox.askyesno("构建补丁", "将重新构建 data.unity3d 并安装到游戏目录，继续？"):
            return
        self._run([sys.executable, str(SRC / "build_patch.py")], "构建补丁")
        self.after(500, self._install_after_build)

    def _install_after_build(self):
        # Poll the build output; install only after patch_data.unity3d is newer.
        if self.busy:
            self.after(500, self._install_after_build)
            return
        if self.last_rc != 0:
            self.status_var.set("构建失败，未安装")
            return
        try:
            shutil.copyfile(PATCH_DATA, GAME_DATA)
            os.makedirs(PATCH_DIR, exist_ok=True)
            shutil.copyfile(PATCH_DATA, os.path.join(PATCH_DIR, "data.unity3d"))
            loc_core.export_csv()
            shutil.copyfile(loc_core.LIST_CSV, os.path.join(PATCH_DIR, "翻译清单.csv"))
            self.status_var.set("补丁已构建并安装到游戏，清单已更新")
        except Exception as e:
            messagebox.showerror("安装失败", str(e))

    def make_package(self):
        if self.busy:
            messagebox.showinfo("请稍候", "已有任务在执行")
            return
        win = tk.Toplevel(self)
        win.title("生成发布包 / 发布到 GitHub")
        win.geometry("520x330")
        ttk.Label(win, text="版本号").pack(anchor="w", padx=12, pady=(12, 0))
        ver_var = tk.StringVar(value=version())
        ttk.Entry(win, textvariable=ver_var, width=20).pack(anchor="w", padx=12)
        ttk.Label(win, text="发布说明").pack(anchor="w", padx=12, pady=(10, 0))
        notes = tk.Text(win, height=7)
        notes.pack(fill="both", expand=True, padx=12)
        notes.insert("1.0", "当前汉化包：\n- 更新翻译\n- 修复字体显示")
        publish_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(win, text="生成后上传到 GitHub Release", variable=publish_var).pack(anchor="w", padx=12, pady=6)

        def go():
            v = ver_var.get().strip()
            if not v:
                return
            win.destroy()
            args = [sys.executable, str(SRC / "package_release.py"), "--version", v]
            text = notes.get("1.0", "end-1c").strip()
            if text:
                args += ["--notes", text]
            if not publish_var.get():
                args.append("--no-release")
            self._run(args, f"生成 v{v}")

        ttk.Button(win, text="开始", command=go).pack(pady=8)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        rows, counts = loc_core.build_rows()
        print("rows", len(rows), counts)
        sys.exit(0)
    App().mainloop()
