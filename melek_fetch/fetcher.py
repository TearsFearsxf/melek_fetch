"""
melek_fetch.py — Melek AI Asistanı: Sessiz Bilgi Toplayıcı Modülü
=================================================================
Yazar        : Melek Projesi
Versiyon     : 2.0.0
Açıklama     : Hava durumu, döviz/altın ve Wikipedia verilerini
               tamamen ücretsiz, anahtarsız (No-Key) API'ler üzerinden
               arka planda çeken, RAM tabanlı TTL önbellekli,
               user-agent rotasyonlu, timeout korumalı veri motoru.

Bağımlılıklar: requests, beautifulsoup4
               pip install requests beautifulsoup4
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Loglama ayarları
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("MelekFetch")


# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

# Gerçekçi tarayıcı kimlikleri havuzu (User-Agent Rotasyonu)
USER_AGENTS: list[str] = [
    # Chrome / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    # Edge / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Safari / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    # Chrome / Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Firefox / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
]

# TTL (saniye cinsinden)
TTL_DOVIZ: int    = 600   # 10 dakika
TTL_HAVA: int     = 1800  # 30 dakika
TTL_WIKI: int     = 3600  # 1 saat

# Ağ isteği zaman aşımı (saniye)
REQUEST_TIMEOUT: int = 4


# ---------------------------------------------------------------------------
# Yardımcı: CacheEntry
# ---------------------------------------------------------------------------

class CacheEntry:
    """Tek bir önbellek kaydını ve TTL bilgisini tutar."""

    def __init__(self, data: Any, ttl: int) -> None:
        self.data: Any = data
        self.expires_at: float = time.monotonic() + ttl

    def is_valid(self) -> bool:
        """Kaydın süresi dolmadıysa True döner."""
        return time.monotonic() < self.expires_at

    def remaining(self) -> float:
        """Kalan geçerlilik süresi (saniye)."""
        return max(0.0, self.expires_at - time.monotonic())


# ---------------------------------------------------------------------------
# Ana Sınıf: MelekFetchController
# ---------------------------------------------------------------------------

class MelekFetchController:
    """
    Melek AI asistanı için merkezi arka-plan veri motoru.

    Özellikler
    ----------
    - RAM tabanlı TTL önbellek (her veri tipi için ayrı geçerlilik süresi)
    - User-Agent rotasyonu ile bot tespitine karşı koruma
    - Katı timeout ve kapsamlı hata yakalama
    - Üç ücretsiz veri motoru: Hava Durumu, Döviz/Altın, Wikipedia
    """

    def __init__(self) -> None:
        # Anahtar: cache_key (str) → CacheEntry
        self._cache: Dict[str, CacheEntry] = {}
        logger.info("MelekFetchController başlatıldı. Önbellek temiz.")

    # ------------------------------------------------------------------
    # Dahili yardımcılar
    # ------------------------------------------------------------------

    def _build_headers(self) -> Dict[str, str]:
        """Her istekte rastgele bir User-Agent seçerek HTTP başlığı üretir."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.7,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
        }

    def _get_json(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Verilen URL'ye GET isteği atar, JSON yanıtını döner.
        Hata durumunda None döner; hiçbir zaman istisna fırlatmaz.
        """
        try:
            response = requests.get(
                url,
                headers=self._build_headers(),
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.warning("Zaman aşımı: %s", url)
        except requests.exceptions.ConnectionError:
            logger.warning("Bağlantı hatası: %s", url)
        except requests.exceptions.HTTPError as exc:
            logger.warning("HTTP hatası %s: %s", exc.response.status_code, url)
        except Exception as exc:
            logger.error("Beklenmedik hata (%s): %s", type(exc).__name__, exc)
        return None

    def _get_text(self, url: str, params: Optional[Dict] = None) -> Optional[str]:
        """
        Verilen URL'ye GET isteği atar, ham metin yanıtını döner.
        Hata durumunda None döner; hiçbir zaman istisna fırlatmaz.
        """
        try:
            response = requests.get(
                url,
                headers=self._build_headers(),
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout:
            logger.warning("Zaman aşımı: %s", url)
        except requests.exceptions.ConnectionError:
            logger.warning("Bağlantı hatası: %s", url)
        except requests.exceptions.HTTPError as exc:
            logger.warning("HTTP hatası %s: %s", exc.response.status_code, url)
        except Exception as exc:
            logger.error("Beklenmedik hata (%s): %s", type(exc).__name__, exc)
        return None

    def _cache_get(self, key: str) -> Tuple[bool, Any]:
        """
        Önbellekte geçerli bir kayıt varsa (True, data) döner.
        Yoksa veya süresi dolmuşsa (False, None) döner.
        """
        entry = self._cache.get(key)
        if entry and entry.is_valid():
            logger.info("[CACHE] Veri internete çıkılmadan hafızadan okundu → %s", key)
            return True, entry.data
        return False, None

    def _cache_set(self, key: str, data: Any, ttl: int) -> None:
        """Veriyi önbelleğe yazar."""
        self._cache[key] = CacheEntry(data, ttl)
        logger.info("[CACHE] Önbelleğe yazıldı → %s (TTL: %ds)", key, ttl)

    def cache_stats(self) -> Dict[str, float]:
        """
        Önbellekteki tüm anahtarların kalan geçerlilik sürelerini döner.
        Süresi dolmuş kayıtları da raporlar.
        """
        return {
            key: entry.remaining()
            for key, entry in self._cache.items()
        }

    # ------------------------------------------------------------------
    # Motor A: Hava Durumu (Open-Meteo — Tamamen Ücretsiz, No-Key)
    # ------------------------------------------------------------------

    # Open-Meteo geocoding API'si ile şehir adından koordinat bulma
    _GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
    _WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

    # WMO hava durumu kodu → Türkçe açıklama
    _WMO_CODES: Dict[int, str] = {
        0: "Açık",
        1: "Çoğunlukla açık", 2: "Parçalı bulutlu", 3: "Kapalı",
        45: "Sisli", 48: "Kırağı sisli",
        51: "Hafif çisenti", 53: "Orta çisenti", 55: "Yoğun çisenti",
        61: "Hafif yağmurlu", 63: "Orta yağmurlu", 65: "Şiddetli yağmurlu",
        71: "Hafif karlı", 73: "Orta karlı", 75: "Yoğun karlı",
        77: "Kar tanecikleri",
        80: "Hafif sağanak", 81: "Orta sağanak", 82: "Şiddetli sağanak",
        85: "Hafif kar yağışı", 86: "Yoğun kar yağışı",
        95: "Gök gürültülü fırtına",
        96: "Hafif dolulu fırtına", 99: "Yoğun dolulu fırtına",
    }

    def _sehir_koordinat(self, sehir: str) -> Optional[Tuple[float, float, str]]:
        """
        Şehir adını Open-Meteo Geocoding API'si üzerinden enlem/boylama çevirir.
        Başarılı olursa (enlem, boylam, resmi_şehir_adı) döner; bulamazsa None.
        """
        data = self._get_json(self._GEO_URL, params={"name": sehir, "count": 1, "language": "tr"})
        if data and data.get("results"):
            sonuc = data["results"][0]
            return sonuc["latitude"], sonuc["longitude"], sonuc.get("name", sehir)
        logger.warning("Şehir bulunamadı: %s", sehir)
        return None

    def hava_durumu(self, sehir: str) -> str:
        """
        Belirtilen şehir için anlık hava durumunu Türkçe metin olarak döner.

        Parametreler
        ------------
        sehir : str
            Şehir adı (Türkçe veya İngilizce kabul edilir).

        Döndürür
        --------
        str
            Türkçe hava durumu özeti veya hata açıklaması.
        """
        cache_key = f"hava:{sehir.lower().strip()}"
        hit, cached = self._cache_get(cache_key)
        if hit:
            return cached

        konum = self._sehir_koordinat(sehir)
        if not konum:
            return f"❌ '{sehir}' şehri için konum bilgisi alınamadı."

        enlem, boylam, resmi_ad = konum
        params = {
            "latitude": enlem,
            "longitude": boylam,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weathercode,windspeed_10m",
            "timezone": "auto",
            "wind_speed_unit": "kmh",
        }
        data = self._get_json(self._WEATHER_URL, params=params)
        if not data or "current" not in data:
            return "❌ Hava durumu verisi alınamadı. Lütfen tekrar deneyin."

        current = data["current"]
        wmo = int(current.get("weathercode", 0))
        durum_aciklama = self._WMO_CODES.get(wmo, "Bilinmeyen")

        sonuc = (
            f"🌤 {resmi_ad} için anlık hava durumu:\n"
            f"   Durum       : {durum_aciklama}\n"
            f"   Sıcaklık    : {current.get('temperature_2m', '?')} °C"
            f" (Hissedilen: {current.get('apparent_temperature', '?')} °C)\n"
            f"   Nem         : %{current.get('relative_humidity_2m', '?')}\n"
            f"   Rüzgar      : {current.get('windspeed_10m', '?')} km/s"
        )
        self._cache_set(cache_key, sonuc, TTL_HAVA)
        return sonuc

    # ------------------------------------------------------------------
    # Motor B: Döviz ve Altın (ExchangeRate-API + TCMB yedek)
    # ------------------------------------------------------------------

    _EXCHANGE_URL = "https://api.exchangerate-api.com/v4/latest/TRY"
    _TCMB_URL     = "https://www.tcmb.gov.tr/kurlar/today.xml"

    def doviz_kurlari(self) -> str:
        """
        Güncel USD, EUR ve TRY bazlı döviz kurlarını çeker.
        Önce ücretsiz ExchangeRate-API denenir; başarısız olursa TCMB XML'i
        ayrıştırılır (yedek motor).

        Döndürür
        --------
        str
            Türkçe biçimlendirilmiş döviz özeti veya hata açıklaması.
        """
        cache_key = "doviz:try_bazli"
        hit, cached = self._cache_get(cache_key)
        if hit:
            return cached

        # --- Birincil Motor: ExchangeRate-API ---
        sonuc = self._doviz_exchangerate()
        if sonuc:
            self._cache_set(cache_key, sonuc, TTL_DOVIZ)
            return sonuc

        # --- Yedek Motor: TCMB XML ---
        logger.info("ExchangeRate-API başarısız, TCMB yedek motoru deneniyor…")
        sonuc = self._doviz_tcmb()
        if sonuc:
            self._cache_set(cache_key, sonuc, TTL_DOVIZ)
            return sonuc

        return "❌ Döviz kuru verisi alınamadı. İnternet bağlantınızı kontrol edin."

    def _doviz_exchangerate(self) -> Optional[str]:
        """ExchangeRate-API üzerinden TRY bazlı kur çeker."""
        data = self._get_json(self._EXCHANGE_URL)
        if not data or "rates" not in data:
            return None

        rates = data["rates"]
        try:
            usd = 1 / rates["USD"]   # 1 USD = ? TRY
            eur = 1 / rates["EUR"]   # 1 EUR = ? TRY
            gbp = 1 / rates["GBP"]   # 1 GBP = ? TRY
        except (KeyError, ZeroDivisionError):
            return None

        tarih = data.get("date", "Bilinmiyor")
        return (
            f"💱 Güncel Döviz Kurları ({tarih}):\n"
            f"   1 USD = {usd:.4f} TRY\n"
            f"   1 EUR = {eur:.4f} TRY\n"
            f"   1 GBP = {gbp:.4f} TRY\n"
            f"   (Kaynak: ExchangeRate-API)"
        )

    def _doviz_tcmb(self) -> Optional[str]:
        """TCMB günlük XML servisi üzerinden kur çeker (yedek motor)."""
        xml_text = self._get_text(self._TCMB_URL)
        if not xml_text:
            return None
        try:
            soup = BeautifulSoup(xml_text, "xml")
            kurlar: Dict[str, str] = {}
            for currency in soup.find_all("Currency"):
                kod = currency.get("CurrencyCode", "")
                alis = currency.find("ForexBuying")
                satis = currency.find("ForexSelling")
                if kod in ("USD", "EUR", "GBP") and alis and satis:
                    kurlar[kod] = {
                        "alış":  alis.text.replace(",", "."),
                        "satış": satis.text.replace(",", "."),
                    }
            if not kurlar:
                return None

            satirlar = ["💱 TCMB Günlük Döviz Kurları:"]
            for kod, degerler in kurlar.items():
                satirlar.append(
                    f"   1 {kod} — Alış: {degerler['alış']} TRY | "
                    f"Satış: {degerler['satış']} TRY"
                )
            return "\n".join(satirlar)
        except Exception as exc:
            logger.error("TCMB XML ayrıştırma hatası: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Motor C: Wikipedia Hızlı Bilgi (Resmi Wikipedia API — No-Key)
    # ------------------------------------------------------------------

    _WIKI_API_URL = "https://tr.wikipedia.org/api/rest_v1/page/summary/{title}"
    _WIKI_SEARCH_URL = "https://tr.wikipedia.org/w/api.php"

    def wikipedia_ozet(self, konu: str) -> str:
        """
        Belirtilen konu hakkında Wikipedia'dan Türkçe özet çeker.

        Parametreler
        ------------
        konu : str
            Aranacak konu, kişi veya kavram (Türkçe).

        Döndürür
        --------
        str
            İlk 2-3 cümlelik Türkçe Wikipedia özeti veya hata açıklaması.
        """
        temiz_konu = konu.strip()
        cache_key = f"wiki:{temiz_konu.lower()}"
        hit, cached = self._cache_get(cache_key)
        if hit:
            return cached

        # Önce doğrudan başlık ile dene
        sonuc = self._wiki_dogrudan(temiz_konu)

        # Bulamazsa Wikipedia arama API'si ile tahmin et
        if not sonuc:
            logger.info("Doğrudan başlık bulunamadı, arama API'si deneniyor: %s", temiz_konu)
            sonuc = self._wiki_ara_ve_getir(temiz_konu)

        if sonuc:
            self._cache_set(cache_key, sonuc, TTL_WIKI)
            return sonuc

        return f"❌ '{konu}' hakkında Wikipedia'da bilgi bulunamadı."

    def _wiki_dogrudan(self, baslik: str) -> Optional[str]:
        """
        Wikipedia REST API'sinin /page/summary/{title} uç noktasını kullanır.
        Başarısız olursa None döner.
        """
        url = self._WIKI_API_URL.format(title=requests.utils.quote(baslik))
        data = self._get_json(url)
        if not data:
            return None
        return self._wiki_veri_isle(data, baslik)

    def _wiki_ara_ve_getir(self, arama_terimi: str) -> Optional[str]:
        """
        Wikipedia arama API'si ile en alakalı başlığı bulur, ardından özetini çeker.
        """
        params = {
            "action": "query",
            "list": "search",
            "srsearch": arama_terimi,
            "srlimit": 1,
            "format": "json",
            "uselang": "tr",
        }
        data = self._get_json(self._WIKI_SEARCH_URL, params=params)
        if not data:
            return None

        arama_sonuclari = data.get("query", {}).get("search", [])
        if not arama_sonuclari:
            return None

        bulunan_baslik = arama_sonuclari[0]["title"]
        logger.info("Wikipedia araması sonucu: '%s' → '%s'", arama_terimi, bulunan_baslik)
        return self._wiki_dogrudan(bulunan_baslik)

    @staticmethod
    def _wiki_veri_isle(data: Dict, orijinal_konu: str) -> Optional[str]:
        """
        Wikipedia API'sinden gelen JSON verisini Türkçe özet metne dönüştürür.
        """
        # Belirsizlik sayfaları ve bulunamayan sayfalar için erken çıkış
        tip = data.get("type", "")
        if tip in ("disambiguation", "https://mediawiki.org/wiki/HyperSwitch/errors/not_found"):
            logger.warning("Wikipedia belirsizlik/bulunamadı: %s", orijinal_konu)
            return None

        ozet = data.get("extract", "").strip()
        if not ozet:
            return None

        baslik = data.get("title", orijinal_konu)

        # İlk 3 cümleyi al (nokta+boşluk ile böl, boş olanları filtrele)
        cumleler = [c.strip() for c in ozet.split(". ") if c.strip()]
        ilk_uc = ". ".join(cumleler[:3])
        if ilk_uc and not ilk_uc.endswith("."):
            ilk_uc += "."

        wiki_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        url_satir = f"\n   🔗 {wiki_url}" if wiki_url else ""

        return (
            f"📖 {baslik} hakkında Wikipedia özeti:\n"
            f"   {ilk_uc}"
            f"{url_satir}"
        )

    # ------------------------------------------------------------------
    # Önbellek yönetim araçları
    # ------------------------------------------------------------------

    def cache_temizle(self) -> None:
        """Tüm önbelleği sıfırlar."""
        self._cache.clear()
        logger.info("Önbellek tamamen temizlendi.")

    def cache_raporu(self) -> str:
        """
        Mevcut önbellek durumunu insan okunur biçimde döner.
        """
        if not self._cache:
            return "Önbellek boş."
        satirlar = ["📦 Önbellek Durumu:"]
        for key, entry in self._cache.items():
            durum = f"{entry.remaining():.0f}s kaldı" if entry.is_valid() else "SÜRESI DOLDU"
            satirlar.append(f"   [{durum}] {key}")
        return "\n".join(satirlar)


# ===========================================================================
# Test / Demo Bloğu
# ===========================================================================

if __name__ == "__main__":

    print("=" * 65)
    print("  MELEK FETCH CONTROLLER — Test Simülasyonu")
    print("=" * 65)

    melek = MelekFetchController()

    # -----------------------------------------------------------------------
    # SENARYO 1: Döviz Kurları
    # -----------------------------------------------------------------------
    print("\n[SENARYO 1] Canlı Döviz Kurları")
    print("-" * 45)
    print(melek.doviz_kurlari())

    # -----------------------------------------------------------------------
    # SENARYO 2: Hava Durumu
    # -----------------------------------------------------------------------
    print("\n[SENARYO 2] Anlık Hava Durumu — İstanbul")
    print("-" * 45)
    print(melek.hava_durumu("Istanbul"))

    # -----------------------------------------------------------------------
    # SENARYO 3: Wikipedia Özeti
    # -----------------------------------------------------------------------
    print("\n[SENARYO 3] Wikipedia Özeti — Yapay Zeka")
    print("-" * 45)
    print(melek.wikipedia_ozet("Yapay zeka"))

    # -----------------------------------------------------------------------
    # SENARYO 4: Önbellek Doğrulama Testi
    # -----------------------------------------------------------------------
    print("\n[SENARYO 4] Önbellek Doğrulama — Albert Einstein")
    print("-" * 45)
    print("► 1. İstek (internetten çekilecek):")
    print(melek.wikipedia_ozet("Albert Einstein"))

    print("\n  [ 2 saniye bekleniyor… ]")
    time.sleep(2)

    print("\n► 2. İstek (önbellekten okunmalı):")
    print(melek.wikipedia_ozet("Albert Einstein"))

    # Önbellek raporu
    print("\n" + "=" * 65)
    print(melek.cache_raporu())
    print("=" * 65)
    print("  Test simülasyonu tamamlandı.")
    print("=" * 65)