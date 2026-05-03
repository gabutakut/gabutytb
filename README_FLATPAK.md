# Gabut YTB — Panduan Build Flatpak

## Struktur Proyek

```
gabutytb/
├── gabutytb.py                                  ← source utama
├── gabutytb.in                                  ← launcher wrapper template
├── meson.build                                  ← build system
├── com.github.gabutakut.gabutytb.json           ← Flatpak manifest
└── data/
    ├── com.github.gabutakut.gabutytb.desktop    ← desktop entry
    ├── com.github.gabutakut.gabutytb.metainfo.xml
    └── icons/
        └── com.github.gabutakut.gabutytb.svg
```

---

## Dependencies Runtime (otomatis via Flatpak manifest)

| Paket | Keterangan |
|-------|------------|
| `org.gnome.Platform//47` | GTK4, GLib, libadwaita, PyGObject |
| `org.gnome.Sdk//47` | Build tools, Python 3.12 |
| `yt-dlp` | Diinstall via pip ke dalam Flatpak sandbox |

> **Tidak perlu install yt-dlp secara manual** — sudah dibundel di dalam Flatpak.

---

## Build & Install

### 1. Install flatpak-builder
```bash
sudo apt install flatpak-builder        # Debian/Ubuntu
sudo dnf install flatpak-builder        # Fedora
```

### 2. Tambah GNOME remote
```bash
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47
```

### 3. Update SHA256 yt-dlp di manifest
Ambil SHA256 dari wheel terbaru yt-dlp:
```bash
pip download yt-dlp --no-deps -d /tmp/whl
sha256sum /tmp/whl/yt_dlp-*.whl
```
Lalu update field `sha256` di `com.github.gabutakut.gabutytb.json`.

### 4. Build Flatpak
```bash
flatpak-builder --force-clean build-dir com.github.gabutakut.gabutytb.json
```

### 5. Test lokal
```bash
flatpak-builder --run build-dir com.github.gabutakut.gabutytb.json gabutytb
```

### 6. Install ke sistem lokal
```bash
flatpak-builder --user --install --force-clean build-dir com.github.gabutakut.gabutytb.json
flatpak run com.github.gabutakut.gabutytb
```

### 7. Export ke repo (opsional, untuk distribusi)
```bash
flatpak-builder --repo=repo --force-clean build-dir com.github.gabutakut.gabutytb.json
flatpak --user remote-add --no-gpg-verify gabutytb-repo repo
flatpak --user install gabutytb-repo com.github.gabutakut.gabutytb
```

---

## Build tanpa Flatpak (meson langsung)

```bash
meson setup builddir --prefix=/usr
ninja -C builddir
sudo ninja -C builddir install
```

---

## Network Permission

App ini membutuhkan `--share=network` karena:
- Server HTTP lokal (`0.0.0.0:PORT`) untuk menerima request JSON-RPC
- yt-dlp mengakses internet untuk fetch info video YouTube
