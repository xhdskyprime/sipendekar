"""
bot.py - Bot CLI Otomatisasi Pengisian SiPENDEKAR Kabupaten Tangerang
Mendukung eksekusi terjadwal setiap jam 17:00 (5 sore).
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    BOLD = Style.BRIGHT
    RESET = Style.RESET_ALL
except ImportError:
    GREEN = RED = YELLOW = CYAN = MAGENTA = BOLD = RESET = ""

from sipendekar_api import SipendekarAPI

CONFIG_FILE = "config.json"
TASK_NAME = "SiPENDEKAR_AutoFill_5PM"

def get_base_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))

def get_log_file(cfg: Dict[str, Any]) -> str:
    log_rel = cfg.get("schedule", {}).get("log_file", "logs/auto_isi.log")
    log_path = os.path.join(get_base_dir(), log_rel)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    return log_path

def log_message(msg: str, cfg: Optional[Dict[str, Any]] = None, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] {msg}"
    print(formatted)
    if cfg:
        try:
            log_file = get_log_file(cfg)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception:
            pass

def load_config() -> Dict[str, Any]:
    cfg_path = os.path.join(get_base_dir(), CONFIG_FILE)
    if not os.path.exists(cfg_path):
        example_path = os.path.join(get_base_dir(), "config.example.json")
        if os.path.exists(example_path):
            import shutil
            shutil.copyfile(example_path, cfg_path)
            print(f"{YELLOW}[INFO]{RESET} config.json belum ada. Berhasil disalin dari config.example.json.")
            print(f"{YELLOW}[PERINGATAN]{RESET} Silakan isi username (NIP) dan password Anda di config.json sebelum melanjutkan.")
            sys.exit(1)
        print(f"{RED}[ERROR]{RESET} File konfigurasi {cfg_path} tidak ditemukan!")
        sys.exit(1)
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg: Dict[str, Any]):
    cfg_path = os.path.join(get_base_dir(), CONFIG_FILE)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_api(cfg: Dict[str, Any], quiet: bool = False) -> SipendekarAPI:
    base_url = cfg.get("sipendekar", {}).get("base_url", "https://sipendekar.tangerangkab.go.id/2026")
    api = SipendekarAPI(base_url=base_url)
    username = cfg["auth"]["username"]
    password = cfg["auth"]["password"]
    fingerprint = cfg["auth"].get("fingerprint", "09a160f689f48ed27b96d6f2fbbeec79")

    if not quiet:
        print(f"{CYAN}[INFO]{RESET} Melakukan autentikasi NIP: {BOLD}{username}{RESET} ...", end=" ", flush=True)

    if api.login(username, password, fingerprint):
        if not quiet:
            print(f"{GREEN}[BERHASIL]{RESET}")
    else:
        if not quiet:
            print(f"{RED}[GAGAL]{RESET}")
        log_message("Login gagal. Periksa username & password di config.json.", cfg, level="ERROR")
        sys.exit(1)
    return api

def cetak_status_bulan(api: SipendekarAPI, cfg: Dict[str, Any], tahun: int, bulan: int):
    """Menampilkan status pengisian hari dalam sebulan."""
    print(f"\n{BOLD}=== STATUS REKAP BULAN {bulan:02d}/{tahun} ==={RESET}")
    dt_now = date.today()
    hmin7 = dt_now - timedelta(days=cfg.get("settings", {}).get("max_hmin_days", 7))

    d_start = date(tahun, bulan, 1)
    if bulan == 12:
        d_end = date(tahun + 1, 1, 1) - timedelta(days=1)
    else:
        d_end = date(tahun, bulan + 1, 1) - timedelta(days=1)

    print(f"{'Tanggal':<12} | {'Hari':<9} | {'Status':<14} | {'Total Menit':<12} | {'Keterangan'}")
    print("-" * 75)

    curr = d_start
    total_hari_kerja = 0
    total_terisi = 0
    total_kosong = 0

    while curr <= d_end:
        is_weekend = curr.weekday() in (5, 6)
        tgl_str = curr.strftime("%Y-%m-%d")
        hari_str = curr.strftime("%A")
        hari_id = {
            "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
            "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
        }.get(hari_str, hari_str)

        if curr > dt_now:
            print(f"{tgl_str:<12} | {hari_id:<9} | {CYAN}{'Masa Depan':<14}{RESET} | {'-':<12} | -")
            curr += timedelta(days=1)
            continue

        if is_weekend:
            print(f"{tgl_str:<12} | {hari_id:<9} | {'Libur Akhir Pekan':<14} | {'-':<12} | -")
            curr += timedelta(days=1)
            continue

        total_hari_kerja += 1
        menit, detail = api.get_total_menit_harian(tgl_str)
        in_h7 = curr >= hmin7

        if len(detail) > 0:
            total_terisi += 1
            status_text = f"{GREEN}Terisi ({len(detail)}){RESET}"
            ket = f"{menit} menit ({detail[0]['nama_aktifitas'][:30]}...)"
            print(f"{tgl_str:<12} | {hari_id:<9} | {status_text:<23} | {f'{menit} menit':<12} | {ket}")
        else:
            total_kosong += 1
            if in_h7:
                status_text = f"{RED}KOSONG (Bisa diisi){RESET}"
            else:
                status_text = f"{YELLOW}KOSONG (Lewat H-7){RESET}"
            print(f"{tgl_str:<12} | {hari_id:<9} | {status_text:<23} | {'0 menit':<12} | {'Perlu diisi segera!' if in_h7 else 'Terkunci sistem'}")

        curr += timedelta(days=1)

    print("-" * 75)
    print(f"Total Hari Kerja Lewat: {total_hari_kerja} | {GREEN}Terisi: {total_terisi}{RESET} | {RED}Kosong: {total_kosong}{RESET}\n")

def submit_template_for_date(api: SipendekarAPI, tgl_str: str, template: Dict[str, Any], delay_sec: float = 1.0, quiet: bool = False) -> bool:
    """Mengirim semua item dalam template ke satu tanggal tertentu."""
    items = template.get("items", [])
    if not items:
        if not quiet:
            print(f"{RED}[ERROR]{RESET} Template tidak memiliki item aktivitas!")
        return False

    success_all = True
    for idx, item in enumerate(items, 1):
        if not quiet:
            print(f"  -> [{idx}/{len(items)}] Mengisi: {item['nama_aktifitas']} ({item['jam_mulai']}:{item['menit_mulai']} - {item['jam_selesai']}:{item['menit_selesai']})...", end=" ", flush=True)
        try:
            res = api.isi_aktivitas(
                tanggal=tgl_str,
                kode_aktifitas=item["kode_aktifitas"],
                volume=item.get("volume", 1),
                keterangan=item.get("keterangan", "-"),
                sasaran_kerja_id=item["sasaran_kerja_id"],
                jam_mulai=item["jam_mulai"],
                menit_mulai=item["menit_mulai"],
                jam_selesai=item["jam_selesai"],
                menit_selesai=item["menit_selesai"],
                jenis=item.get("jenis", "kinerja")
            )
            if res.get("success") is True or res.get("success") == 1:
                if not quiet:
                    print(f"{GREEN}[OK]{RESET}")
            else:
                err_msg = res.get("error", "Gagal menyimpan")
                if not quiet:
                    print(f"{RED}[GAGAL: {err_msg}]{RESET}")
                success_all = False
        except Exception as e:
            if not quiet:
                print(f"{RED}[ERROR: {e}]{RESET}")
            success_all = False

        if delay_sec > 0:
            time.sleep(delay_sec)

    return success_all

def proses_auto_isi_kosong(api: SipendekarAPI, cfg: Dict[str, Any], template_key: Optional[str] = None, force_confirm: bool = False):
    """Mendeteksi hari kosong dalam rentang H-7 dan mengisinya."""
    dt_now = date.today()
    max_hmin = cfg.get("settings", {}).get("max_hmin_days", 7)
    dt_hmin = dt_now - timedelta(days=max_hmin)

    tkey = template_key or cfg.get("active_template", "pelatihan_prakom")
    template = cfg.get("templates", {}).get(tkey)
    if not template:
        print(f"{RED}[ERROR]{RESET} Template '{tkey}' tidak ditemukan di config.json!")
        return

    print(f"\n{BOLD}=== AUTO-ISI HARI KOSONG (H-{max_hmin} s/d Hari Ini) ==={RESET}")
    print(f"Rentang Tanggal: {CYAN}{dt_hmin} s/d {dt_now}{RESET}")
    print(f"Template Digunakan: {BOLD}{template['nama_template']}{RESET}")
    print(f"Mendeteksi hari kosong...", end=" ", flush=True)

    kosong = api.cari_hari_kosong(dt_hmin, dt_now, skip_weekends=cfg.get("settings", {}).get("skip_weekends", True))
    print(f"Ditemukan {BOLD}{len(kosong)}{RESET} hari kerja kosong.")

    if not kosong:
        print(f"{GREEN}[SELAMAT]{RESET} Semua hari kerja dalam periode H-{max_hmin} sudah lengkap terisi!")
        return

    print("\nDaftar hari yang akan diisi:")
    for k in kosong:
        print(f" - {BOLD}{k['tanggal']}{RESET} ({k['hari']})")

    auto_confirm = cfg.get("settings", {}).get("auto_confirm", False) or force_confirm
    if not auto_confirm:
        konfirm = input(f"\n{YELLOW}Apakah Anda yakin ingin mengisi {len(kosong)} hari tersebut? (y/N): {RESET}").strip().lower()
        if konfirm != "y":
            print(f"{YELLOW}[DIBATALKAN]{RESET} Pengisian dibatalkan oleh pengguna.")
            return

    delay = cfg.get("settings", {}).get("delay_between_requests_sec", 1.5)
    print(f"\n{BOLD}Memulai proses pengisian otomatis...{RESET}")

    berhasil_count = 0
    for k in kosong:
        tgl = k["tanggal"]
        print(f"\n[{tgl}] Mengisi aktivitas...")
        sukses = submit_template_for_date(api, tgl, template, delay_sec=delay)
        if sukses:
            berhasil_count += 1

    print(f"\n{GREEN}[SELESAI]{RESET} Berhasil mengisi {berhasil_count} dari {len(kosong)} hari kosong.")

def run_auto_today(api: Optional[SipendekarAPI] = None, cfg: Optional[Dict[str, Any]] = None):
    """
    Eksekusi otomatis untuk hari ini (digunakan oleh Task Scheduler jam 17:00).
    Aman, idempotent, dan mencatat log ke file logs/auto_isi.log.
    """
    if cfg is None:
        cfg = load_config()

    log_message("=== MEMULAI AUTO-FILL HARIAN SiPENDEKAR ===", cfg, level="INFO")
    today = date.today()
    tgl_str = str(today)
    is_weekend = today.weekday() in (5, 6)

    skip_weekends = cfg.get("schedule", {}).get("skip_weekends", True)
    if skip_weekends and is_weekend:
        log_message(f"Hari ini ({tgl_str}) adalah akhir pekan (Sabtu/Minggu). Libur kerja, pengisian dilewati.", cfg, level="INFO")
        return

    if api is None:
        api = get_api(cfg, quiet=True)

    tkey = cfg.get("active_template", "pelatihan_prakom")
    template = cfg.get("templates", {}).get(tkey)
    if not template:
        log_message(f"Template '{tkey}' tidak ditemukan di config.json!", cfg, level="ERROR")
        return

    # Cek hari ini
    menit, detail = api.get_total_menit_harian(tgl_str)
    if len(detail) > 0:
        log_message(f"Hari ini ({tgl_str}) sudah terisi ({menit} menit, {len(detail)} aktivitas). Tidak perlu diisi ulang.", cfg, level="INFO")
    else:
        log_message(f"Hari ini ({tgl_str}) belum terisi. Mengisi dengan template: '{template['nama_template']}'...", cfg, level="INFO")
        sukses = submit_template_for_date(api, tgl_str, template, delay_sec=1.5, quiet=True)
        if sukses:
            log_message(f"BERHASIL: Laporan hari ini ({tgl_str}) telah sukses diisi!", cfg, level="SUCCESS")
        else:
            log_message(f"GAGAL: Terjadi kendala saat mengisi laporan hari ini ({tgl_str}).", cfg, level="ERROR")

    # Cek apakah ada hari kosong sebelumnya dalam rentang H-7 yang terlewat
    if cfg.get("schedule", {}).get("fill_missed_past_days", True):
        max_hmin = cfg.get("settings", {}).get("max_hmin_days", 7)
        dt_hmin = today - timedelta(days=max_hmin)
        kosong_past = api.cari_hari_kosong(dt_hmin, today - timedelta(days=1), skip_weekends=True)
        if kosong_past:
            log_message(f"Ditemukan {len(kosong_past)} hari kerja lampau yang belum terisi dalam batas H-{max_hmin}. Memproses pengisian...", cfg, level="INFO")
            for k in kosong_past:
                tgl_k = k["tanggal"]
                log_message(f"Mengisi hari lampau: {tgl_k}...", cfg, level="INFO")
                res_k = submit_template_for_date(api, tgl_k, template, delay_sec=1.5, quiet=True)
                if res_k:
                    log_message(f"BERHASIL: {tgl_k} sukses diisi.", cfg, level="SUCCESS")
                else:
                    log_message(f"GAGAL: {tgl_k} gagal diisi.", cfg, level="ERROR")

    log_message("=== SELESAI AUTO-FILL HARIAN ===", cfg, level="INFO")

# --- MANAJEMEN WINDOWS TASK SCHEDULER ---

def pasang_windows_task():
    """Mendaftarkan tugas otomatisasi ke Windows Task Scheduler pada jam 17:00."""
    cfg = load_config()
    target_time = cfg.get("schedule", {}).get("time", "17:00")
    python_exe = sys.executable
    script_path = os.path.join(get_base_dir(), "bot.py")
    cmd_run = f'"{python_exe}" "{script_path}" --auto-today'

    print(f"\n{BOLD}=== PASANG JADWAL OTOMATIS WINDOWS (JAM {target_time}) ==={RESET}")
    print(f"Nama Task: {CYAN}{TASK_NAME}{RESET}")
    print(f"Jadwal   : Setiap Hari Kerja (Senin - Jumat) Pukul {BOLD}{target_time}{RESET}")
    print(f"Perintah : {cmd_run}")

    # Gunakan schtasks untuk membuat task harian di Windows
    # /sc daily /st 17:00
    cmd_schtask = [
        "schtasks", "/Create",
        "/TN", TASK_NAME,
        "/TR", cmd_run,
        "/SC", "DAILY",
        "/ST", target_time,
        "/F"
    ]

    try:
        res = subprocess.run(cmd_schtask, capture_output=True, text=True, check=True)
        print(f"\n{GREEN}[BERHASIL]{RESET} Jadwal otomatis berhasil dipasang di Windows Task Scheduler!")
        print(f"Windows akan secara otomatis menjalankan bot setiap jam {target_time} sore.")
        print(f"Log hasil pengisian dapat dilihat di file: {CYAN}{get_log_file(cfg)}{RESET}")
    except subprocess.CalledProcessError as e:
        print(f"\n{RED}[GAGAL MEMASANG JADWAL]{RESET}")
        print(f"Output error: {e.stderr.strip() or e.stdout.strip()}")
        print(f"{YELLOW}Tips: Pastikan menjalankan Command Prompt atau bot sebagai Administrator jika akses ditolak.{RESET}")

def hapus_windows_task():
    """Menghapus tugas otomatisasi dari Windows Task Scheduler."""
    print(f"\n{BOLD}=== HAPUS JADWAL OTOMATIS WINDOWS ==={RESET}")
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"{GREEN}[BERHASIL]{RESET} Jadwal {TASK_NAME} telah dihapus dari Windows Task Scheduler.")
    except subprocess.CalledProcessError as e:
        print(f"{YELLOW}[INFO]{RESET} Jadwal tidak ditemukan atau gagal dihapus: {e.stderr.strip() or e.stdout.strip()}")

def cek_windows_task():
    """Mengecek status tugas di Windows Task Scheduler."""
    print(f"\n{BOLD}=== STATUS JADWAL WINDOWS TASK SCHEDULER ==={RESET}")
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(res.stdout)
    except subprocess.CalledProcessError:
        print(f"{YELLOW}Jadwal '{TASK_NAME}' belum terpasang di sistem Windows ini.{RESET}")

def run_scheduler_daemon():
    """Menjalankan background scheduler internal (APScheduler)."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print(f"{RED}[ERROR]{RESET} Library APScheduler belum terpasang. Jalankan: pip install apscheduler")
        return

    cfg = load_config()
    target_time = cfg.get("schedule", {}).get("time", "17:00")
    jam, menit = target_time.split(":")

    sched = BlockingScheduler()
    # Jadwalkan Senin - Jumat pada jam yang ditentukan
    trigger = CronTrigger(day_of_week="mon-fri", hour=int(jam), minute=int(menit))

    print(f"""
{CYAN}================================================================={RESET}
{BOLD}{MAGENTA}   SiPENDEKAR DAEMON SCHEDULER (STANDBY){RESET}
{CYAN}================================================================={RESET}
  Jadwal Otomatis: Setiap Senin - Jumat Pukul {BOLD}{target_time}{RESET}
  Template Aktif : {BOLD}{cfg.get('active_template')}{RESET}
  Log Berkas     : {BOLD}{get_log_file(cfg)}{RESET}
  Status         : {GREEN}AKTIF MENUNGGU JAM {target_time}...{RESET}
  Tekan Ctrl+C untuk menghentikan.
{CYAN}================================================================={RESET}
""")

    def job():
        print(f"\n{BOLD}[TRIGGER]{RESET} Waktu menunjukkan {target_time}. Menjalankan auto-fill...")
        try:
            c = load_config()
            a = get_api(c, quiet=True)
            run_auto_today(a, c)
        except Exception as e:
            log_message(f"Kesalahan pada daemon: {e}", cfg, level="ERROR")

    sched.add_job(job, trigger)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print(f"\n{YELLOW}Daemon scheduler dihentikan.{RESET}")

