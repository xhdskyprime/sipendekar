"""
web_dashboard.py - Web Interface Modern untuk Bot SiPENDEKAR Kabupaten Tangerang
"""

import os
import json
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, render_template_string
from sipendekar_api import SipendekarAPI

app = Flask(__name__)
CONFIG_FILE = "config.json"

def get_config():
    if not os.path.exists(CONFIG_FILE):
        example_path = "config.example.json"
        if os.path.exists(example_path):
            import shutil
            shutil.copyfile(example_path, CONFIG_FILE)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_api_client():
    cfg = get_config()
    api = SipendekarAPI(base_url=cfg["sipendekar"]["base_url"])
    ok = api.login(cfg["auth"]["username"], cfg["auth"]["password"], cfg["auth"].get("fingerprint", "09a160f689f48ed27b96d6f2fbbeec79"))
    if not ok:
        raise ValueError("Gagal login ke SiPENDEKAR. Periksa NIP/Password.")
    return api, cfg

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SiPENDEKAR Auto-Filler Dashboard</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(22, 30, 49, 0.85);
      --card-border: rgba(255, 255, 255, 0.08);
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --success: #10b981;
      --success-bg: rgba(16, 185, 129, 0.15);
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.15);
      --warning: #f59e0b;
      --warning-bg: rgba(245, 158, 11, 0.15);
      --radius: 14px;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
    body { background-color: var(--bg); color: var(--text); min-height: 100vh; padding: 24px; }

    .container { max-width: 1200px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 16px; }
    .brand { display: flex; align-items: center; gap: 14px; }
    .badge-icon { background: linear-gradient(135deg, #3b82f6, #8b5cf6); padding: 10px; border-radius: 12px; font-weight: 800; font-size: 20px; }
    .title-area h1 { font-size: 22px; font-weight: 700; color: #fff; }
    .title-area p { font-size: 13px; color: var(--text-muted); }

    .action-bar { display: flex; gap: 12px; align-items: center; }
    .btn { padding: 10px 18px; border-radius: 10px; font-weight: 600; font-size: 13px; cursor: pointer; border: none; transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px; }
    .btn-primary { background: linear-gradient(135deg, #3b82f6, #2563eb); color: #fff; box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4); }
    .btn-primary:hover { opacity: 0.95; transform: translateY(-1px); }
    .btn-success { background: linear-gradient(135deg, #10b981, #059669); color: #fff; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4); }
    .btn-success:hover { opacity: 0.95; transform: translateY(-1px); }
    .btn-outline { background: transparent; border: 1px solid var(--card-border); color: var(--text); }
    .btn-outline:hover { background: rgba(255, 255, 255, 0.05); }

    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .stat-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 18px; backdrop-filter: blur(10px); }
    .stat-card .label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }
    .stat-card .val { font-size: 24px; font-weight: 800; }

    .main-grid { display: grid; grid-template-columns: 1fr 340px; gap: 24px; }
    @media(max-width: 900px) { .main-grid { grid-template-columns: 1fr; } }

    .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 20px; backdrop-filter: blur(10px); }
    .card-title { font-size: 16px; font-weight: 700; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }

    .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; }
    .cal-header { font-size: 11px; font-weight: 700; text-align: center; color: var(--text-muted); padding: 6px 0; }
    .cal-cell {
      border: 1px solid var(--card-border); border-radius: 10px; padding: 10px 8px; min-height: 85px;
      display: flex; flex-direction: column; justify-content: space-between; cursor: pointer; transition: all 0.2s;
      background: rgba(255, 255, 255, 0.02);
    }
    .cal-cell:hover { transform: translateY(-2px); border-color: rgba(255, 255, 255, 0.2); }
    .cal-cell.terisi { background: var(--success-bg); border-color: rgba(16, 185, 129, 0.4); }
    .cal-cell.kosong-bisa { background: var(--danger-bg); border-color: rgba(239, 68, 68, 0.5); }
    .cal-cell.kosong-lewat { background: var(--warning-bg); border-color: rgba(245, 158, 11, 0.3); opacity: 0.7; }
    .cal-cell.weekend { opacity: 0.4; cursor: default; }
    .cal-cell.future { opacity: 0.3; cursor: default; }

    .cell-top { display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-weight: 700; }
    .cell-status { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 6px; margin-top: 4px; display: inline-block; }
    .badge-terisi { background: var(--success); color: #000; }
    .badge-kosong { background: var(--danger); color: #fff; }
    .badge-lewat { background: var(--warning); color: #000; }

    .template-box { margin-bottom: 16px; }
    .template-select { width: 100%; padding: 10px; border-radius: 8px; background: rgba(0,0,0,0.4); border: 1px solid var(--card-border); color: #fff; font-size: 13px; outline: none; }
    .template-desc { font-size: 12px; color: var(--text-muted); margin-top: 8px; line-height: 1.4; }

    /* Modal */
    .modal { display: none; position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(5px); z-index: 1000; align-items: center; justify-content: center; padding: 16px; }
    .modal.active { display: flex; }
    .modal-content { background: #161e31; border: 1px solid var(--card-border); border-radius: var(--radius); width: 100%; max-width: 520px; padding: 24px; }
    .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .close-btn { background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer; }

    .toast { position: fixed; bottom: 24px; right: 24px; padding: 14px 20px; border-radius: 10px; font-size: 13px; font-weight: 600; display: none; z-index: 2000; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
    .toast.show { display: block; animation: slideIn 0.3s forwards; }
    .toast.success { background: #10b981; color: #fff; }
    .toast.error { background: #ef4444; color: #fff; }

    @keyframes slideIn { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="brand">
        <div class="badge-icon">⚡</div>
        <div class="title-area">
          <h1>SiPENDEKAR Bot Dashboard</h1>
          <p>Otomatisasi Laporan Dedikasi & Kinerja Aparatur Kabupaten Tangerang</p>
        </div>
      </div>
      <div class="action-bar">
        <button class="btn btn-outline" onclick="loadData()">🔄 Refresh</button>
        <button class="btn btn-success" onclick="autoFillEmpty()">⚡ Auto-Isi Hari Kosong (H-7)</button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">NIP Terautentikasi</div>
        <div class="val" id="stat-nip">-</div>
      </div>
      <div class="stat-card">
        <div class="label">Hari Kerja Lewat</div>
        <div class="val" id="stat-total-hari">-</div>
      </div>
      <div class="stat-card">
        <div class="label">Hari Terisi</div>
        <div class="val" style="color: var(--success);" id="stat-terisi">-</div>
      </div>
      <div class="stat-card">
        <div class="label">Hari Kosong (Bisa Diisi)</div>
        <div class="val" style="color: var(--danger);" id="stat-kosong">-</div>
      </div>
    </div>

    <div class="main-grid">
      <div class="card">
        <div class="card-title">
          <span id="cal-title">Kalender Aktivitas</span>
          <span style="font-size: 12px; color: var(--text-muted);">Klik pada tanggal untuk melihat detail / isi</span>
        </div>
        <div class="calendar-grid" id="cal-grid">
          <!-- Calendar cells injected by JS -->
        </div>
      </div>

      <div>
        <div class="card" style="margin-bottom: 20px;">
          <div class="card-title">Template Laporan</div>
          <div class="template-box">
            <select class="template-select" id="template-select" onchange="onTemplateChange()">
              <!-- Options populated by JS -->
            </select>
            <div class="template-desc" id="template-desc">Pilih template aktivitas yang akan digunakan saat pengisian otomatis.</div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">Pencarian Katalog Kegiatan</div>
          <input type="text" id="catalog-search" placeholder="Cari kegiatan (misal: jaringan, rapat)..." class="template-select" style="margin-bottom: 10px;" onkeyup="if(event.key==='Enter') searchCatalog()">
          <button class="btn btn-outline" style="width: 100%; justify-content: center;" onclick="searchCatalog()">🔍 Cari Katalog</button>
          <div id="catalog-results" style="margin-top: 14px; max-height: 250px; overflow-y: auto; font-size: 12px;"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- Detail Modal -->
  <div class="modal" id="modal-detail">
    <div class="modal-content">
      <div class="modal-header">
        <h3 id="modal-tgl-title">Detail Aktivitas</h3>
        <button class="close-btn" onclick="closeModal()">&times;</button>
      </div>
      <div id="modal-body" style="font-size: 13px; line-height: 1.6; margin-bottom: 20px;">
        <!-- Injected by JS -->
      </div>
      <div style="display: flex; gap: 10px; justify-content: flex-end;">
        <button class="btn btn-outline" onclick="closeModal()">Tutup</button>
        <button class="btn btn-primary" id="modal-isi-btn" onclick="isiTanggalModal()">Isi dengan Template Aktif</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    let globalData = null;
    let selectedDate = null;

    function showToast(msg, isSuccess = true) {
      const t = document.getElementById("toast");
      t.className = `toast show ${isSuccess ? 'success' : 'error'}`;
      t.innerText = msg;
      setTimeout(() => { t.className = "toast"; }, 4000);
    }

    async function loadData() {
      try {
        const res = await fetch("/api/status");
        const data = await res.json();
        if(!data.success) {
          showToast(data.error || "Gagal memuat status", false);
          return;
        }
        globalData = data;
        renderDashboard(data);
      } catch(e) {
        showToast("Koneksi gagal: " + e.message, false);
      }
    }

    function renderDashboard(data) {
      document.getElementById("stat-nip").innerText = data.auth.username;
      document.getElementById("stat-total-hari").innerText = data.summary.total_hari_kerja;
      document.getElementById("stat-terisi").innerText = data.summary.terisi;
      document.getElementById("stat-kosong").innerText = data.summary.kosong_bisa;
      document.getElementById("cal-title").innerText = `Kalender Aktivitas - ${data.bulan_nama} ${data.tahun}`;

      // Populate templates
      const sel = document.getElementById("template-select");
      sel.innerHTML = "";
      for (const [k, v] of Object.entries(data.templates)) {
        const opt = document.createElement("option");
        opt.value = k;
        opt.innerText = v.nama_template;
        if(k === data.active_template) opt.selected = true;
        sel.appendChild(opt);
      }
      onTemplateChange();

      // Render calendar
      const grid = document.getElementById("cal-grid");
      grid.innerHTML = "";
      const days = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];
      days.forEach(d => {
        const h = document.createElement("div");
        h.className = "cal-header";
        h.innerText = d;
        grid.appendChild(h);
      });

      // Align first day offset
      const firstDayOffset = data.first_day_weekday; // 0=Mon, 6=Sun
      for(let i=0; i<firstDayOffset; i++) {
        const emptyCell = document.createElement("div");
        grid.appendChild(emptyCell);
      }

      data.calendar_days.forEach(d => {
        const cell = document.createElement("div");
        cell.className = `cal-cell ${d.cell_class}`;
        cell.onclick = () => openDayDetail(d.tanggal, d);

        let badgeHtml = "";
        if(d.is_future) {
          badgeHtml = `<span class="cell-status" style="color: #64748b;">Masa Depan</span>`;
        } else if(d.is_weekend) {
          badgeHtml = `<span class="cell-status" style="color: #64748b;">Akhir Pekan</span>`;
        } else if(d.terisi) {
          badgeHtml = `<span class="cell-status badge-terisi">${d.total_menit}m</span>`;
        } else if(d.bisa_diisi) {
          badgeHtml = `<span class="cell-status badge-kosong">Kosong</span>`;
        } else {
          badgeHtml = `<span class="cell-status badge-lewat">Lewat H-7</span>`;
        }

        cell.innerHTML = `
          <div class="cell-top">
            <span>${d.day_num}</span>
            ${d.terisi ? '✅' : (d.bisa_diisi ? '⚠️' : '')}
          </div>
          <div>${badgeHtml}</div>
        `;
        grid.appendChild(cell);
      });
    }

    function onTemplateChange() {
      const k = document.getElementById("template-select").value;
      if(globalData && globalData.templates[k]) {
        document.getElementById("template-desc").innerText = globalData.templates[k].deskripsi;
      }
    }

    async function openDayDetail(tgl, dayInfo) {
      selectedDate = tgl;
      document.getElementById("modal-tgl-title").innerText = `Aktivitas: ${tgl} (${dayInfo.hari_nama})`;
      const mb = document.getElementById("modal-body");
      mb.innerHTML = "Memuat data dari SiPENDEKAR...";
      document.getElementById("modal-detail").classList.add("active");

      try {
        const res = await fetch(`/api/day/${tgl}`);
        const data = await res.json();
        if(!data.success) {
          mb.innerHTML = `<span style="color:red;">${data.error}</span>`;
          return;
        }

        if(data.detail.length === 0) {
          mb.innerHTML = `
            <div style="background: rgba(239,68,68,0.1); padding: 12px; border-radius: 8px; border: 1px solid rgba(239,68,68,0.3); margin-bottom: 12px;">
              <strong>Hari Ini Belum Ada Laporan!</strong><br>
              Status: ${dayInfo.bisa_diisi ? '<span style="color:#10b981;">Bisa diisi sekarang</span>' : '<span style="color:#f59e0b;">Terkunci H-7</span>'}
            </div>
          `;
          document.getElementById("modal-isi-btn").style.display = dayInfo.bisa_diisi ? "inline-flex" : "none";
        } else {
          let listHtml = `<strong>Total: ${data.total_menit} menit</strong><br><br>`;
          data.detail.forEach((it, idx) => {
            listHtml += `
              <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <strong>${it.jam_mulai} - ${it.jam_selesai}</strong>: ${it.nama_aktifitas}<br>
                  <small style="color:#94a3b8;">${it.keterangan}</small>
                </div>
                <button class="btn btn-outline" style="color:#ef4444; border-color:#ef4444; padding: 4px 8px; font-size: 11px;" onclick="deleteAct(${it.id})">Hapus</button>
              </div>
            `;
          });
          mb.innerHTML = listHtml;
          document.getElementById("modal-isi-btn").style.display = "inline-flex";
        }
      } catch(e) {
        mb.innerHTML = "Error: " + e.message;
      }
    }

    function closeModal() {
      document.getElementById("modal-detail").classList.remove("active");
    }

    async function isiTanggalModal() {
      if(!selectedDate) return;
      const tkey = document.getElementById("template-select").value;
      if(!confirm(`Isi laporan tanggal ${selectedDate} menggunakan template ini?`)) return;

      showToast("Sedang mengirim aktivitas...", true);
      const res = await fetch("/api/fill-day", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tanggal: selectedDate, template_key: tkey })
      });
      const data = await res.json();
      if(data.success) {
        showToast("Berhasil mengisi aktivitas!", true);
        closeModal();
        loadData();
      } else {
        showToast("Gagal: " + data.error, false);
      }
    }

    async function autoFillEmpty() {
      const tkey = document.getElementById("template-select").value;
      if(!confirm(`Apakah Anda yakin ingin mengisi semua hari kerja kosong dalam periode H-7 dengan template ini?`)) return;

      showToast("Sedang memproses auto-fill...", true);
      const res = await fetch("/api/auto-fill-empty", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_key: tkey })
      });
      const data = await res.json();
      if(data.success) {
        showToast(`Selesai! Berhasil mengisi ${data.filled_count} hari.`, true);
        loadData();
      } else {
        showToast("Gagal: " + data.error, false);
      }
    }

    async function deleteAct(id) {
      if(!confirm(`Hapus aktivitas ID ${id}?`)) return;
      const res = await fetch("/api/delete-activity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id })
      });
      const data = await res.json();
      if(data.success) {
        showToast("Aktivitas berhasil dihapus", true);
        closeModal();
        loadData();
      } else {
        showToast("Gagal menghapus: " + data.error, false);
      }
    }

    async function searchCatalog() {
      const kw = document.getElementById("catalog-search").value.trim();
      if(!kw) return;
      const container = document.getElementById("catalog-results");
      container.innerHTML = "Mencari...";
      const res = await fetch(`/api/search-catalog?q=${encodeURIComponent(kw)}`);
      const data = await res.json();
      if(!data.success || data.results.length === 0) {
        container.innerHTML = "<span style='color:#94a3b8;'>Tidak ada kegiatan ditemukan.</span>";
        return;
      }
      let html = "";
      data.results.forEach(it => {
        html += `
          <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 6px; margin-bottom: 6px;">
            <strong>${it.kode_aktifitas}</strong> - ${it.nama_aktifitas}<br>
            <small style="color:#94a3b8;">${it.waktu}m | ${it.satuan_output}</small>
          </div>
        `;
      });
      container.innerHTML = html;
    }

    window.onload = loadData;
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/status")
def api_status():
    try:
        api, cfg = get_api_client()
        td = date.today()
        tahun = td.year
        bulan = td.month
        max_hmin = cfg.get("settings", {}).get("max_hmin_days", 7)
        hmin_date = td - timedelta(days=max_hmin)

        d_start = date(tahun, bulan, 1)
        if bulan == 12:
            d_end = date(tahun + 1, 1, 1) - timedelta(days=1)
        else:
            d_end = date(tahun, bulan + 1, 1) - timedelta(days=1)

        nama_bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"][bulan]
        first_day_weekday = d_start.weekday() # 0 = Monday

        curr = d_start
        cal_days = []
        total_kerja = 0
        terisi_count = 0
        kosong_bisa_count = 0

        while curr <= d_end:
            tgl_str = curr.strftime("%Y-%m-%d")
            is_weekend = curr.weekday() in (5, 6)
            is_future = curr > td
            in_h7 = curr >= hmin_date

            terisi = False
            total_menit = 0
            if not is_weekend and not is_future:
                total_kerja += 1
                total_menit, detail = api.get_total_menit_harian(tgl_str)
                if len(detail) > 0:
                    terisi = True
                    terisi_count += 1
                else:
                    if in_h7:
                        kosong_bisa_count += 1

            cell_class = ""
            if is_future:
                cell_class = "future"
            elif is_weekend:
                cell_class = "weekend"
            elif terisi:
                cell_class = "terisi"
            elif in_h7:
                cell_class = "kosong-bisa"
            else:
                cell_class = "kosong-lewat"

            hari_id = {
                "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
                "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
            }.get(curr.strftime("%A"), curr.strftime("%A"))

            cal_days.append({
                "tanggal": tgl_str,
                "day_num": curr.day,
                "hari_nama": hari_id,
                "is_weekend": is_weekend,
                "is_future": is_future,
                "terisi": terisi,
                "total_menit": total_menit,
                "bisa_diisi": (not is_weekend and not is_future and not terisi and in_h7),
                "cell_class": cell_class
            })
            curr += timedelta(days=1)

        return jsonify({
            "success": True,
            "auth": {"username": cfg["auth"]["username"]},
            "tahun": tahun,
            "bulan": bulan,
            "bulan_nama": nama_bulan,
            "first_day_weekday": first_day_weekday,
            "templates": cfg.get("templates", {}),
            "active_template": cfg.get("active_template"),
            "summary": {
                "total_hari_kerja": total_kerja,
                "terisi": terisi_count,
                "kosong_bisa": kosong_bisa_count
            },
            "calendar_days": cal_days
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/day/<tanggal>")
def api_day_detail(tanggal):
    try:
        api, _ = get_api_client()
        total_menit, detail = api.get_total_menit_harian(tanggal)
        return jsonify({
            "success": True,
            "tanggal": tanggal,
            "total_menit": total_menit,
            "detail": detail
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/fill-day", methods=["POST"])
def api_fill_day():
    try:
        data = request.json or {}
        tanggal = data.get("tanggal")
        template_key = data.get("template_key")
        if not tanggal:
            return jsonify({"success": False, "error": "Tanggal wajib diisi"}), 400

        api, cfg = get_api_client()
        tmpl = cfg.get("templates", {}).get(template_key or cfg.get("active_template"))
        if not tmpl:
            return jsonify({"success": False, "error": "Template tidak ditemukan"}), 400

        items = tmpl.get("items", [])
        for it in items:
            res = api.isi_aktivitas(
                tanggal=tanggal,
                kode_aktifitas=it["kode_aktifitas"],
                volume=it.get("volume", 1),
                keterangan=it.get("keterangan", "-"),
                sasaran_kerja_id=it["sasaran_kerja_id"],
                jam_mulai=it["jam_mulai"],
                menit_mulai=it["menit_mulai"],
                jam_selesai=it["jam_selesai"],
                menit_selesai=it["menit_selesai"],
                jenis=it.get("jenis", "kinerja")
            )
            if not (res.get("success") is True or res.get("success") == 1):
                return jsonify({"success": False, "error": res.get("error", "Gagal menyimpan")})

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/auto-fill-empty", methods=["POST"])
def api_auto_fill_empty():
    try:
        data = request.json or {}
        template_key = data.get("template_key")

        api, cfg = get_api_client()
        tmpl = cfg.get("templates", {}).get(template_key or cfg.get("active_template"))
        if not tmpl:
            return jsonify({"success": False, "error": "Template tidak ditemukan"}), 400

        td = date.today()
        max_hmin = cfg.get("settings", {}).get("max_hmin_days", 7)
        hmin_date = td - timedelta(days=max_hmin)

        kosong = api.cari_hari_kosong(hmin_date, td, skip_weekends=cfg.get("settings", {}).get("skip_weekends", True))
        filled_count = 0

        for k in kosong:
            tgl = k["tanggal"]
            for it in tmpl.get("items", []):
                api.isi_aktivitas(
                    tanggal=tgl,
                    kode_aktifitas=it["kode_aktifitas"],
                    volume=it.get("volume", 1),
                    keterangan=it.get("keterangan", "-"),
                    sasaran_kerja_id=it["sasaran_kerja_id"],
                    jam_mulai=it["jam_mulai"],
                    menit_mulai=it["menit_mulai"],
                    jam_selesai=it["jam_selesai"],
                    menit_selesai=it["menit_selesai"],
                    jenis=it.get("jenis", "kinerja")
                )
            filled_count += 1

        return jsonify({"success": True, "filled_count": filled_count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete-activity", methods=["POST"])
def api_delete_act():
    try:
        data = request.json or {}
        id_act = data.get("id")
        if not id_act:
            return jsonify({"success": False, "error": "ID wajib diisi"}), 400
        api, _ = get_api_client()
        res = api.hapus_aktivitas(id_act)
        return jsonify({"success": True, "result": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/search-catalog")
def api_search_catalog():
    try:
        q = request.args.get("q", "")
        api, _ = get_api_client()
        results = api.search_catalog(q, limit=15)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    print("Menjalankan SiPENDEKAR Web Dashboard di http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
