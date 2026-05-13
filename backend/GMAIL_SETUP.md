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

## Çoklu Hesap

Jarvan iki Gmail hesabını ayrı token dosyalarıyla yönetir:

- `burcu`, `burcuemre`, `burcuemre0` -> `burcuemre0@gmail.com`
- `erdem`, `burak`, `erdemciburakemre` -> `erdemciburakemre@gmail.com`

Sesle hesap değiştirmek için:

- "burcuemre hesabına geç"
- "erdemciburakemre hesabına geç"

İlk geçişte o hesap için Google izin penceresi açılır. Sonrasında ilgili token dosyası saklanır ve tekrar sormaz.
