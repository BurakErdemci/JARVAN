"""Gemini Live — native audio dialog + on-demand ekran analizi."""
import asyncio
import io
import os
import re
import sys
import time
from typing import Callable

import pyaudio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY

from google import genai
from google.genai import types

from tools.app_control import open_app, close_app
from tools.whatsapp import send_whatsapp
from tools.browser_agent import run_browser_task, run_takeover_task, launch_debug_browser
from tools.browser import open_url, search_web, hidden_search
from tools.calculator import run_calculator_task
from tools.computer_use import run_computer_task
from tools.mail import send_mail
from tools.spotify import play_spotify_track
from tools.weather import get_weather
from ai.wake_word import WakeWordEngine

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
        "name": "search_web",
        "description": (
            "Arka planda gizli arama yapar ve en iyi 3 metin sonucunu döner. "
            "Herhangi bir araştırma için BUNU ZORUNLU KULLAN. "
            "Kullanıcı senden bulduğun bir sayfayı açmanı isterse, doğrudan o sitenin 'href' (link) adresini kullanarak open_url aracını çağır."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Aranacak kelime (örn: 'crimson desert metacritic')",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "open_result",
        "description": (
            "En son `search_web` sonucundaki N. linki tarayıcıda açar. "
            "Kullanıcı araştırma sonrası 'aç', 'göster', 'birinciyi aç' derse URL ezberlemek yerine bunu kullan. "
            "1 = birinci sonuç, 2 = ikinci, 3 = üçüncü."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer",
                    "description": "Açılacak sonucun sıra numarası (1, 2 veya 3)",
                },
            },
            "required": ["index"],
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
        "name": "browser_task",
        "description": (
            "Tarayıcıda otonom araştırma/bilgi toplama görevi yürütür (uçak bileti ara, ürün karşılaştır, siteden bilgi topla). "
            "Gemini 3 Flash bir tarayıcı ajanı açar, adım adım tıklayarak görevi çözer, sonucu metin olarak sana döner. "
            "ÇOK ÖNEMLİ: 30-90 saniye sürer. Çağırmadan önce 'tarayıcıda arıyorum, bir dakikanı alabilir' de ve SUS. "
            "SADECE arama/okuma için — form gönderme, satın alma, hesap açma YAPAMAZ (güvenlik). "
            "`task` alanını net ve spesifik Türkçe yaz: 'İstanbul-Londra 15 Mayıs tek yön en ucuz 3 uçuşu bul' gibi. "
            "Basit arama için `search_web` yeter; `browser_task` sadece çoklu adım gerektiğinde (siteye gir, filtrele, karşılaştır)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Tarayıcı ajanının yapacağı görev, Türkçe doğal dille"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "browser_start",
        "description": (
            "Opera GX'i debug modunda (port 9222) başlatır. Kullanıcının gerçek profili yüklenir "
            "(tab'lar, loginler, bookmarks hepsi yerinde) ama Jarvan istediği an CDP ile bağlanıp "
            "sekmeleri devralabilir. Kullanıcı 'tarayıcıyı debug modda aç', 'tarayıcıyı jarvan modda aç', "
            "'debug tarayıcı başlat' gibi dediğinde çağır. Opera zaten başka bir pencerede açıksa "
            "hata döner — kullanıcıya 'önce Opera'yı kapat' demen gerekir."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "browser_takeover",
        "description": (
            "Kullanıcının ZATEN AÇIK tarayıcısını devralıp görevi orada tamamlar (örn: 'şu an baktığım "
            "otobüs bileti sayfasında en ucuzunu bul', 'açık Gmail sekmesinde şu mailı oku'). "
            "browser_task'tan farkı: yeni browser açmaz, kullanıcının kaldığı yerden devam eder. "
            "Gereken: kullanıcının tarayıcısı debug modunda (port 9222) çalışıyor olmalı. Değilse "
            "Jarvan otomatik debug modda yeni bir pencere başlatır (kullanıcının eski tab'ları orada DEĞİL). "
            "Kullanım senaryosu: kullanıcı 'bunu sen devral', 'kaldığım yerden sen devam et', "
            "'şu açık sayfayı senin halletmene bırakıyorum' derse. Aksi halde `browser_task` kullan. "
            "30-90sn sürer. Çağırmadan önce 'tamam devralıyorum' de ve SUS."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Devralınan tarayıcıda yapılacak görev, Türkçe"},
            },
            "required": ["task"],
        },
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
        "name": "spotify_play",
        "description": (
            "Spotify'da şarkı aratıp çalmayı deterministic olarak dener. "
            "Örnek: 'Spotify'da Tarkan Kuzu Kuzu çal'. "
            "Mümkün olduğunda bunu `computer_use` yerine tercih et."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "track": {
                    "type": "string",
                    "description": "Çalınacak şarkı veya arama sorgusu",
                },
                "artist": {
                    "type": "string",
                    "description": "Opsiyonel sanatçı adı",
                },
            },
            "required": ["track"],
        },
    },
    {
        "name": "computer_use",
        "description": (
            "Bilgisayarı otonom kontrol eder — ekranı görür, mouse/keyboard ile herhangi bir uygulamada "
            "işlem yapar (Spotify'da şarkı aç, Finder'da dosya bul, ayarları değiştir, VS Code'da dosya aç, "
            "Discord'da mesaj yaz, masaüstü uygulama kontrol et vb.). "
            "30-120sn sürer. Çağırmadan önce 'tamam hallettim, bilgisayarda yapıyorum' de ve SUS. "
            "Tarayıcıda otonom araştırma için `browser_task` DAHA HIZLI — onu tercih et. "
            "`computer_use` SADECE tarayıcı dışı uygulamalar veya browser_task'ın yetmediği durumlar için."
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
    "send_whatsapp": lambda args: send_whatsapp(args.get("message", ""), args.get("phone")),
}

MODEL_NATIVE_AUDIO = "gemini-2.5-flash-native-audio-latest"
MODEL_FLASH_LIVE = "gemini-3.1-flash-live-preview"

VISION_MODELS = ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite-preview")
SUMMARY_MODELS = ("gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3.1-flash-lite-preview")
VOICE_NAME = "Kore"
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
INPUT_CHUNK_MS = 32
INPUT_CHUNK = int(INPUT_SAMPLE_RATE * INPUT_CHUNK_MS / 1000)
OUTPUT_COOLDOWN_S = 0.8  # Jarvan konuşurken + bittikten sonra kısa sessizlik (Yankıyı engellemek için 0.8'e çıkarıldı)

RESEARCH_HINT = (
    "\n\n[ARAŞTIRMA AKIŞI — ZORUNLU KURALLAR]\n"
    "Kullanıcı fiyat, bilet, puan, tarih, ürün, karşılaştırma, haber, 'X nedir/kim/ne kadar' gibi somut güncel bilgi istediğinde:\n"
    "1. HER ZAMAN `search_web(query)` aracını çağır. Arka planda canlı web araması yapar. Sana dönen sonuç ZATEN Türkçe 2-4 cümlelik bir `summary` alanı içerir — sistem ham sonuçları arka planda Flash Lite ile özetleyip sana sunar. Aramadan ASLA fiyat, havayolu adı, puan, tarih, URL ÜRETME. (Hava durumu için get_weather kullan.)\n"
    "2. Çağrı öncesi kısaca 'Hemen araştırıyorum...' de ve SUS, sonucu bekle.\n"
    "3. Sonuç gelince `summary` alanını kendi ağzınla, biraz yeniden düzenleyerek söyle. Kaynak isimlerini ('Metacritic'e göre...', 'NotebookCheck'e göre...') kullanabilirsin — bu bilgi summary içinde zaten geçiyor. URL ASLA söyleme, uzun linkleri JSON'a yazma.\n"
    "4. Sonra 'İstersen birincisini açabilirim' diye TEKLİF et. Kullanıcı 'aç', 'göster', 'evet' derse `open_result(index)` çağır (1, 2 veya 3). URL hatırlamana gerek yok.\n"
    "5. Arama dışı, kullanıcının açıkça söylediği bir domain için `open_url` kullan. Araştırma sonucunu açmak için DAİMA `open_result`."
)

TOOL_CONFIRMATION_HINT = (
    "\n\n[ARAÇ KULLANIM KURALLARI]\n"
    "- `open_app`, `close_app`, `open_url`: düşük riskli, doğrudan çağırabilirsin. "
    "Kullanıcı 'X sayfasını aç' derse önce 'tamam açıyorum' gibi kısa bir onay söyle, aracı çağır.\n"
    "- `search_web`: arka planda sessiz çalışır, ekranda bir şey açılmaz. 'Hemen araştırıyorum...' de, aracı çağır, sonucu bekle — 'açıyorum' DEME (çünkü hiçbir şey açılmıyor).\n"
    "- `browser_task`: tarayıcıda uzun süren araştırma (30-120sn sürebilir). Aracı BİR KEZ çağır, sonuç gelene kadar BEKLE. "
    "Sonuç geldiğinde `result` alanındaki veriyi KELİMESİ KELİMESİNE kullan — kendi kafandan fiyat/veri UYDURMA. "
    "Halüsinasyon YASAK: result'ta '11.539 TL AJet' yazıyorsa sen de '11.539 TL AJet' dersin, '2500 TL civarında' demezsin. "
    "Sonuç geldikten sonra aynı görevi tekrar ÇAĞIRMA.\n"
    "- `browser_takeover`: SADECE kullanıcı 'devral', 'kaldığım yerden devam et', 'sen halletmeye devam et', "
    "'şu açık sayfayı sen hallet' gibi AÇIKÇA devralma istediğinde kullan. Normal araştırmada DEĞİL — o `browser_task`. "
    "Sonuç kuralları browser_task ile aynı: result'u kelimesi kelimesine söyle, uydurma.\n"
    "- `send_whatsapp` ve `send_mail` (özellikle auto_send=true) VE dış dünyaya görünen her türlü aksiyon: ÖNCE ONAY AL. "
    "Mail için: 'X adresine \"konu\" başlıklı şu mesajı yazıp GÖNDERİYORUM (veya HAZIRLIYORUM): \"...\" — onaylıyor musun?' diye net bir cümle kur. "
    "WhatsApp için aynı kalıp. "
    "Kullanıcı 'evet', 'tamam', 'at', 'gönder', 'onaylıyorum' gibi NET onay vermeden aracı ÇAĞIRMA. "
    "'Belki', 'bilmiyorum', 'şey' gibi belirsiz cevaplar → tekrar sor.\n"
    "- Kullanıcı 'iptal', 'dur', 'boşver' derse aracı çağırma, kısaca 'tamam iptal ettim' de."
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
    "- Tarayıcı araştırması için `browser_task` DAHA HIZLI — tarayıcıda onu kullan.\n"
    "- Sonuç geldikten sonra result'u sesli özetle, kelimesi kelimesine.\n"
    "- Riskli istekler (dosya silme, format, kritik ayar) → ÖNCE ONAY AL."
)


class LiveSession:
    def __init__(
        self,
        system_prompt: str,
        on_log: Callable[[str, str, str | None], None],
        should_stop: Callable[[], bool],
        send_video: bool = False,
        conversation_memory: list[dict] = None,
        search_cache: list[dict] = None,
    ):
        self.system_prompt = system_prompt
        self.on_log = on_log
        self.should_stop = should_stop
        self.send_video = send_video
        self.conversation_memory = conversation_memory or []
        self.last_output_time = 0.0
        self.is_speaking = False
        self.playback_end_time = 0.0
        self.last_search_results: list[dict] = search_cache if search_cache is not None else []
        self._inflight_tools: set[str] = set()  # duplicate tool call koruması
        self._tool_cooldown: dict[str, float] = {}  # son tamamlanma zamanı
        self.is_asleep = True  # 7/24 dinleme modu için uyku durumu (Default Uyku)
        
        # Wake Word Motoru (Yerel)
        try:
            self.ww_engine = WakeWordEngine("models/vosk-tr", sample_rate=INPUT_SAMPLE_RATE)
        except Exception as e:
            self.on_log("error", f"WakeWord motoru başlatılamadı: {e}", None)
            self.ww_engine = None

        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"api_version": "v1beta"},
        )

    async def run(self):
        active_model = MODEL_FLASH_LIVE
        system_instruction = (
            self.system_prompt
            + "\n\n[UYKU MODU KURALLARI]\n"
            "Sen 7/24 uyanık kalabilen bir asistansın. Kullanıcı 'uyu', 'kendini kapat', 'hoşçakal', 'dinlenmeye geç' gibi veda cümleleri kurarsa "
            "mutlaka `sleep_mode()` aracını çağır. Uyumadan önce kullanıcıya nazikçe veda et (Örn: 'Tamamdır Burak, ben buralardayım, uyanmamı istersen seslenmen yeterli.'). "
            "Uyku modundayken sesin Gemini'ye gitmeyecek, sadece yerel olarak 'Uyan Jarvan' demeni bekleyeceğim."
            + (VISION_BEHAVIOR_HINT_PROACTIVE if self.send_video else VISION_BEHAVIOR_HINT_FALLBACK)
            + TOOL_CONFIRMATION_HINT
            + RESEARCH_HINT
            + COMPUTER_USE_HINT
        )
        
        if self.conversation_memory:
            mem_text = "\n".join([f"{m['role']}: {m['text']}" for m in self.conversation_memory])
            system_instruction += (
                "\n\n[ÇOK ÖNEMLİ - GEÇMİŞ SOHBET HAFIZAN]\n"
                "Kullanıcı UI üzerinden geçiş veya mod değişikliği yaptığı için bağlantın saniyeler önce resetlendi. Ancak sohbet kesintisiz devam ediyor. "
                "İşte yeniden bağlanmadan önceki son konuşmalarınızın dökümü. Doğrudan bu konuşmanın devamıymış gibi davran, kendini baştan tanıtma:\n"
                f"{mem_text}\n"
                "-----------------------------------\n\n"
            )

        config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": system_instruction,
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {"voice_name": VOICE_NAME}
                },
                "language_code": "tr-TR",
            },
            "input_audio_transcription": {},
            "output_audio_transcription": {},
            "tools": [
                {"function_declarations": FUNCTION_DECLARATIONS},
            ],
        }

        try:
            async with self.client.aio.live.connect(model=active_model, config=config) as session:
                self.on_log("system", f"Live bağlandı ({active_model}) — ses: {VOICE_NAME}.", None)
                if self.is_asleep:
                    self.on_log("system", "Jarvan uyku modunda (Pusu). 'Uyan Jarvan' diyerek uyandırabilirsin.", None)

                tasks = [
                    asyncio.create_task(self._mic_loop(session)),
                    asyncio.create_task(self._receive_loop(session)),
                    asyncio.create_task(self._stop_watcher()),
                ]
                
                if self.send_video:
                    tasks.append(asyncio.create_task(self._video_loop(session)))

                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for t in pending:
                    t.cancel()
                for t in pending:
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass
        except Exception as e:
            self.on_log("error", f"Live hatası: {e}", None)

    async def _stop_watcher(self):
        while not self.should_stop():
            await asyncio.sleep(0.1)

    async def _mic_loop(self, session):
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=INPUT_CHUNK,
        )
        try:
            while not self.should_stop():
                data = await asyncio.to_thread(stream.read, INPUT_CHUNK, False)
                
                # --- Wake Word / Sleep Logic ---
                if self.is_asleep:
                    if self.ww_engine:
                        result = self.ww_engine.process_data(data)
                        if result and "uyan" in result:
                            self.on_log("system", "Wake Word yakalandı: UYAN!", None)
                            self.is_asleep = False
                            # Gemini'ye uyandığını ve selam vermesi gerektiğini söyle
                            try:
                                await session.send_realtime_input(
                                    text="Kullanıcı seni 'Uyan Jarvan' diyerek uyandırdı. Ona sıcak ve enerjik bir karşılama yap."
                                )
                            except Exception as e:
                                self.on_log("error", f"Selam tetikleme hatası (devam ediliyor): {e}", None)
                    continue # Uyku modundayken sesi buluta gönderme
                
                if self.is_speaking or (time.monotonic() - self.last_output_time < OUTPUT_COOLDOWN_S):
                    continue
                
                await session.send_realtime_input(
                    audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}")
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.on_log("error", f"Mic loop: {e}", None)
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

    async def _receive_loop(self, session):
        p = pyaudio.PyAudio()
        out_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
        )
        in_buf = ""
        out_buf = ""
        try:
            while not self.should_stop():
                async for response in session.receive():
                    if self.should_stop():
                        break

                    if response.data:
                        self.is_speaking = True
                        now = time.monotonic()
                        self.last_output_time = now
                        # Bu chunk'ın çalma süresini playback_end_time'a ekle
                        chunk_duration = len(response.data) / (OUTPUT_SAMPLE_RATE * 2)
                        self.playback_end_time = max(self.playback_end_time, now) + chunk_duration
                        await asyncio.to_thread(out_stream.write, response.data)
                        self.last_output_time = time.monotonic()

                    tc = getattr(response, "tool_call", None)
                    if tc and getattr(tc, "function_calls", None):
                        wait_s = self.playback_end_time - time.monotonic()
                        if wait_s > 0:
                            await asyncio.sleep(wait_s + 0.15)
                        self.is_speaking = False
                        # create_task: ses beklendi, audio tamam. Artık receive_loop
                        # dönmeye devam eder → WebSocket ping-pong işlenir → session düşmez.
                        task = asyncio.create_task(self._handle_tool_calls(session, tc.function_calls))
                        task.add_done_callback(
                            lambda t: self.on_log("error", f"tool task hata: {t.exception()}", None)
                            if not t.cancelled() and t.exception() else None
                        )
                        continue

                    sc = getattr(response, "server_content", None)
                    if sc is None:
                        continue

                    it = getattr(sc, "input_transcription", None)
                    if it and getattr(it, "text", None):
                        in_buf += it.text

                    ot = getattr(sc, "output_transcription", None)
                    if ot and getattr(ot, "text", None):
                        out_buf += ot.text

                    if getattr(sc, "turn_complete", False):
                        self.is_speaking = False
                        self.last_output_time = time.monotonic()
                        user_text = in_buf.strip()
                        if user_text:
                            self.on_log("user", user_text, None)
                            in_buf = ""
                        if out_buf.strip():
                            import re
                            clean_out = re.sub(r"<ctrl\d+>", "", out_buf).strip()
                            if clean_out:
                                self.on_log("jarvan", clean_out, "live")
                            out_buf = ""

                    if getattr(sc, "interrupted", False):
                        self.is_speaking = False
                        self.last_output_time = time.monotonic()
                        if out_buf.strip():
                            import re
                            clean_out = re.sub(r"<ctrl\d+>", "", out_buf).strip()
                            if clean_out:
                                self.on_log("jarvan", clean_out + " …", "live")
                            out_buf = ""
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.on_log("error", f"Receive loop: {e}", None)
        finally:
            if in_buf.strip():
                self.on_log("user", in_buf.strip(), None)
            if out_buf.strip():
                self.on_log("jarvan", out_buf.strip(), "live")
            out_stream.stop_stream()
            out_stream.close()
            p.terminate()

    async def _handle_tool_calls(self, session, function_calls):
        responses = []
        for fc in function_calls:
            name = fc.name
            args = dict(fc.args) if fc.args else {}

            if name == "search_web":
                query = args.get("query", "")
                self.on_log("system", f"[tool] search_web({args})", None)
                try:
                    raw = await asyncio.to_thread(hidden_search, query)
                    if raw.get("ok"):
                        self.last_search_results.clear()
                        self.last_search_results.extend(raw.get("results") or [])
                        summary = await self._summarize_search(query, raw)
                        result = {
                            "ok": True,
                            "summary": summary,
                            "count": len(self.last_search_results),
                        }
                    else:
                        result = {"ok": False, "error": raw.get("error", "arama başarısız")}
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "browser_task":
                task = args.get("task", "")
                now = time.monotonic()
                cooldown_until = self._tool_cooldown.get("browser_task", 0)
                if "browser_task" in self._inflight_tools:
                    result = {"ok": False, "error": "Tarayıcı görevi zaten çalışıyor, lütfen bekle."}
                    self.on_log("system", "[tool] browser_task zaten in-flight, atlandı", None)
                    responses.append({"id": fc.id, "name": name, "response": result})
                    continue
                if now < cooldown_until:
                    result = {"ok": False, "error": f"Az önce aynı görev tamamlandı, sonucu sesli özetle."}
                    self.on_log("system", f"[tool] browser_task cooldown ({cooldown_until - now:.0f}s kaldı), atlandı", None)
                    responses.append({"id": fc.id, "name": name, "response": result})
                    continue
                self._inflight_tools.add("browser_task")
                self.on_log("system", f"[tool] browser_task({task[:80]}...)", None)
                try:
                    # Keepalive yok — WebSocket kendi ping/pong yapıyor, boş text frame'leri
                    # Gemini Live'ı confuse edip tool response sonrası halüsinasyona sebep oluyordu.
                    raw = await run_browser_task(task)
                    self._inflight_tools.discard("browser_task")
                    self._tool_cooldown["browser_task"] = time.monotonic() + 90

                    if raw.get("ok"):
                        result = {"ok": True, "result": raw.get("result", "")}
                    else:
                        result = {"ok": False, "error": raw.get("error", "görev başarısız")}
                except Exception as e:
                    self._inflight_tools.discard("browser_task")
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "browser_start":
                self.on_log("system", "[tool] browser_start()", None)
                try:
                    result = await asyncio.to_thread(launch_debug_browser)
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "browser_takeover":
                task = args.get("task", "")
                if "browser_task" in self._inflight_tools or "browser_takeover" in self._inflight_tools:
                    result = {"ok": False, "error": "Bir tarayıcı görevi zaten çalışıyor, lütfen bekle."}
                    self.on_log("system", "[tool] browser_takeover in-flight, atlandı", None)
                    responses.append(types.FunctionResponse(id=fc.id, name=name, response=result))
                    continue
                self._inflight_tools.add("browser_takeover")
                self.on_log("system", f"[tool] browser_takeover({task[:80]}...)", None)
                try:
                    raw = await run_takeover_task(task)
                    self._inflight_tools.discard("browser_takeover")
                    if raw.get("ok"):
                        result = {"ok": True, "result": raw.get("result", "")}
                    else:
                        result = {"ok": False, "error": raw.get("error", "takeover başarısız")}
                except Exception as e:
                    self._inflight_tools.discard("browser_takeover")
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "computer_use":
                task = args.get("task", "")
                if "computer_use" in self._inflight_tools:
                    result = {"ok": False, "error": "Computer use görevi zaten çalışıyor, lütfen bekle."}
                    self.on_log("system", "[tool] computer_use zaten in-flight, atlandı", None)
                    responses.append(types.FunctionResponse(id=fc.id, name=name, response=result))
                    continue
                now = time.monotonic()
                cooldown_until = self._tool_cooldown.get("computer_use", 0)
                if now < cooldown_until:
                    result = {"ok": False, "error": "Az önce aynı görev tamamlandı, sonucu sesli özetle."}
                    self.on_log("system", f"[tool] computer_use cooldown ({cooldown_until - now:.0f}s kaldı), atlandı", None)
                    responses.append(types.FunctionResponse(id=fc.id, name=name, response=result))
                    continue
                self._inflight_tools.add("computer_use")
                self.on_log("system", f"[tool] computer_use({task[:80]}...)", None)
                try:
                    raw = await asyncio.wait_for(run_computer_task(task), timeout=300)
                    self._inflight_tools.discard("computer_use")
                    self._tool_cooldown["computer_use"] = time.monotonic() + 60
                    if raw and raw.get("ok"):
                        result = {"ok": True, "result": str(raw.get("result", ""))}
                    else:
                        err_msg = raw.get("error", "görev başarısız") if raw else "Boş yanıt"
                        result = {"ok": False, "error": str(err_msg)}
                except asyncio.TimeoutError:
                    self._inflight_tools.discard("computer_use")
                    result = {"ok": False, "error": "Computer use 5 dakikada bitmedi, zaman aşımı."}
                except Exception as e:
                    self._inflight_tools.discard("computer_use")
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "calculator_compute":
                task = args.get("task", "")
                self.on_log("system", f"[tool] calculator_compute({task[:80]}...)", None)
                try:
                    raw = await run_calculator_task(task)
                    if raw.get("ok"):
                        result = {"ok": True, "result": f"Calculator'da {raw.get('expression')} işlendi, sonuç: {raw.get('result')}"}
                    else:
                        result = {"ok": False, "error": raw.get("error", "hesap makinesi görevi başarısız")}
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "spotify_play":
                track = args.get("track", "")
                artist = args.get("artist")
                self.on_log("system", f"[tool] spotify_play(track={track!r}, artist={artist!r})", None)
                try:
                    raw = await play_spotify_track(track, artist)
                    if raw.get("ok"):
                        result = {"ok": True, "result": raw.get("result", "")}
                    else:
                        result = {"ok": False, "error": raw.get("error", "spotify görevi başarısız")}
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "see_screen":
                self.on_log("system", "[tool] see_screen()", None)
                try:
                    description = await self._describe_screen()
                    if description:
                        result = {"ok": True, "screen": description}
                    else:
                        result = {"ok": False, "error": "ekran analizi başarısız"}
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "sleep_mode":
                self.on_log("system", "[tool] sleep_mode()", None)
                self.is_asleep = True
                result = {"ok": True, "message": "Jarvan uyku moduna geçti. Sadece 'Uyan Jarvan' ile uyanacak."}
                self.on_log("system", "[Jarvan Uyuyor...]", None)
            elif name == "open_result":
                self.on_log("system", f"[tool] open_result({args})", None)
                try:
                    idx = int(args.get("index", 0))
                    if not self.last_search_results:
                        result = {"ok": False, "error": "henüz bir search_web sonucu yok"}
                    elif idx < 1 or idx > len(self.last_search_results):
                        result = {"ok": False, "error": f"geçersiz index: {idx} (1..{len(self.last_search_results)})"}
                    else:
                        target = self.last_search_results[idx - 1]
                        url = target.get("href") or target.get("url") or ""
                        if not url:
                            result = {"ok": False, "error": "sonuçta URL yok"}
                        else:
                            raw_res = await asyncio.to_thread(open_url, url)
                            if raw_res.get("ok"):
                                result = {"ok": True, "note": "Sayfa tarayıcıda başarıyla açıldı."}
                            else:
                                result = raw_res
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)
            else:
                impl = TOOL_IMPL.get(name)
                if impl is None:
                    result = {"ok": False, "error": f"bilinmeyen tool: {name}"}
                else:
                    self.on_log("system", f"[tool] {name}({args})", None)
                    try:
                        raw_result = await asyncio.to_thread(impl, args)
                        result = raw_result.copy() if isinstance(raw_result, dict) else raw_result
                        if isinstance(result, dict) and "url" in result:
                            del result["url"]
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}
                    self.on_log("system", f"[tool sonuç] {result}", None)

            responses.append(types.FunctionResponse(
                id=fc.id,
                name=name,
                response=result,
            ))

        await session.send_tool_response(function_responses=responses)


    async def _summarize_search(self, query: str, raw: dict) -> str:
        """Ham arama sonucunu (Tavily answer + results[]) Flash Lite ile 2-4 cümleye indirir.
        Live'a sadece temiz Türkçe metin gider; URL/JSON serialize edilmez → 1011 riski düşer."""
        answer = (raw.get("answer") or "").strip()
        results = raw.get("results") or []

        def _domain(href: str) -> str:
            try:
                from urllib.parse import urlparse
                host = urlparse(href).netloc
                return host.replace("www.", "") if host else ""
            except Exception:
                return ""

        lines = []
        if answer:
            lines.append(f"Özet cevap: {answer}")
        for i, r in enumerate(results[:3], start=1):
            title = (r.get("title") or "").strip()
            body = (r.get("body") or "").strip()
            dom = _domain(r.get("href") or "")
            lines.append(f"{i}. [{dom or title}] {title}\n{body}")

        context = "\n\n".join(lines) if lines else "(sonuç boş)"

        prompt = (
            f"Kullanıcının sorusu: \"{query}\"\n\n"
            f"Web arama sonuçları:\n{context}\n\n"
            "Bu sonuçları sesli asistanın okuyacağı 2-4 cümlelik TEMİZ TÜRKÇE özete dönüştür. "
            "Somut verileri (puan, fiyat, tarih, isim) BİREBİR koru. "
            "Kaynak adlarını doğal cümle içinde kullan ('Metacritic'e göre 78 puan...'). "
            "URL, link, parantez içi referans YAZMA. "
            "Çelişen bilgiler varsa en güncel/güvenilir kaynağı tercih et. "
            "Sonuç yoksa 'net bir bilgi bulamadım' de. Sadece özeti döndür, başka bir şey yazma."
        )

        gen_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        last_err = None
        for model in SUMMARY_MODELS:
            try:
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=[prompt],
                    config=gen_config,
                )
                text = (response.text or "").strip()
                if text:
                    return text
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                if any(t in msg for t in ("quota", "429", "exhausted", "rate", "503", "unavailable", "overload")):
                    continue
                break

        self.on_log("error", f"Arama özetleme başarısız: {last_err}", None)
        if answer:
            return answer[:400]
        if results:
            first = results[0]
            body = (first.get("body") or "").strip()
            return f"{first.get('title', '')}: {body[:250]}"
        return "Arama sonucu bulunamadı."

    async def _describe_screen(self) -> str:
        from screen.capture import capture_screenshot_pil

        self.on_log("system", "Ekran analiz ediliyor…", None)
        img = await asyncio.to_thread(capture_screenshot_pil)
        img.thumbnail((720, 720))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=75)
        jpeg = buf.getvalue()

        prompt = (
            "Ekranda net görüneni 2-3 cümle teknik Türkçe özetle. "
            "Spekülasyon yok, sadece görülen. Araç/pencere adı, hata mesajı, "
            "kod veya UI elementi varsa belirt."
        )

        vision_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        description = ""
        last_err: Exception | None = None
        for model in VISION_MODELS:
            try:
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
                        prompt,
                    ],
                    config=vision_config,
                )
                description = (response.text or "").strip()
                if description:
                    break
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                if any(t in msg for t in ("quota", "429", "exhausted", "rate", "503", "unavailable", "overload")):
                    continue
                raise

        if not description:
            self.on_log("error", f"Vision başarısız: {last_err}", None)
            return ""

        self.on_log("system", f"[ekran] {description}", None)
        return description

    async def _video_loop(self, session):
        try:
            from screen.capture import capture_screenshot_pil
            self.on_log("system", "Gerçek zamanlı ekran yayını (1 FPS) başladı.", None)
            while not self.should_stop():
                img = await asyncio.to_thread(capture_screenshot_pil)
                
                # Çözünürlüğü çok büyütmemek lazım, 2 FPS olduğu için ağa bindirmesin
                img.thumbnail((720, 720))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=60)
                jpeg = buf.getvalue()

                await session.send_realtime_input(
                    video=types.Blob(mime_type="image/jpeg", data=jpeg)
                )
                
                await asyncio.sleep(1.0)  # Canlı akış = Saniyede 1 kare (1 FPS)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.on_log("error", f"Video loop: {e}", None)