def lihat_dan_hapus_harian(api: SipendekarAPI, tgl_str: str):
    """Melihat detail kegiatan dan opsi menghapus."""
    print(f"\n{BOLD}=== AKTIVITAS PADA TANGGAL {tgl_str} ==={RESET}")
    menit, detail = api.get_total_menit_harian(tgl_str)
    if not detail:
        print(f"{YELLOW}Tidak ada aktivitas yang tercatat pada tanggal {tgl_str}.{RESET}")
        return

    print(f"Total Durasi: {BOLD}{menit} Menit{RESET} ({len(detail)} aktivitas)")
    print(f"{'No':<3} | {'ID':<10} | {'Waktu':<13} | {'Kode':<12} | {'Aktivitas'}")
    print("-" * 75)
    for idx, d in enumerate(detail, 1):
        print(f"{idx:<3} | {d['id']:<10} | {d['jam_mulai']}-{d['jam_selesai']:<7} | {d['kode_aktifitas']:<12} | {d['nama_aktifitas']}")
        print(f"     Ket: {d['keterangan']}")
    print("-" * 75)

    pilihan = input(f"\nKetik nomor/ID kegiatan yang ingin dihapus, atau tekan Enter untuk kembali: ").strip()
    if not pilihan:
        return

    target_id = None
    if pilihan.isdigit():
        idx_p = int(pilihan)
        if 1 <= idx_p <= len(detail):
            target_id = detail[idx_p - 1]["id"]
        else:
            target_id = int(pilihan)

    if target_id:
        konfirm = input(f"{RED}Yakin ingin menghapus aktivitas dengan ID {target_id}? (y/N): {RESET}").strip().lower()
        if konfirm == "y":
            res = api.hapus_aktivitas(target_id)
            print(f"{GREEN}[BERHASIL]{RESET} Aktivitas ID {target_id} telah dihapus.")
        else:
            print("Penghapusan dibatalkan.")

