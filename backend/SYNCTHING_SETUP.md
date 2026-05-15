# Syncthing Kurulum — Jarvan İki Cihaz Arası Hafıza ve Dosya Transferi

## Mimari

```
Mac (Master)                              Windows (İkincil)
────────────────────────────────          ──────────────────────────────────
/Users/burakemreerdemci/JarvanShare/  <─> C:\JarvanShare\
  memory/chroma/                            memory/chroma/        (okur)
  memory/memory.json                        memory/memory.json    (okur)
  obsidian/JARVAN/                          obsidian/JARVAN/      (okur)
  transfer/to_mac/                          transfer/to_mac/      (buraya gönderir)
  transfer/to_windows/                      transfer/to_windows/  (buradan alır)
  transfer/manifests/                       transfer/manifests/
```

Mac hafızayı yazar, Windows sadece okur. Dosya transferinde her cihaz diğerinin inbox'ına yazar.

---

## 1. Syncthing Kur

**Mac:**
```bash
brew install syncthing
brew services start syncthing
```

**Windows:**
- [syncthing.net/downloads](https://syncthing.net/downloads/) → Windows Installer indir, kur
- Kurulum sırasında "Start on Login" seç (sistem açılınca otomatik başlar)

---

## 2. Ortak Klasörü Ekle

Her iki cihazda tarayıcıdan `http://127.0.0.1:8384` aç.

**Mac'te (Add Folder):**
- Folder Path: `/Users/burakemreerdemci/JarvanShare`
- Folder ID: `jarvan-share`
- Sharing sekmesi → Windows cihazının Device ID'sini ekle

**Windows'ta:**
- Mac'ten gelen paylaşım isteğini kabul et
- Yerel yol: `C:\JarvanShare`

---

## 3. Mac'te Dosyaları Ortak Klasöre Taşı

Backend kapalıyken yap:

```bash
# Obsidian vault'u taşı
mv /Users/burakemreerdemci/Documents/JarvanVault/JARVAN \
   /Users/burakemreerdemci/JarvanShare/obsidian/JARVAN

# ChromaDB verisini kopyala
cp -r /Users/burakemreerdemci/Documents/JARVAN/backend/data/chroma \
      /Users/burakemreerdemci/JarvanShare/memory/chroma

cp /Users/burakemreerdemci/Documents/JARVAN/backend/data/memory.json \
   /Users/burakemreerdemci/JarvanShare/memory/memory.json
```

---

## 4. .env Dosyalarını Güncelle

**Mac `.env`:**
```env
OBSIDIAN_VAULT_PATH=/Users/burakemreerdemci/JarvanShare/obsidian/JARVAN
CHROMA_DB_PATH=/Users/burakemreerdemci/JarvanShare/memory/chroma
MEMORY_JSON_PATH=/Users/burakemreerdemci/JarvanShare/memory/memory.json
JARVAN_SHARE_PATH=/Users/burakemreerdemci/JarvanShare
```

**Windows `.env` (`C:\Users\burcu\Downloads\JARVAN-main\backend\.env`):**
```env
OBSIDIAN_VAULT_PATH=C:\JarvanShare\obsidian\JARVAN
CHROMA_DB_PATH=C:\JarvanShare\memory\chroma
MEMORY_JSON_PATH=C:\JarvanShare\memory\memory.json
JARVAN_SHARE_PATH=C:\JarvanShare
MEMORY_READ_ONLY=1
```

---

## 5. Obsidian'ı Yeni Vault Yoluna Bağla

Mac ve Windows'ta Obsidian'ı aç → **Open folder as vault** seç:
- Mac: `/Users/burakemreerdemci/JarvanShare/obsidian/JARVAN`
- Windows: `C:\JarvanShare\obsidian\JARVAN`

---

## Kullanım

Jarvan'a sesle:
- **"Şu dosyayı windows'a gönder"** → dosya `C:\JarvanShare\transfer\to_windows\`'a düşer, Windows Jarvan sesli bildirir
- **"Mac'imdeki raporu buraya gönder"** → Mac Jarvan dosyayı `to_windows/` klasörüne koyar
- **"Gelen kutumda ne var?"** → `get_transfer_status` listeler
- **"Hafızamı yedekle"** → Google Drive'a anlık yedek alır (Mac'te)

## Uzaktan Erişim (Dışarıdayken)

Syncthing relay sunucuları sayesinde aynı ağda olmak gerekmez. Her iki cihaz internete bağlıysa otomatik senkronize eder. End-to-end şifreli, hesap gerektirmez.
