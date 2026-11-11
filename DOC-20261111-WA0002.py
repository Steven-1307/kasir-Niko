"""
Aplikasi Kasir Desktop sederhana
Teknologi : Python 3 + Tkinter (bawaan Python) + SQLite (bawaan Python)
Jalankan  : python kasir.py
Data      : tersimpan otomatis di file kasir.db (satu folder dengan kasir.py)
"""
import os
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

NAMA_TOKO = "TOKO SAYA"
ALAMAT_TOKO = "Jl. Contoh No. 1"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kasir.db")


def rp(n):
    return "Rp " + f"{int(n):,}".replace(",", ".")


def angka(teks):
    digit = "".join(c for c in str(teks) if c.isdigit())
    return int(digit) if digit else 0


# ----------------------------------------------------------------- database
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
db.executescript(
    """
CREATE TABLE IF NOT EXISTS produk(
    kode  TEXT PRIMARY KEY,
    nama  TEXT NOT NULL,
    harga INTEGER NOT NULL,
    stok  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS penjualan(
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    waktu  TEXT NOT NULL,
    total  INTEGER NOT NULL,
    bayar  INTEGER NOT NULL,
    kembali INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS item_penjualan(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    penjualan_id INTEGER NOT NULL REFERENCES penjualan(id),
    kode         TEXT NOT NULL,
    nama         TEXT NOT NULL,
    harga        INTEGER NOT NULL,
    qty          INTEGER NOT NULL
);
"""
)
if db.execute("SELECT COUNT(*) FROM produk").fetchone()[0] == 0:
    db.executemany(
        "INSERT INTO produk VALUES (?,?,?,?)",
        [
            ("P001", "Air Mineral 600ml", 4000, 50),
            ("P002", "Mie Instan", 3500, 80),
            ("P003", "Kopi Sachet", 2000, 100),
            ("P004", "Roti Tawar", 15000, 20),
            ("P005", "Telur 1 kg", 28000, 15),
        ],
    )
    db.commit()


