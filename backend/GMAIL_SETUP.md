# Gmail Setup

Jarvan mail okumak ve göndermek için Gmail API OAuth kullanır. Browser-use veya debug tarayıcı profiline bağlı değildir.

Gerekli gizli dosyalar:

- `backend/credentials.json`: Google Cloud OAuth client dosyası.
- `backend/token.json`: İlk izin verdikten sonra otomatik oluşur.

İki bilgisayar için ayrı dosya kullanmak istersen `.env` içine şunları yazabilirsin:

```env
GMAIL_CREDENTIALS_PATH=C:\Users\burcu\Downloads\JARVAN-main\backend\credentials.json
GMAIL_TOKEN_PATH=C:\Users\burcu\Downloads\JARVAN-main\backend\token.json
```

İlk çalıştırmada Google izin penceresi açılır. Jarvan şu izinleri ister:

- `gmail.send`: Mail göndermek için.
- `gmail.readonly`: Mailleri kontrol edip özetlemek için.

`credentials.json` ve `token.json` repo'ya eklenmez; `.gitignore` içinde kalmalıdır.

## Google Drive (Hafıza Yedeği)

Jarvan her gece 23:00'de hafızayı Drive'a yedekler. Bunun için **aynı** `credentials.json` kullanılır ama Drive API'nin Google Cloud Console'da aktif olması gerekir.

1. [console.cloud.google.com](https://console.cloud.google.com) → Projen → **APIs & Services → Library**
2. "Google Drive API" → **Enable**
3. Jarvan'a ilk kez "hafızamı yedekle" dediğinde `token_drive.json` için ayrı bir izin penceresi açılır (tek seferlik, sadece Mac'te).

Yedekler Drive'da `jarvan_backups/` klasöründe saklanır, son 7 gün korunur.

## Çoklu Hesap

Jarvan iki Gmail hesabını ayrı token dosyalarıyla yönetir:

- `burcu`, `burcuemre`, `burcuemre0` -> `burcuemre0@gmail.com`
- `erdem`, `burak`, `erdemciburakemre` -> `erdemciburakemre@gmail.com`

Sesle hesap değiştirmek için:

- "burcuemre hesabına geç"
- "erdemciburakemre hesabına geç"

İlk geçişte o hesap için Google izin penceresi açılır. Sonrasında ilgili token dosyası saklanır ve tekrar sormaz.
