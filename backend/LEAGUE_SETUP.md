# League of Legends Setup

Jarvan League of Legends'i özel Windows tool'u ile açar:

- Riot/LoL launcher yolunu otomatik bulmaya çalışır.
- Riot Client Services için `--launch-product=league_of_legends --launch-patchline=live` kullanır.
- League client ana ekranı gelene kadar bekler.
- Login gerekirse `.env` içindeki bilgilerle bir kez denemeye çalışır.

Opsiyonel `.env` değerleri:

```env
RIOT_DEFAULT_ACCOUNT=fjkis

RIOT_FJKIS_USERNAME=...
RIOT_FJKIS_PASSWORD=...

RIOT_KATILBRONZ_USERNAME=...
RIOT_KATILBRONZ_PASSWORD=...

RIOT_ABUBAKAR_USERNAME=...
RIOT_ABUBAKAR_PASSWORD=...

# Otomatik path bulamazsa:
RIOT_CLIENT_PATH=C:\Riot Games\Riot Client\RiotClientServices.exe
LOL_CLIENT_PATH=C:\Riot Games\League of Legends\LeagueClient.exe
```

Desteklenen sesli aliaslar:

- `fjkis`, `fjkis123`, `ana`, `ana hesap`
- `katilbronz`, `ikinci`
- `abubakar`, `üçüncü`

Notlar:

- Şifreyi koda yazma; sadece `.env` içinde tut.
- Riot Client sık UI değiştirdiği için login otomasyonu ilk sürümde temkinlidir.
- En sağlam kullanım: Riot hesabında "beni hatırla" açık olsun. O zaman Jarvan çoğunlukla sadece client'ı hazır hale getirir.