# ---------------------------------------------------------------- aplikasi
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Kasir - {NAMA_TOKO}")
        self.geometry("1150x680")
        self.minsize(980, 600)
        self.cart = {}  # kode -> {kode, nama, harga, qty}

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_kasir = ttk.Frame(nb, padding=8)
        self.tab_produk = ttk.Frame(nb, padding=8)
        self.tab_riwayat = ttk.Frame(nb, padding=8)
        nb.add(self.tab_kasir, text="  Kasir  ")
        nb.add(self.tab_produk, text="  Produk  ")
        nb.add(self.tab_riwayat, text="  Riwayat  ")
        nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())

        self.build_kasir()
        self.build_produk()
        self.build_riwayat()
        self.refresh_all()
        self.bind("<F12>", lambda e: self.bayar())
        self.ent_cari.focus_set()

    # ------------------------------------------------------------- tab kasir
    def build_kasir(self):
        f = self.tab_kasir
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(0, weight=1)

        # kiri: katalog
        kiri = ttk.LabelFrame(f, text="Katalog Produk", padding=8)
        kiri.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        kiri.rowconfigure(1, weight=1)
        kiri.columnconfigure(0, weight=1)

        bar = ttk.Frame(kiri)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        bar.columnconfigure(1, weight=1)
        ttk.Label(bar, text="Kode / Nama:").grid(row=0, column=0)
        self.var_cari = tk.StringVar()
        self.var_cari.trace_add("write", lambda *a: self.refresh_katalog())
        self.ent_cari = ttk.Entry(bar, textvariable=self.var_cari, font=("Segoe UI", 12))
        self.ent_cari.grid(row=0, column=1, sticky="ew", padx=6)
        self.ent_cari.bind("<Return>", self.enter_cari)
        ttk.Label(bar, text="Qty:").grid(row=0, column=2)
        self.var_qty = tk.StringVar(value="1")
        ttk.Spinbox(bar, from_=1, to=999, width=5, textvariable=self.var_qty).grid(row=0, column=3, padx=4)

        self.tv_katalog = self.buat_tree(
            kiri,
            [("kode", "Kode", 80), ("nama", "Nama", 200), ("harga", "Harga", 90), ("stok", "Stok", 60)],
        )
        self.tv_katalog.master.grid(row=1, column=0, sticky="nsew")
        self.tv_katalog.bind("<Double-1>", lambda e: self.tambah_terpilih())
        self.tv_katalog.bind("<Return>", lambda e: self.tambah_terpilih())
        ttk.Button(kiri, text="Tambah ke Keranjang", command=self.tambah_terpilih).grid(
            row=2, column=0, sticky="ew", pady=(6, 0)
        )

        # kanan: keranjang
        kanan = ttk.LabelFrame(f, text="Keranjang", padding=8)
        kanan.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        kanan.rowconfigure(0, weight=1)
        kanan.columnconfigure(0, weight=1)

        self.tv_cart = self.buat_tree(
            kanan,
            [
                ("kode", "Kode", 70),
                ("nama", "Nama", 170),
                ("harga", "Harga", 80),
                ("qty", "Qty", 45),
                ("sub", "Subtotal", 95),
            ],
        )
        self.tv_cart.master.grid(row=0, column=0, sticky="nsew")

        btn = ttk.Frame(kanan)
        btn.grid(row=1, column=0, sticky="ew", pady=6)
        ttk.Button(btn, text="+ 1", width=6, command=lambda: self.ubah_qty(1)).pack(side="left")
        ttk.Button(btn, text="- 1", width=6, command=lambda: self.ubah_qty(-1)).pack(side="left", padx=4)
        ttk.Button(btn, text="Hapus Item", command=self.hapus_item).pack(side="left")
        ttk.Button(btn, text="Kosongkan", command=self.kosongkan).pack(side="left", padx=4)

        self.lbl_total = tk.Label(kanan, text="TOTAL: Rp 0", font=("Segoe UI", 22, "bold"), anchor="e")
        self.lbl_total.grid(row=2, column=0, sticky="ew")

        pay = ttk.Frame(kanan)
        pay.grid(row=3, column=0, sticky="ew", pady=6)
        pay.columnconfigure(1, weight=1)
        ttk.Label(pay, text="Uang Bayar:").grid(row=0, column=0, sticky="w")
        self.var_bayar = tk.StringVar()
        self.var_bayar.trace_add("write", lambda *a: self.hitung_kembali())
        ent = ttk.Entry(pay, textvariable=self.var_bayar, font=("Segoe UI", 14))
        ent.grid(row=0, column=1, sticky="ew", padx=6)
        ent.bind("<Return>", lambda e: self.bayar())
        ttk.Button(pay, text="Uang Pas", command=self.uang_pas).grid(row=0, column=2)
        self.lbl_kembali = tk.Label(pay, text="Kembalian: Rp 0", font=("Segoe UI", 13), anchor="w")
        self.lbl_kembali.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        tk.Button(
            kanan,
            text="BAYAR  (F12)",
            font=("Segoe UI", 14, "bold"),
            bg="#2e7d32",
            fg="white",
            activebackground="#1b5e20",
            activeforeground="white",
            command=self.bayar,
        ).grid(row=4, column=0, sticky="ew", ipady=6)

    def buat_tree(self, parent, kolom):
        wrap = ttk.Frame(parent)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        tv = ttk.Treeview(wrap, columns=[k[0] for k in kolom], show="headings", selectmode="browse")
        for key, judul, lebar in kolom:
            tv.heading(key, text=judul)
            tv.column(key, width=lebar, anchor="e" if key in ("harga", "stok", "qty", "sub", "total", "bayar", "kembali") else "w")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        return tv

    def refresh_katalog(self):
        q = f"%{self.var_cari.get().strip()}%"
        rows = db.execute(
            "SELECT * FROM produk WHERE kode LIKE ? OR nama LIKE ? ORDER BY nama LIMIT 300", (q, q)
        ).fetchall()
        self.tv_katalog.delete(*self.tv_katalog.get_children())
        for r in rows:
            self.tv_katalog.insert("", "end", iid=r["kode"], values=(r["kode"], r["nama"], rp(r["harga"]), r["stok"]))

    def enter_cari(self, _e=None):
        teks = self.var_cari.get().strip()
        if not teks:
            return
        r = db.execute("SELECT kode FROM produk WHERE kode = ? COLLATE NOCASE", (teks,)).fetchone()
        if r:
            self.tambah(r["kode"])
        else:
            anak = self.tv_katalog.get_children()
            if len(anak) == 1:
                self.tambah(anak[0])
            elif not anak:
                messagebox.showinfo("Tidak ditemukan", "Produk tidak ditemukan.")
            else:
                self.tv_katalog.focus_set()
                self.tv_katalog.selection_set(anak[0])
                self.tv_katalog.focus(anak[0])
                return
        self.var_cari.set("")
        self.ent_cari.focus_set()

    def tambah_terpilih(self):
        sel = self.tv_katalog.selection()
        if sel:
            self.tambah(sel[0])

    def tambah(self, kode):
        p = db.execute("SELECT * FROM produk WHERE kode = ?", (kode,)).fetchone()
        if not p:
            return
        qty = max(1, angka(self.var_qty.get()))
        sudah = self.cart.get(kode, {}).get("qty", 0)
        if sudah + qty > p["stok"]:
            messagebox.showwarning("Stok kurang", f"Stok {p['nama']} hanya {p['stok']}.")
            return
        if kode in self.cart:
            self.cart[kode]["qty"] += qty
        else:
            self.cart[kode] = {"kode": kode, "nama": p["nama"], "harga": p["harga"], "qty": qty}
        self.var_qty.set("1")
        self.refresh_cart()

    def item_terpilih(self):
        sel = self.tv_cart.selection()
        return sel[0] if sel else None

    def ubah_qty(self, delta):
        kode = self.item_terpilih()
        if not kode:
            return
        item = self.cart[kode]
        baru = item["qty"] + delta
        stok = db.execute("SELECT stok FROM produk WHERE kode = ?", (kode,)).fetchone()["stok"]
        if baru > stok:
            messagebox.showwarning("Stok kurang", f"Stok {item['nama']} hanya {stok}.")
            return
        if baru <= 0:
            del self.cart[kode]
        else:
            item["qty"] = baru
        self.refresh_cart(pilih=kode)

    def hapus_item(self):
        kode = self.item_terpilih()
        if kode:
            del self.cart[kode]
            self.refresh_cart()

    def kosongkan(self):
        if self.cart and messagebox.askyesno("Konfirmasi", "Kosongkan keranjang?"):
            self.cart.clear()
            self.var_bayar.set("")
            self.refresh_cart()

    def total(self):
        return sum(i["harga"] * i["qty"] for i in self.cart.values())

    def refresh_cart(self, pilih=None):
        self.tv_cart.delete(*self.tv_cart.get_children())
        for k, i in self.cart.items():
            self.tv_cart.insert(
                "", "end", iid=k, values=(k, i["nama"], rp(i["harga"]), i["qty"], rp(i["harga"] * i["qty"]))
            )
        if pilih and pilih in self.cart:
            self.tv_cart.selection_set(pilih)
        self.lbl_total.config(text=f"TOTAL: {rp(self.total())}")
        self.hitung_kembali()

    def hitung_kembali(self):
        sisa = angka(self.var_bayar.get()) - self.total()
        if sisa >= 0:
            self.lbl_kembali.config(text=f"Kembalian: {rp(sisa)}", fg="black")
        else:
            self.lbl_kembali.config(text=f"Kurang: {rp(-sisa)}", fg="#c62828")

    def uang_pas(self):
        self.var_bayar.set(str(self.total()))

    def bayar(self):
        if not self.cart:
            messagebox.showinfo("Keranjang kosong", "Belum ada barang di keranjang.")
            return
        total = self.total()
        bayar = angka(self.var_bayar.get())
        if bayar < total:
            messagebox.showwarning("Uang kurang", "Uang bayar kurang dari total.")
            return
        try:
            with db:
                # cek stok terakhir sebelum simpan
                for i in self.cart.values():
                    stok = db.execute("SELECT stok FROM produk WHERE kode = ?", (i["kode"],)).fetchone()
                    if not stok or stok["stok"] < i["qty"]:
                        raise ValueError(f"Stok {i['nama']} tidak mencukupi.")
                cur = db.execute(
                    "INSERT INTO penjualan(waktu,total,bayar,kembali) VALUES (?,?,?,?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total, bayar, bayar - total),
                )
                sid = cur.lastrowid
                for i in self.cart.values():
                    db.execute(
                        "INSERT INTO item_penjualan(penjualan_id,kode,nama,harga,qty) VALUES (?,?,?,?,?)",
                        (sid, i["kode"], i["nama"], i["harga"], i["qty"]),
                    )
                    db.execute("UPDATE produk SET stok = stok - ? WHERE kode = ?", (i["qty"], i["kode"]))
        except Exception as e:
            messagebox.showerror("Gagal", str(e))
            return
        self.cart.clear()
        self.var_bayar.set("")
        self.refresh_all()
        self.tampil_struk(sid)
        self.ent_cari.focus_set()

    # ------------------------------------------------------------ tab produk
    def build_produk(self):
        f = self.tab_produk
        f.columnconfigure(1, weight=1)
        f.rowconfigure(0, weight=1)

        form = ttk.LabelFrame(f, text="Data Produk", padding=10)
        form.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        self.pv = {k: tk.StringVar() for k in ("kode", "nama", "harga", "stok")}
        for r, (k, label) in enumerate([("kode", "Kode"), ("nama", "Nama"), ("harga", "Harga"), ("stok", "Stok")]):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=4)
            ttk.Entry(form, textvariable=self.pv[k], width=26).grid(row=r, column=1, pady=4, padx=(8, 0))
        ttk.Button(form, text="Simpan", command=self.simpan_produk).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 2))
        ttk.Button(form, text="Baru / Bersihkan", command=self.bersih_produk).grid(row=5, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(form, text="Hapus", command=self.hapus_produk).grid(row=6, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Label(
            form,
            text="Kode sama = update data.\nPilih baris di tabel untuk mengedit.",
            foreground="#555",
        ).grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="w")

        self.tv_produk = self.buat_tree(
            f, [("kode", "Kode", 90), ("nama", "Nama", 260), ("harga", "Harga", 110), ("stok", "Stok", 70)]
        )
        self.tv_produk.master.grid(row=0, column=1, sticky="nsew")
        self.tv_produk.bind("<<TreeviewSelect>>", self.pilih_produk)

    def refresh_produk(self):
        self.tv_produk.delete(*self.tv_produk.get_children())
        for r in db.execute("SELECT * FROM produk ORDER BY nama"):
            self.tv_produk.insert("", "end", iid=r["kode"], values=(r["kode"], r["nama"], rp(r["harga"]), r["stok"]))

    def pilih_produk(self, _e=None):
        sel = self.tv_produk.selection()
        if not sel:
            return
        r = db.execute("SELECT * FROM produk WHERE kode = ?", (sel[0],)).fetchone()
        if r:
            self.pv["kode"].set(r["kode"])
            self.pv["nama"].set(r["nama"])
            self.pv["harga"].set(str(r["harga"]))
            self.pv["stok"].set(str(r["stok"]))

    def bersih_produk(self):
        for v in self.pv.values():
            v.set("")
        self.tv_produk.selection_remove(self.tv_produk.selection())

    def simpan_produk(self):
        kode = self.pv["kode"].get().strip().upper()
        nama = self.pv["nama"].get().strip()
        harga = angka(self.pv["harga"].get())
        stok = angka(self.pv["stok"].get())
        if not kode or not nama or harga <= 0:
            messagebox.showwarning("Data belum lengkap", "Kode, nama, dan harga (> 0) wajib diisi.")
            return
        with db:
            db.execute(
                "INSERT INTO produk(kode,nama,harga,stok) VALUES (?,?,?,?) "
                "ON CONFLICT(kode) DO UPDATE SET nama=excluded.nama, harga=excluded.harga, stok=excluded.stok",
                (kode, nama, harga, stok),
            )
        self.bersih_produk()
        self.refresh_all()

    def hapus_produk(self):
        kode = self.pv["kode"].get().strip().upper()
        if not kode:
            return
        if messagebox.askyesno("Konfirmasi", f"Hapus produk {kode}? (riwayat penjualan tetap aman)"):
            with db:
                db.execute("DELETE FROM produk WHERE kode = ?", (kode,))
            self.cart.pop(kode, None)
            self.bersih_produk()
            self.refresh_all()
            self.refresh_cart()

    # ----------------------------------------------------------- tab riwayat
    def build_riwayat(self):
        f = self.tab_riwayat
        f.rowconfigure(1, weight=1)
        f.columnconfigure(0, weight=1)
        self.lbl_hari_ini = tk.Label(f, text="", font=("Segoe UI", 13, "bold"), anchor="w")
        self.lbl_hari_ini.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.tv_riwayat = self.buat_tree(
            f,
            [
                ("id", "No.", 60),
                ("waktu", "Waktu", 160),
                ("total", "Total", 110),
                ("bayar", "Bayar", 110),
                ("kembali", "Kembali", 110),
            ],
        )
        self.tv_riwayat.master.grid(row=1, column=0, sticky="nsew")
        self.tv_riwayat.bind("<Double-1>", self.buka_struk)
        ttk.Label(f, text="Klik dua kali untuk melihat struk.", foreground="#555").grid(row=2, column=0, sticky="w", pady=(6, 0))

    def refresh_riwayat(self):
        self.tv_riwayat.delete(*self.tv_riwayat.get_children())
        for r in db.execute("SELECT * FROM penjualan ORDER BY id DESC LIMIT 300"):
            self.tv_riwayat.insert(
                "", "end", iid=str(r["id"]), values=(r["id"], r["waktu"], rp(r["total"]), rp(r["bayar"]), rp(r["kembali"]))
            )
        hari = datetime.now().strftime("%Y-%m-%d")
        r = db.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(total),0) t FROM penjualan WHERE waktu LIKE ?", (hari + "%",)
        ).fetchone()
        self.lbl_hari_ini.config(text=f"Hari ini: {r['n']} transaksi  |  Omzet {rp(r['t'])}")

    def buka_struk(self, _e=None):
        sel = self.tv_riwayat.selection()
        if sel:
            self.tampil_struk(int(sel[0]))

    # ----------------------------------------------------------------- struk
    def teks_struk(self, sid):
        s = db.execute("SELECT * FROM penjualan WHERE id = ?", (sid,)).fetchone()
        items = db.execute("SELECT * FROM item_penjualan WHERE penjualan_id = ?", (sid,)).fetchall()
        w = 38
        out = [NAMA_TOKO.center(w), ALAMAT_TOKO.center(w), "=" * w]
        out.append(f"No : {sid:06d}")
        out.append(f"Tgl: {s['waktu']}")
        out.append("-" * w)
        for i in items:
            out.append(i["nama"][:w])
            kiri = f"  {i['qty']} x {rp(i['harga'])}"
            kanan = rp(i["qty"] * i["harga"])
            out.append(kiri + kanan.rjust(w - len(kiri)))
        out.append("-" * w)
        for label, nilai in (("TOTAL", s["total"]), ("BAYAR", s["bayar"]), ("KEMBALI", s["kembali"])):
            out.append(label + rp(nilai).rjust(w - len(label)))
        out.append("=" * w)
        out.append("Terima kasih".center(w))
        return "\n".join(out)

    def tampil_struk(self, sid):
        teks = self.teks_struk(sid)
        win = tk.Toplevel(self)
        win.title(f"Struk #{sid:06d}")
        win.transient(self)
        t = tk.Text(win, font=("Courier New", 10), width=40, height=min(40, teks.count("\n") + 2))
        t.insert("1.0", teks)
        t.config(state="disabled")
        t.pack(padx=10, pady=10)

        def simpan():
            path = filedialog.asksaveasfilename(
                defaultextension=".txt", initialfile=f"struk_{sid:06d}.txt", filetypes=[("Teks", "*.txt")]
            )
            if path:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(teks)

        bar = ttk.Frame(win)
        bar.pack(pady=(0, 10))
        ttk.Button(bar, text="Simpan .txt", command=simpan).pack(side="left", padx=4)
        ttk.Button(bar, text="Tutup", command=win.destroy).pack(side="left", padx=4)

    # ---------------------------------------------------------------- umum
    def refresh_all(self):
        self.refresh_katalog()
        self.refresh_produk()
        self.refresh_riwayat()


if __name__ == "__main__":
    App().mainloop()