def cari_katalog_dan_skp(api: SipendekarAPI):
    """Mencari aktivitas di katalog beserta SKP terkait."""
    kw = input(f"\n{CYAN}Masukkan kata kunci pencarian kegiatan: {RESET}").strip()
    if not kw:
        return
    results = api.search_catalog(kw, limit=10)
    if not results:
        print(f"{YELLOW}Tidak ditemukan aktivitas dengan kata kunci '{kw}'.{RESET}")
        return

    print(f"\n{BOLD}Ditemukan {len(results)} aktivitas:{RESET}")
    for idx, r in enumerate(results, 1):
        print(f"[{idx}] {BOLD}{r['kode_aktifitas']}{RESET} - {r['nama_aktifitas']}")
        print(f"    Waktu: {r['waktu']} menit | Satuan: {r['satuan_output']} | Kategori: {r['kategori']}")

    pilih = input(f"\nKetik nomor (1-{len(results)}) untuk melihat daftar SKP yang cocok, atau Enter: ").strip()
    if pilih.isdigit() and 1 <= int(pilih) <= len(results):
        selected = results[int(pilih) - 1]
        kode = selected["kode_aktifitas"]
        print(f"\nMengambil SKP untuk {kode}...", end=" ", flush=True)
        skp_list = api.get_skp(kode)
        print(f"{GREEN}OK{RESET}")
        if not skp_list:
            print(f"{YELLOW}Tidak ada SKP yang terkait dengan kegiatan ini untuk akun Anda.{RESET}")
        else:
            print(f"{BOLD}Daftar SKP yang dapat dipilih:{RESET}")
            for skp in skp_list:
                print(f" - [ID: {skp['id']}] {skp['nama']}")

