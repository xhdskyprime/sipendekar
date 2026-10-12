"""
sipendekar_api.py - Client API untuk Sistem Informasi Penilaian Dedikasi dan Kinerja AparatuR (SiPENDEKAR)
Kabupaten Tangerang.
"""

import re
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("SipendekarAPI")

class SipendekarAPI:
    def __init__(self, base_url: str = "https://sipendekar.tangerangkab.go.id/2026", user_agent: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "id,en-US;q=0.7,en;q=0.3",
        })
        self.csrf_token: Optional[str] = None
        self.user_nip: Optional[str] = None
        self.is_logged_in: bool = False
        self._activities_cache: Optional[List[Dict[str, Any]]] = None

    def get_login_token(self) -> str:
        """Mengambil CSRF token awal dari halaman login."""
        login_url = f"{self.base_url}/login"
        resp = self.session.get(login_url, verify=False, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        token_input = soup.find("input", {"name": "_token"})
        if not token_input or not token_input.get("value"):
            raise ValueError("Gagal menemukan input CSRF _token pada halaman login.")
        return token_input["value"]

    def login(self, username: str, password: str, fingerprint: str = "09a160f689f48ed27b96d6f2fbbeec79") -> bool:
        """
        Login ke SiPENDEKAR menggunakan NIP dan Password.
        """
        token = self.get_login_token()
        login_url = f"{self.base_url}/login"
        payload = {
            "_token": token,
            "fingerprint": fingerprint,
            "username": username,
            "password": password
        }

        resp = self.session.post(
            login_url,
            data=payload,
            headers={"Referer": login_url},
            allow_redirects=True,
            verify=False,
            timeout=25
        )

        # Cek apakah diarahkan ke dashboard atau berhasil login
        # Bila gagal login, response biasanya tetap di /login dengan alert error
        if "/login" in resp.url and "Dashboard" not in resp.text:
            self.is_logged_in = False
            return False

        self.is_logged_in = True
        self.user_nip = username

        # Segera inisialisasi CSRF token aktivitas
        self.refresh_csrf_token()
        return True

    def refresh_csrf_token(self) -> str:
        """Mengambil CSRF token terbaru dari halaman aktivitas."""
        act_url = f"{self.base_url}/input/aktivitas"
        resp = self.session.get(act_url, verify=False, timeout=25)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        token_input = soup.find("input", {"name": "_token"})
        if token_input and token_input.get("value"):
            self.csrf_token = token_input["value"]
        else:
            # Fallback ke meta tag
            meta_token = soup.find("meta", {"name": "csrf-token"})
            if meta_token and meta_token.get("content"):
                self.csrf_token = meta_token["content"]

        # Cache aktivitas jika tersedia di halaman
        if not self._activities_cache:
            m = re.search(r'<pilih-aktivitas[^>]*:items=\'(\[.*?\])\'', resp.text, re.DOTALL)
            if m:
                try:
                    self._activities_cache = json.loads(m.group(1))
                except Exception as e:
                    logger.warning(f"Gagal mem-parse katalog aktivitas dari HTML: {e}")

        return self.csrf_token or ""

    def get_activities_catalog(self) -> List[Dict[str, Any]]:
        """Mengambil seluruh daftar katalog aktivitas yang tersedia."""
        if self._activities_cache:
            return self._activities_cache
        self.refresh_csrf_token()
        return self._activities_cache or []

    def search_catalog(self, keyword: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Mencari kegiatan di katalog berdasarkan kata kunci."""
        catalog = self.get_activities_catalog()
        keyword_lower = keyword.lower()
        results = []
        for item in catalog:
            nama = item.get("nama_aktifitas", "").lower()
            kode = item.get("kode_aktifitas", "").lower()
            if keyword_lower in nama or keyword_lower in kode:
                results.append(item)
                if len(results) >= limit:
                    break
        return results

    def get_skp(self, kode_aktivitas: str) -> List[Dict[str, Any]]:
        """
        Mengambil Sasaran Kinerja Pegawai (SKP) yang valid untuk kode aktivitas tertentu.
        Returns: list of dict {'id': int, 'nama': str}
        """
        url = f"{self.base_url}/input/getKegiatan"
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/input/aktivitas"
        }
        resp = self.session.get(url, params={"kode_aktivitas": kode_aktivitas}, headers=headers, verify=False, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        skp_list = []
        s_ids = data.get("sasaran_kerja_id", [])
        s_names = data.get("nama_skp", [])
        for sid, name in zip(s_ids, s_names):
            if sid != 0 and name != "-":
                skp_list.append({"id": sid, "nama": name})
        return skp_list

    def get_aktivitas_harian(self, tanggal: str, jenis: str = "kinerja") -> List[Dict[str, Any]]:
        """
        Mengambil daftar aktivitas yang sudah diisi pada tanggal tertentu.
        tanggal: Format YYYY-MM-DD
        """
        url = f"{self.base_url}/input/getaktivitastampil"
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/input/aktivitas"
        }
        resp = self.session.get(url, params={"tanggal": tanggal, "jenis": jenis}, headers=headers, verify=False, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_total_menit_harian(self, tanggal: str) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Menghitung total menit kegiatan yang sudah dilaporkan pada tanggal tertentu.
        Returns: (total_menit, list_detail_kegiatan)
        """
        data = self.get_aktivitas_harian(tanggal, jenis="kinerja")
        total_menit = 0
        detail = []
        for item in data:
            nama = item.get("nama_aktifitas", "")
            kode = item.get("kode_aktifitas", "")
            waktu_standar = item.get("waktu", 0)
            for isi in item.get("isi_aktifitas", []):
                vol = isi.get("volume", 1)
                jam_m = isi.get("jam_mulai", 0)
                menit_m = isi.get("menit_mulai", 0)
                jam_s = isi.get("jam_selesai", 0)
                menit_s = isi.get("menit_selesai", 0)
                durasi = ((jam_s * 60) + menit_s) - ((jam_m * 60) + menit_m)
                total_menit += durasi
                detail.append({
                    "id": isi.get("id"),
                    "kode_aktifitas": kode,
                    "nama_aktifitas": nama,
                    "volume": vol,
                    "keterangan": isi.get("keterangan", ""),
                    "durasi_menit": durasi,
                    "jam_mulai": f"{jam_m:02d}:{menit_m:02d}",
                    "jam_selesai": f"{jam_s:02d}:{menit_s:02d}",
                    "sasaran_kerja_id": isi.get("sasaran_kerja_id")
                })
        return total_menit, detail

    def get_kalender_bulan(self, tahun: int, bulan: int) -> Dict[str, Any]:
        """
        Melihat rekap kalender per bulan dari SiPENDEKAR.
        """
        # Timestamp awal dan akhir bulan (UTC timestamp in milliseconds)
        dt_from = datetime(tahun, bulan, 1)
        if bulan == 12:
            dt_to = datetime(tahun + 1, 1, 1) - timedelta(days=1)
        else:
            dt_to = datetime(tahun, bulan + 1, 1) - timedelta(days=1)

        ts_from = int(dt_from.timestamp() * 1000)
        ts_to = int(dt_to.timestamp() * 1000)

        url = f"{self.base_url}/input/getValueCal"
        params = {
            "from": ts_from,
            "to": ts_to,
            "utc_offset_from": -420,
            "utc_offset_to": -420
        }
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/input/aktivitas"
        }
        resp = self.session.get(url, params=params, headers=headers, verify=False, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def isi_aktivitas(
        self,
        tanggal: str,
        kode_aktifitas: str,
        volume: int,
        keterangan: str,
        sasaran_kerja_id: int,
        jam_mulai: str,
        menit_mulai: str,
        jam_selesai: str,
        menit_selesai: str,
        jenis: str = "kinerja",
        nip18: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mengirim laporan aktivitas harian.
        tanggal: YYYY-MM-DD
        jam_mulai: "07", menit_mulai: "00", dst.
        """
        if not self.csrf_token:
            self.refresh_csrf_token()

        url = f"{self.base_url}/input/isiaktifitas"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-TOKEN": self.csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/input/aktivitas"
        }

        payload = {
            "tanggal": tanggal,
            "nip18": nip18 or self.user_nip or "",
            "kode_aktifitas": kode_aktifitas,
            "kode_kegiatan": "",
            "volume": str(volume),
            "keterangan": keterangan,
            "tupoksi": "",
            "sasaran_kerja_id": str(sasaran_kerja_id),
            "jenis": jenis,
            "jam_mulai": str(jam_mulai).zfill(2),
            "jam_selesai": str(jam_selesai).zfill(2),
            "menit_mulai": str(menit_mulai).zfill(2),
            "menit_selesai": str(menit_selesai).zfill(2),
            "id_input": ""
        }

        resp = self.session.post(url, data=payload, headers=headers, verify=False, timeout=20)
        resp.raise_for_status()
        result = resp.json()
        return result

    def hapus_aktivitas(self, id_laporan: int) -> Dict[str, Any]:
        """
        Membatalkan/menghapus laporan aktivitas berdasarkan ID.
        """
        if not self.csrf_token:
            self.refresh_csrf_token()

        url = f"{self.base_url}/input/hapusaktifitas"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-TOKEN": self.csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/input/aktivitas"
        }

        payload = {"id": str(id_laporan)}
        resp = self.session.post(url, data=payload, headers=headers, verify=False, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def cari_hari_kosong(
        self,
        start_date: date,
        end_date: date,
        skip_weekends: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Memindai rentang tanggal untuk menemukan hari kerja yang belum ada laporannya.
        """
        curr = start_date
        empty_days = []
        while curr <= end_date:
            is_weekend = curr.weekday() in (5, 6) # Sabtu=5, Minggu=6
            if skip_weekends and is_weekend:
                curr += timedelta(days=1)
                continue

            tgl_str = curr.strftime("%Y-%m-%d")
            total_menit, detail = self.get_total_menit_harian(tgl_str)
            if len(detail) == 0:
                empty_days.append({
                    "tanggal": tgl_str,
                    "hari": curr.strftime("%A"),
                    "status": "Kosong",
                    "total_menit": 0
                })
            curr += timedelta(days=1)

        return empty_days
