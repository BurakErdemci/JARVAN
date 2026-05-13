"""Tool declarations, implementations, and hint strings for JARVAN."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.app_control import open_app, close_app
from tools.whatsapp import send_whatsapp
from tools.browser import open_url
from tools.mail import send_mail, check_mail, read_mail_body
from tools.weather import get_weather
from tools.developer import create_folder

# ─── Konfigürasyon ──────────────────────────────────────────────────

FUNCTION_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Kullanıcının bilgisayarında bir uygulamayı veya oyunu açar. Örnek: 'not defteri aç', 'chrome aç', 'CS2 aç'.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Açılacak uygulamanın adı (not defteri, chrome, vscode, cs2, spotify vb.)",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "close_app",
        "description": "Açık bir uygulamayı kapatır. Örnek: 'chrome kapat', 'spotify kapat'.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Kapatılacak uygulamanın adı",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_weather",
        "description": "Herhangi bir şehrin ANLIK ve YARINKİ hava durumunu (derecesiyle birlikte) SANIYELER İÇİNDE getirir. Kullanıcı hava durumu sorduğunda (eskişehir hava durumu vs) web aramasına yönelme, KESİNLİKLE BU ARACI ZORUNLU KULLAN.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Şehir veya bölge adı (örn: Eskişehir, İstanbul)",
                },
            },
            "required": ["location"],
        },
    },
    {
        "name": "open_url",
        "description": "Tarayıcıda verilen URL'yi açar. Tam URL (https://...) ya da domain (metacritic.com/...) verilebilir. Spesifik sayfa/oyun/film isteğinde bu aracı kullan.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Açılacak tam URL veya domain (örn: https://www.metacritic.com/game/crimson-desert)",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "see_screen",
        "description": (
            "Kullanıcının o ANKİ bilgisayar ekranını çeker ve ne gördüğünü Türkçe 2-3 cümle olarak döner. "
            "Kullanıcı 'ekrana bak', 'şuna bak', 'görüyor musun', 'ekranda ne var', 'şu sayfa' gibi ekranla ilgili bir şey sorduğunda ZORUNLU bu aracı çağır. "
            "Tahmin yürütme, asla ekranda ne olduğunu uydurma — bu araç gerçek ekran görüntüsünü analiz eder ve sana metin olarak döner. "
            "Aracı çağırmadan ekran hakkında konuşma."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "send_mail",
        "description": (
            "Gmail compose ekranını prefilled açar. `auto_send=true` ise tarayıcı yüklenince otomatik gönderir (Cmd+Enter), "
            "`auto_send=false` ise sadece doldurup açık bırakır (kullanıcı manuel gönderir). "
            "Kullanıcı 'gönder', 'at', 'yolla' gibi net gönderim sözcüğü kullanırsa auto_send=true; "
            "'hazırla', 'göster', 'aç', 'doldur' gibi pasif istek varsa auto_send=false."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Alıcı — tam e-posta adresi VEYA rehberdeki isim ('burak', 'burcu', 'kendime', 'kurumsal', 'yan hesap'). Sistem ismi otomatik adrese çevirir."},
                "subject": {"type": "string", "description": "Mail konusu"},
                "body": {"type": "string", "description": "Mail gövdesi (düz metin)"},
                "auto_send": {"type": "boolean", "description": "True ise otomatik gönderir, False ise manuel gönderim için açık bırakır."},
            },
            "required": ["to", "subject", "body", "auto_send"],
        },
    },
    {
        "name": "check_mail",
        "description": (
            "Gmail'deki son mailleri listeler (gönderen, konu, tarih, kısa önizleme + mail id). "
            "Kullanıcı 'son mailim ne', 'okumamış mailler', 'X kişisinden mail var mı', 'bugün gelen mailler' "
            "gibi şeyler sorduğunda kullan. KESİNLİKLE computer_use veya browser çağırma — bu tool Gmail API kullanır, anında döner. "
            "ÖNEMLİ: Liste döner ama tam mail içeriği DÖNMEZ — sadece snippet (kısa özet). "
            "Kullanıcı 'şu maili tam oku', 'içeriği ne', 'detayını gör' derse `read_mail_body` ile mail id'sini geçirip tam içerik al. "
            "Gmail arama syntax örnekleri: 'from:burcu', 'subject:fatura', 'after:2026/01/01', 'is:unread', 'has:attachment'. "
            "Birden fazla kriter: 'from:burcu is:unread'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search syntax (boş = tüm mailler). Örnek: 'from:burcu subject:fatura', 'is:unread after:2026/05/01'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Kaç mail listelensin (1-10, default 5)"
                },
                "unread_only": {
                    "type": "boolean",
                    "description": "Sadece okumamış mailler için true"
                },
                "account": {
                    "type": "string",
                    "description": "Hangi hesap? 'burcu' / 'erdem'. Boş = default hesap (erdem)."
                }
            }
        }
    },
    {
        "name": "read_mail_body",
        "description": (
            "Belirli bir mailin tam gövdesini okur. `check_mail`'den dönen mail id'si ile çağırılır. "
            "Kullanıcı 'şu maili tam oku', 'içeriği ne', 'detayını söyle' dediğinde kullan. "
            "ÖNEMLİ: Mail id'sini önce `check_mail` ile almış olmalısın — uydurma."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "check_mail'in messages[].id alanından gelen mail id'si"
                },
                "account": {
                    "type": "string",
                    "description": "Hangi hesaptan okunacak (boş = aktif hesap)"
                }
            },
            "required": ["message_id"]
        }
    },

    {
        "name": "send_whatsapp",
        "description": (
            "Kullanıcının WhatsApp'ından mesaj gönderir. `phone` alanına tam numara (ülke koduyla, + olmadan) VEYA rehberdeki isim "
            "('kendime', 'burak' vb.) verilebilir. Sistem ismi numaraya otomatik çevirir. "
            "Rehberde olmayan bir isim verilirse tool `ok: false` ile hata döner — o durumda kullanıcıdan numarayı iste, "
            "UYDURMA veya kendine gönderme. phone boş bırakılırsa .env'deki MY_WHATSAPP'a (kullanıcının kendi numarasına) gider."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Gönderilecek mesaj metni",
                },
                "phone": {
                    "type": "string",
                    "description": "Hedef: rehberdeki isim (ör. 'cengiz') VEYA tam numara (ülke koduyla, + olmadan, ör. '905321234567'). Boş = kullanıcının kendisi.",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "calculator_compute",
        "description": (
            "Hesap makinesini deterministic olarak açar ve basit bir işlemi yapar. "
            "Örnek: 'hesap makinesinde 7+7 yap', 'calculator ile 145*32 hesapla'. "
            "Mümkün olduğunda bunu `computer_use` yerine tercih et."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Yapılacak işlem cümlesi veya ifade (örn: '7+7', 'hesap makinesinde 12/3 yap')",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "play_spotify_track",
        "description": "Spotify'da belirli bir şarkıyı veya çalma listesini arar ve çalmaya başlar.",
        "parameters": {
            "type": "object",
            "properties": {
                "track": {"type": "string", "description": "Kullanıcının söylediği şarkı VEYA çalma listesi isminin TAMAMI (Örn: 'bunun adı ne bilmiyom', 'Raptimee'). Lütfen 'playlist' gibi jenerik kelimeler yerine kullanıcının telaffuz ettiği özel ismi kullan."},
                "artist": {"type": "string", "description": "Sanatçı adı (opsiyonel)."},
                "is_playlist": {"type": "boolean", "description": "Eğer aranan şey bir çalma listesi ise True olmalı."},
                "shuffle": {"type": "boolean", "description": "Eğer çalma listesi rastgele (karışık) çalınacaksa True olmalı."}
            },
            "required": ["track"],
        },
    },
    {
        "name": "spotify_control",
        "description": "Spotify çalma kontrollerini (duraklat, devam et, sonraki/önceki şarkı) yönetir.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["pause", "play", "next", "previous", "toggle"],
                    "description": "Yapılacak işlem: pause (durdur), play (devam et), next (sıradaki), previous (önceki), toggle (oynat/duraklat)."
                }
            },
            "required": ["action"],
        },
    },
    {
        "name": "computer_use",
        "description": (
            "Bilgisayarı otonom kontrol eder — ekranı görür, mouse/keyboard ile herhangi bir uygulamada "
            "işlem yapar (Discord'da mesaj yaz, sistem ayarlarını değiştir, GUI uygulamaları kontrol et vb.). "
            "30-120sn sürer. Çağırmadan önce 'tamam hallettim, bilgisayarda yapıyorum' de ve SUS. "
            "KESİNLİKLE KULLANMA: dosya/klasör oluşturma (`create_folder`, `create_project_file` kullan), "
            "uygulama açma/kapama (`open_app`/`close_app` kullan). "
            "`computer_use` SADECE GUI ile yapılabilecek ve başka tool'u olmayan işler içindir."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Bilgisayarda yapılacak görev, Türkçe doğal dille (örn: 'Spotify'da Tarkan Kuzu Kuzu çal', 'Hesap makinesinde 145*32 hesapla')",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "sleep_mode",
        "description": "Jarvan'ı uyku moduna alır. Kullanıcı 'uyu', 'kendini kapat', 'dinlenmeye geç' dediğinde bu aracı çağır. Oturum kapanmaz ama Jarvan sadece 'Uyan Jarvan' dendiğinde tekrar cevap verir.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "save_report",
        "description": "Kullanıcının Masaüstüne profesyonel bir analiz raporu (.md formatında) kaydeder. Derin araştırmalardan sonra mutlaka kullanılmalıdır.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Kaydedilecek dosya adı (örn: 'Berlin_Seyahat_Raporu.md')"},
                "content": {"type": "string", "description": "Raporun tüm içeriği (Markdown formatında, tablolar ve analizlerle birlikte)"}
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "create_folder",
        "description": (
            "Belirtilen konumda klasör oluşturur. 'Masaüstünde klasör oluştur', 'şu dizinde yeni klasör aç' "
            "gibi isteklerde DOĞRUDAN bu aracı kullan. `computer_use` çağırma."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "folder_path": {"type": "string", "description": "Klasör yolu (örn: 'Desktop/proje', 'masaüstü/yeni_klasör')"}
            },
            "required": ["folder_path"]
        }
    },
    {
        "name": "create_project_file",
        "description": "Belirtilen konumda dosya oluşturur ve içine kod/metin yazar. 'Desktop/proje/main.py', 'masaüstü/test.js' gibi yolları anlar.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Dosya yolu (örn: 'backend/main.py' veya 'Desktop/test.js')"},
                "content": {"type": "string", "description": "Dosya içeriği veya kod blokları"}
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "start_gemini_task",
        "description": (
            "Gemini CLI'yi arka planda başlatır ve kod yazma, refactor, analiz gibi uzun süren geliştirme görevlerini yapar. "
            "Görev bitince job_id ile sonucu almak için get_gemini_result kullan. "
            "Kullanıcı 'şu kodu yaz', 'bunu refactor et', 'proje analizi yap' gibi şeyler istediğinde bu aracı kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Gemini CLI'ye verilecek görev açıklaması. Ne yapılması gerektiğini detaylı yaz."
                },
                "heavy": {
                    "type": "boolean",
                    "description": "true → gemini-3.1-pro-preview (büyük refactor, derin analiz). false veya boş → gemini-3-flash-preview (genel kod, hızlı işler)."
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "get_gemini_result",
        "description": "start_gemini_task ile başlatılan bir görevin sonucunu sorgular. status: running (devam ediyor), done (bitti), error (hata).",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "start_gemini_task'tan dönen job_id"
                }
            },
            "required": ["job_id"]
        }
    },
    {
        "name": "obsidian_manage",
        "description": (
            "Obsidian not defterini yönetir. Not oluşturabilir, okuyabilir, arama yapabilir veya notları listeleyebilir. "
            "Kullanıcı 'şunu not al', 'notlarımı oku', 'X hakkında ne not almışım' gibi şeyler dediğinde bunu kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "read", "search", "list"],
                    "description": "Yapılacak işlem: create (oluştur), read (oku), search (ara), list (listele)"
                },
                "title": {"type": "string", "description": "Not başlığı (create ve read için gerekli)"},
                "content": {"type": "string", "description": "Not içeriği (sadece create için)"},
                "query": {"type": "string", "description": "Arama sorgusu (sadece search için)"},
                "folder": {"type": "string", "description": "Opsiyonel klasör yolu"}
            },
            "required": ["action"]
        }
    },
]

TOOL_IMPL = {
    "open_app": lambda args: open_app(args.get("name", "")),
    "close_app": lambda args: close_app(args.get("name", "")),
    "get_weather": lambda args: get_weather(args.get("location", "")),
    "open_url": lambda args: open_url(args.get("url", "")),
    "send_mail": lambda args: send_mail(
        args.get("to", ""),
        args.get("subject", ""),
        args.get("body", ""),
        bool(args.get("auto_send", False)),
    ),
    "check_mail": lambda args: check_mail(
        query=args.get("query", ""),
        max_results=args.get("max_results", 5),
        unread_only=bool(args.get("unread_only", False)),
        account=args.get("account"),
    ),
    "read_mail_body": lambda args: read_mail_body(
        message_id=args.get("message_id", ""),
        account=args.get("account"),
    ),
    "send_whatsapp": lambda args: send_whatsapp(args.get("message", ""), args.get("phone")),
}

RESEARCH_HINT = (
    "\n\n[ARAŞTIRMA VE ANALİZ STRATEJİSİ]\n"
    "1. ÖNCE HAFIZA: Herhangi bir şeyi araştırmadan önce 'Daha önce bu konuda bir not almış mıyım?' diye düşün. `obsidian_manage(action='search')` kullan.\n"
    "2. Web araması veya çok adımlı tarayıcı işi için `start_gemini_task` kullan — Gemini CLI Playwright ile tarayıcıyı tam kontrol eder.\n"
    "3. Kodlama, refactor veya uzun analiz için `start_gemini_task` kullan. Sonucu `get_gemini_result` ile al.\n"
    "4. ARŞİVLEME: Önemli sonuçları `obsidian_manage(action='create')` ile kaydet.\n"
    "\n[ARAŞTIRMA SONUCU GELDİĞİNDE — ZORUNLU KURAL]\n"
    "Bir araştırma sonucu (start_gemini_task veya herhangi bir tool) döndüğünde:\n"
    "- Sonuçtaki TARİH, FİYAT, SAYI, İSİM gibi SOMUT verileri kesinlikle doğru kabul et.\n"
    "- Bu veriler senin önceki tahmininle veya hafızanla çelişiyorsa → ARAŞTIRMA SONUCUNU KULLAN, tahminini at.\n"
    "- Sonraki araştırmalarda (otel, uçak, detay vb.) MUTLAKA bu güncel verileri kullan. Eski tahminine ASLA dönme.\n"
    "- ÖRNEK: 'Kurban Bayramı Mayıs sonu' diyen bir araştırma geldi → bundan sonra 'Mayıs sonu' yaz, 'Temmuz' yazma.\n"
    "- Emin değilsen kullanıcıya sor: 'Araştırmadan X çıktı, bunu baz alayım mı?' De. Uydurma.\n"
)

TOOL_CONFIRMATION_HINT = (
    "\n\n[ARAÇ KULLANIM KURALLARI]\n"
    "- `open_app`, `close_app`, `open_url`: düşük riskli, doğrudan çağırabilirsin. "
    "Kullanıcı 'X sayfasını aç' derse önce 'tamam açıyorum' gibi kısa bir onay söyle, aracı çağır.\n"
    "- `start_gemini_task`: web araştırması veya karmaşık tarayıcı görevi için kullan. Arka planda çalışır, "
    "job_id döner. Kullanıcıya 'başlattım, biraz sürebilir' de. Sonucu `get_gemini_result` ile al.\n"
    "- `send_whatsapp` ve `send_mail` (özellikle auto_send=true) VE dış dünyaya görünen her türlü aksiyon: ÖNCE ONAY AL. "
    "Mail için: 'X adresine \"konu\" başlıklı şu mesajı yazıp GÖNDERİYORUM (veya HAZIRLIYORUM): \"...\" — onaylıyor musun?' diye net bir cümle kur. "
    "WhatsApp için aynı kalıp. "
    "Kullanıcı 'evet', 'tamam', 'at', 'gönder', 'onaylıyorum' gibi NET onay vermeden aracı ÇAĞIRMA. "
    "'Belki', 'bilmiyorum', 'şey' gibi belirsiz cevaplar → tekrar sor.\n"
    "- Kullanıcı 'iptal', 'dur', 'boşver' derse aracı çağırma, kısaca 'tamam iptal ettim' de.\n\n"
    "[DOĞALLIK VE AKICILIK KURALLARI]\n"
    "1. TEKNİK TERİMLERDEN KAÇIN: 'Notlarıma bakıyorum', 'Hafızamı tarıyorum', 'Sisteme kaydediyorum', 'Tool çağırıyorum' gibi teknik ve robotik ifadeleri ASLA kullanma.\n"
    "2. ÖZ BİLGİ GİBİ DAVRAN: Obsidian'dan veya hafızadan bir bilgi çekerken, bunu sanki o an kendin hatırlıyormuşsun gibi doğal bir şekilde söyle. "
    "Örn: 'Hatırladığım kadarıyla Mad Men en sevdiğin diziydi' veya direkt 'Tabii, Sherlock ve Breaking Bad favorilerin arasında.'\n"
    "3. SESSİZ ÇALIŞMA: Arka planda bir araç (obsidian_manage, start_gemini_task vb.) çalışırken süreci anlatmak yerine sessizce bekle veya doğal bir 'Hımm...' çekip sonucu bekle.\n"
    "4. HEDEF: Kullanıcıya bir veritabanıyla değil, onunla yaşayan ve onu gerçekten tanıyan bir dostla konuştuğu hissini ver."
)

VISION_BEHAVIOR_HINT_FALLBACK = (
    "\n\n[EKRANI GÖRME — ZORUNLU KURALLAR]\n"
    "Kullanıcının ekranını saniye saniye GÖREMİYORSUN. Ekranı görmek için TEK YOL: `see_screen()` aracını çağırmak.\n"
    "1. Kullanıcı ekranla ilgili bir şey sorduğunda ('ekrana bak', 'şuna bak', 'görüyor musun', 'ekranda ne var', 'şu sayfa', 'açtığın site' vb.):\n"
    "   a) Önce kısaca 'Hemen bakıyorum...' de ve SUS.\n"
    "   b) `see_screen()` aracını çağır — argüman yok, boş obje.\n"
    "   c) Araç sana `screen` alanında gerçek ekran metnini dönecek. Cevabını SADECE ve SADECE bu metne dayanarak 'Ekranda ... görüyorum' şeklinde ver.\n"
    "2. YASAK: `see_screen()` çağırmadan ekran hakkında konuşma. 'Ekranda X var' gibi bir cümleyi aracı çağırmadan ASLA kurma — önceki sohbetten, tool sonuçlarından veya tahminden ekran içeriği ÜRETME.\n"
    "3. YASAK: Ekran görmek için `open_app`, `open_url` gibi başka araçları çağırma. Ekran = SADECE `see_screen()`.\n"
    "4. Kullanıcı ekranı sormuyorsa (sohbet, araştırma, başka tool) `see_screen()` çağırma. 'Bakalım', 'görelim' gibi dolgu ifadeleri ekran isteği DEĞİL.\n"
    "5. ÇOK ÖNEMLİ: `see_screen()` `ok: false` dönerse (hata, 503, timeout), kullanıcıya DÜRÜSTÇE söyle: 'Şu an ekrana bakamadım, bir saniye tekrar deneyebilir miyim?' DE. ASLA önceki ekran içeriğini tekrar etme, tahminden ekran anlatma. Hafızandaki eski ekran bilgisi artık geçersiz."
)

VISION_BEHAVIOR_HINT_PROACTIVE = (
    "\n\n[ÇOK ÖNEMLİ] ŞU ANDA ekrana 1 FPS hızında SÜREKLİ VİDEO YAYINI İLE bağlanmış durumdasın. Kullanıcının bilgisayar ekranını saniye saniye canlı izliyorsun! "
    "Eğer kullanıcı 'şu animasyon bozuk mu?' veya 'ekranımda ne görüyorsun' gibi bir şey sorarsa, hemen o saniye ne görüyorsan söyle. Ekstra bir bekleme veya fotoğraf çekme kuralı yok, doğrudan gördüğünden bahset."
)

COMPUTER_USE_HINT = (
    "\n\n[COMPUTER USE KURALLARI]\n"
    "- `computer_use`: Bilgisayarda herhangi bir uygulamayı otonom kontrol eder (ekranı görür, mouse/keyboard kullanır). "
    "Spotify, Discord, Finder, VS Code, sistem ayarları, masaüstü uygulamalar — HER ŞEY. "
    "30-120sn sürer. Çağırmadan önce 'tamam hallettim, bilgisayarda yapıyorum' de ve SUS.\n"
    "- Tarayıcı araştırması için `start_gemini_task` kullan — Gemini CLI Playwright ile tam kontrol sağlar.\n"
    "- Sonuç geldikten sonra result'u sesli özetle, kelimesi kelimesine.\n"
    "- Riskli istekler (dosya silme, format, kritik ayar) → ÖNCE ONAY AL."
)

LEARNING_PROTOCOL_HINT = (
    "\n\n[OBSIDIAN NÖRAL AĞ MİMARİSİ - ZORUNLU]\n"
    "Senin hafızan hiyerarşik bir ağ yapısındadır. Her yeni not mutlaka bir üst düğüme bağlı olmalıdır.\n"
    "1. MERKEZİ DÜĞÜM: Tüm notların en tepesinde `[[BEYİN]]` notu bulunur.\n"
    "2. ANA KATEGORİLER: \n"
    "   - Kullanıcı bilgileri -> `[[Kullanıcı Davranışları]]` altına,\n"
    "   - Araştırma sonuçları -> `[[Araştırmalar]]` altına,\n"
    "   - Teknik işler/kodlar -> `[[Projeler]]` altına,\n"
    "   - Kendi gelişimin -> `[[Jarvan Gelişim Günlüğü]]` altına bağlanmalıdır.\n"
    "3. BAĞLANTI KURALI: Yeni bir not oluştururken (action='create'), içeriğin sonuna mutlaka 'Bağlantı: [[İlgili Kategori]]' şeklinde WikiLink ekle. "
    "Eğer not mevcut bir konuyla ilgiliyse (Örn: Unity), o konunun notuna da (`[[Unity]]`) link ver.\n"
    "4. ARAMA DİSİPLİNİ: Bir şeyi araştırmadan önce mutlaka `search` yap. Eğer sonuç çoksa `list` yaparak tüm başlıkları oku. "
    "Kullanıcının sorduğu şeyi 'Hangi notta olabilir?' diye mantık yürüterek ara.\n"
    "5. OKUMA ZORUNLULUĞU (HALİSÜNASYON ENGELİ): Bir notun ismini bulman, içeriğini bildiğin anlamına gelmez! "
    "Kullanıcıya notun içeriğiyle ilgili bilgi vermeden önce MUTLAKA `obsidian_manage(action='read', title='...')` yaparak içeriği kelimesi kelimesine oku. "
    "Notu okumadan asla tahmin yürütme, popüler oyunları/müzikleri uydurma! Bilmiyorsan 'Bulamadım, neydi?' diye sor.\n"
    "6. HEDEF: Grafik görünümünde (Graph View) asla tek başına asılı duran (orphan) bir nokta bırakma. Her şey BEYİN'e ulaşan bir yolun parçası olmalı."
)