def pilih_template(cfg: Dict[str, Any]) -> str:
    """Memilih template aktif."""
    templates = cfg.get("templates", {})
    keys = list(templates.keys())
    print(f"\n{BOLD}Pilih Template Aktivitas:{RESET}")
    for idx, k in enumerate(keys, 1):
        t = templates[k]
        aktif = " (AKTIF)" if k == cfg.get("active_template") else ""
        print(f" [{idx}] {BOLD}{t['nama_template']}{RESET}{aktif}")
        print(f"     Deskripsi: {t.get('deskripsi', '-')}")

    pilih = input(f"\nPilih nomor template (1-{len(keys)}) atau Enter untuk tetap: ").strip()
    if pilih.isdigit() and 1 <= int(pilih) <= len(keys):
        sel_key = keys[int(pilih) - 1]
        cfg["active_template"] = sel_key
        save_config(cfg)
        print(f"{GREEN}Template aktif diganti menjadi: {sel_key}{RESET}")
        return sel_key
    return cfg.get("active_template", keys[0])

def menu_jadwal():
    """Sub-menu pengaturan jadwal otomatis."""
    while True:
        cfg = load_config()
        jam = cfg.get("schedule", {}).get("time", "17:00")
        print(f"""
{BOLD}=== PENGATURAN JADWAL OTOMATIS (JAM {jam}) ==={RESET}
 [1] Pasang Jadwal di Windows Task Scheduler (Rekomendasi - Otomatis Jam {jam})
 [2] Cek Status Jadwal di Windows Task Scheduler
 [3] Hapus Jadwal dari Windows Task Scheduler
 [4] Ubah Jam Pengisian Otomatis (Saat ini: {jam})
 [5] Jalankan Eksekusi Hari Ini Sekarang (Test Run)
 [0] Kembali ke Menu Utama
""")
        p = input(f"{BOLD}Pilih opsi [0-5]: {RESET}").strip()
        if p == "1":
            pasang_windows_task()
        elif p == "2":
            cek_windows_task()
        elif p == "3":
            hapus_windows_task()
        elif p == "4":
            new_jam = input(f"Masukkan jam baru (Format JJ:MM, contoh: 17:00): ").strip()
            if len(new_jam) == 5 and ":" in new_jam:
                cfg.setdefault("schedule", {})["time"] = new_jam
                save_config(cfg)
                print(f"{GREEN}Jam jadwal otomatis diubah menjadi {new_jam}.{RESET}")
                tanya = input("Perbarui jadwal di Windows Task Scheduler sekarang? (y/N): ").strip().lower()
                if tanya == "y":
                    pasang_windows_task()
            else:
                print(f"{RED}Format jam salah! Harus format JJ:MM (contoh: 17:00).{RESET}")
        elif p == "5":
            api = get_api(cfg)
            run_auto_today(api, cfg)
        elif p == "0":
            break

