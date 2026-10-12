# 🤖 Bot Auto-Isi SiPENDEKAR Kabupaten Tangerang

Bot otomatisasi untuk mengisi laporan aktivitas harian pada portal **SiPENDEKAR** (*Sistem Informasi Penilaian Dedikasi dan Kinerja AparatuR*) Kabupaten Tangerang ([https://sipendekar.tangerangkab.go.id/2026](https://sipendekar.tangerangkab.go.id/2026)).

Bot ini dibangun berdasarkan analisis lalu lintas jaringan file HAR (`sipendekar.tangerangkab.go.id.har`), menangani autentikasi session token CSRF, fingerprint browser, pemetaan SKP, serta pengisian otomatis dengan validasi cerdas.

---

## 🌟 Fitur Utama

1. **Jadwal Otomatis Jam 17:00 (5 Sore)**:
   - Terintegrasi dengan **Windows Task Scheduler**.
   - **Komputer/Laptop Anda otomatis menjalankan pengisian setiap jam 5 sore tanpa perlu membuka terminal terus-menerus**.
   - Cerdas & aman: Mengecek apakah hari ini sudah terisi; jika sudah terisi, tidak akan diisi ulang (mencegah duplikasi).
   - Melewati hari libur akhir pekan (Sabtu & Minggu).
   - Mencatat seluruh riwayat eksekusi ke berkas `logs/auto_isi.log`.
2. **Autentikasi Otomatis & CSRF Handling**:
   - Bypass form CSRF Laravel dan header Ajax `X-CSRF-TOKEN`.
   - Menggunakan fingerprint device yang kompatibel.
3. **Pengecekan Kalender & Deteksi Hari Kosong**:
   - Memindai kalender kerja bulanan secara langsung.
   - Mengabaikan akhir pekan secara otomatis.
   - Memeriksa batas pengisian **H-7** sesuai aturan SiPENDEKAR.
4. **Auto-Filler Cerdas (1-Click)**:
   - Mengisi otomatis seluruh hari kerja kosong dalam rentang H-7 hingga hari ini.
   - Dilengkapi konfirmasi keamanan (*preview*) sebelum eksekusi.
5. **Preset Template Fleksibel**:
   - Tersedia template bawaan (Pelatihan Pranata Komputer, Layanan TI/Jaringan, Video Conference).
   - Pengguna dapat menambah atau menyesuaikan template kegiatan di `config.json`.
6. **Katalog 2.100+ Kegiatan & SKP**:
   - Dilengkapi pencarian instan seluruh katalog kegiatan SiPENDEKAR beserta menit standar dan daftar SKP akun pengguna.
7. **2 Pilihan Antarmuka**:
   - **CLI Interaktif**: Cepat, informatif dengan teks berwarna di terminal.
   - **Modern Web Dashboard**: Tampilan visual kalender modern di browser (Flask).

---

## ⏰ Cara Mengaktifkan Jadwal Otomatis Jam 5 Sore

Tersedia 2 metode praktis:

### Metode 1: Windows Task Scheduler (Sangat Direkomendasikan ⭐)
Windows akan otomatis membangunkan proses di latar belakang setiap pukul **17:00 (Senin - Jumat)** tanpa perlu membuka terminal atau aplikasi apa pun:

1. **Pasang Jadwal**:
   Klik ganda berkas **`pasang_jadwal_jam_5_sore.bat`**, atau ketik di terminal:
   ```bash
   python bot.py --install-task
   ```
2. **Lihat Riwayat Eksekusi**:
   Buka berkas `logs/auto_isi.log` untuk melihat riwayat aktivitas pengisian harian.
3. **Batalkan / Hapus Jadwal Kapan Saja**:
   Klik ganda berkas **`hapus_jadwal_otomatis.bat`**, atau ketik:
   ```bash
   python bot.py --remove-task
   ```

### Metode 2: Background Daemon (Standby di Terminal)
Jika Anda ingin bot tetap standby di jendela terminal:
```bash
python bot.py --daemon
```
atau klik ganda **`jalankan_scheduler_daemon.bat`**.

---

## 📂 Struktur Berkas

```
d:\sipendekar\
│
├── bot.py                        # Skrip utama CLI & Scheduler
├── sipendekar_api.py             # Library client API SiPENDEKAR
├── web_dashboard.py              # Web Dashboard GUI lokal (port 5000)
├── config.json                   # Pengaturan akun, jam kerja, jadwal, & template
├── activities_catalog.json       # Cache lokal katalog 2.123 kegiatan SiPENDEKAR
│
├── pasang_jadwal_jam_5_sore.bat  # Klik ganda untuk pasang jadwal otomatis jam 17:00
├── hapus_jadwal_otomatis.bat     # Klik ganda untuk menghapus jadwal otomatis
├── jalankan_scheduler_daemon.bat # Menjalankan background daemon standby
├── jalankan_web_dashboard.bat    # Pintasan Web Dashboard di browser
├── jalankan_bot_cli.bat          # Pintasan CLI interaktif di terminal
├── cek_status.bat                # Pintasan cek kalender bulan berjalan
│
├── logs/
│   └── auto_isi.log              # Log riwayat auto-fill jam 5 sore
└── README.md                     # Dokumentasi panduan
```

---

## 🚀 Cara Menjalankan Manual Lainnya

### Menggunakan Terminal / CMD

1. **Jalankan Menu Interaktif CLI**:
   ```bash
   python bot.py
   ```
2. **Cek Status Pengisian Bulan Berjalan**:
   ```bash
   python bot.py --check
   ```
3. **Auto-Isi Seluruh Hari Kosong (H-7 s/d Hari Ini)**:
   ```bash
   python bot.py --fill-empty
   ```
4. **Isi Tanggal Tertentu**:
   ```bash
   python bot.py --date 2026-10-05 --template pelatihan_prakom
   ```
5. **Buka Web Dashboard**:
   ```bash
   python bot.py --web
   ```

---

## 📦 Instalasi & Persiapan

1. **Clone repositori**:
   ```bash
   git clone https://github.com/xhdskyprime/sipendekar.git
   cd sipendekar
   ```

2. **Pasang dependensi Python**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Salin dan atur konfigurasi**:
   Salin `config.example.json` menjadi `config.json`, lalu isi NIP dan kata sandi Anda:
   ```bash
   copy config.example.json config.json
   ```

---

## ⚙️ Konfigurasi (`config.json`)

Anda dapat menyesuaikan akun, waktu penjadwalan, dan template pada berkas `config.json`:

```json
{
  "auth": {
    "username": "NIP_ANDA",
    "password": "PASSWORD_ANDA",
    "fingerprint": "09a160f689f48ed27b96d6f2fbbeec79"
  },
  "schedule": {
    "enabled": true,
    "time": "17:00",
    "days": "mon-fri",
    "skip_weekends": true,
    "fill_missed_past_days": true,
    "log_file": "logs/auto_isi.log"
  },
  "active_template": "pelatihan_prakom"
}
```

### Template Bawaan yang Tersedia:
1. **`pelatihan_prakom`**:
   - Kode: `UTAMA00463` (*Mengikuti pelatihan/sosialisasi/pendidikan*)
   - Volume: 2 (Total 600 menit / 10 jam, Pukul 07:00 - 17:00)
   - SKP: `709828` (*Terlaksananya tugas-tugas yang diberikan pimpinan*)
2. **`layanan_ti`**:
   - Kode: `UTAMA01250` (*Penerapan konfigurasi sistem jaringan komputer*, 08:00 - 12:00, SKP: `709809`)
   - Kode: `UTAMA01120` (*Tugas kedinasan lain dari pimpinan*, 13:00 - 16:00, SKP: `709828`)
3. **`vicon_meeting`**:
   - Kode: `UTAMA01120` (*Penyiapan & monitoring perangkat video conference*, 08:00 - 16:00, SKP: `709821`)