def main_interactive():
    cfg = load_config()
    jam_sch = cfg.get("schedule", {}).get("time", "17:00")
    print(f"""
{CYAN}================================================================={RESET}
{BOLD}{MAGENTA}   BOT AUTO-ISI SiPENDEKAR - KABUPATEN TANGERANG{RESET}
{CYAN}================================================================={RESET}
  NIP Pengguna   : {BOLD}{cfg['auth']['username']}{RESET}
  Tahun Berjalan : {BOLD}{cfg['sipendekar'].get('year', 2026)}{RESET}
  Template Aktif : {BOLD}{cfg.get('active_template', 'pelatihan_prakom')}{RESET}
  Jadwal Otomatis: {BOLD}Setiap Hari Kerja Jam {jam_sch} Sore{RESET}
{CYAN}================================================================={RESET}
""")

    api = get_api(cfg)

    while True:
        print(f"""
{BOLD}MENU UTAMA:{RESET}
 [1] Cek Status Hari Kerja & Kalender Bulan Ini
 [2] Auto-Isi Semua Hari Kosong (Rentang H-7 s/d Hari Ini)
 [3] Isi Manual untuk Satu Tanggal Tertentu
 [4] Lihat Detail / Hapus Aktivitas Tanggal Tertentu
 [5] Cari Katalog Kegiatan & Cek SKP
 [6] Ganti Template Kegiatan Aktif
 [7] Buka Web Dashboard Lokal
 [8] Pengaturan Jadwal Otomatis Jam {jam_sch} Sore (Windows Task Scheduler)
 [9] Jalankan Scheduler Daemon (Standby Background)
 [0] Keluar
""")
        pilihan = input(f"{BOLD}Pilih opsi [0-9]: {RESET}").strip()

        if pilihan == "1":
            today = date.today()
            bln = input(f"Bulan [1-12] (Default: {today.month}): ").strip()
            thn = input(f"Tahun (Default: {today.year}): ").strip()
            bulan = int(bln) if bln.isdigit() else today.month
            tahun = int(thn) if thn.isdigit() else today.year
            cetak_status_bulan(api, cfg, tahun, bulan)

        elif pilihan == "2":
            proses_auto_isi_kosong(api, cfg)

        elif pilihan == "3":
            tgl = input(f"Masukkan tanggal (Format YYYY-MM-DD, Default: {date.today()}): ").strip()
            if not tgl:
                tgl = str(date.today())
            try:
                datetime.strptime(tgl, "%Y-%m-%d")
            except ValueError:
                print(f"{RED}[ERROR] Format tanggal harus YYYY-MM-DD!{RESET}")
                continue

            menit, detail = api.get_total_menit_harian(tgl)
            if detail:
                print(f"{YELLOW}[PERINGATAN] Tanggal {tgl} sudah memiliki {len(detail)} aktivitas ({menit} menit).{RESET}")
                lanjut = input("Apakah ingin tetap menambahkan? (y/N): ").strip().lower()
                if lanjut != "y":
                    continue

            tkey = cfg.get("active_template", "pelatihan_prakom")
            template = cfg.get("templates", {}).get(tkey)
            print(f"Menggunakan template: {BOLD}{template['nama_template']}{RESET}")
            submit_template_for_date(api, tgl, template)

        elif pilihan == "4":
            tgl = input(f"Masukkan tanggal yang ingin dicek (YYYY-MM-DD, Default: {date.today()}): ").strip()
            if not tgl:
                tgl = str(date.today())
            lihat_dan_hapus_harian(api, tgl)

        elif pilihan == "5":
            cari_katalog_dan_skp(api)

        elif pilihan == "6":
            pilih_template(cfg)

        elif pilihan == "7":
            print(f"{CYAN}Menjalankan Web Dashboard di http://127.0.0.1:5000 ...{RESET}")
            os.system(f"python web_dashboard.py")

        elif pilihan == "8":
            menu_jadwal()

        elif pilihan == "9":
            run_scheduler_daemon()

        elif pilihan == "0":
            print(f"{CYAN}Terima kasih telah menggunakan Bot SiPENDEKAR.{RESET}")
            break
        else:
            print(f"{RED}Pilihan tidak valid! Silakan pilih 0-9.{RESET}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot Auto-Isi SiPENDEKAR Kabupaten Tangerang")
    parser.add_argument("--check", action="store_true", help="Cek status kalender bulan berjalan")
    parser.add_argument("--fill-empty", action="store_true", help="Auto-isi semua hari kerja yang kosong di rentang H-7")
    parser.add_argument("--date", type=str, help="Isi aktivitas untuk tanggal tertentu (YYYY-MM-DD)")
    parser.add_argument("--template", type=str, help="Kunci template yang digunakan")
    parser.add_argument("--yes", action="store_true", help="Lewati konfirmasi (langsung eksekusi)")
    parser.add_argument("--web", action="store_true", help="Jalankan Web Dashboard")
    parser.add_argument("--auto-today", action="store_true", help="Eksekusi otomatis pengisian hari ini (untuk Task Scheduler)")
    parser.add_argument("--daemon", action="store_true", help="Jalankan daemon scheduler background")
    parser.add_argument("--install-task", action="store_true", help="Pasang jadwal otomatis di Windows Task Scheduler")
    parser.add_argument("--remove-task", action="store_true", help="Hapus jadwal dari Windows Task Scheduler")

    args = parser.parse_args()

    if args.web:
        os.system("python web_dashboard.py")
        sys.exit(0)

    if args.daemon:
        run_scheduler_daemon()
        sys.exit(0)

    if args.install_task:
        pasang_windows_task()
        sys.exit(0)

    if args.remove_task:
        hapus_windows_task()
        sys.exit(0)

    cfg = load_config()

    if args.auto_today:
        run_auto_today(cfg=cfg)
        sys.exit(0)

    if args.check:
        api = get_api(cfg)
        td = date.today()
        cetak_status_bulan(api, cfg, td.year, td.month)
    elif args.fill_empty:
        api = get_api(cfg)
        proses_auto_isi_kosong(api, cfg, template_key=args.template, force_confirm=args.yes)
    elif args.date:
        api = get_api(cfg)
        tkey = args.template or cfg.get("active_template", "pelatihan_prakom")
        tmpl = cfg.get("templates", {}).get(tkey)
        if not tmpl:
            print(f"{RED}Template {tkey} tidak ditemukan.{RESET}")
            sys.exit(1)
        submit_template_for_date(api, args.date, tmpl)
    else:
        main_interactive()
