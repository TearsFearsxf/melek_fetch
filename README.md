# 🌟 Melek AI Fetch Engine (`melek_fetch`)

[![Python Version](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macos-lightgrey)]()
[![Build](https://img.shields.io/badge/build-passing-brightgreen)]()

> Melek AI Asistan Projesi için tasarlanmış; tamamen ücretsiz, API anahtarı (No-Key) gerektirmeyen, yüksek hızlı, RAM önbellekli ve anti-bot korumalı veri toplama motoru.

---

## 📖 Genel Bakış

**Melek AI Fetch Engine**, asistanınızın internetten anlık olarak ihtiyaç duyduğu bilgileri (hava durumu, döviz/altın fiyatları, Wikipedia özetleri) çeken hafif ama dayanıklı bir motor sunar. Ücretli veya üyelik gerektiren hiçbir harici servise bağımlı değildir; arka planda akıllı istek rotasyonları yaparak çalışır.

---

## ✨ Öne Çıkan Özellikler

### 🌤️ Hava Durumu Motoru (Open-Meteo Entegrasyonu)
* Şehir adını enlem ve boylama otomatik çeviren **Geocoding API** entegrasyonu.
* Türkçe WMO (World Meteorological Organization) durum kodları eşleştirmesi.
* Hissedilen sıcaklık, anlık nem, rüzgar hızı ve yönü gibi detaylı veriler.

### 💱 Döviz ve Altın Kurları Motoru (Çift Motor Teknolojisi)
* **Birincil Motor (ExchangeRate-API):** TRY bazlı güncel USD, EUR, GBP fiyatlarını anlık yakalar.
* **Yedek Motor (TCMB Günlük XML):** Birincil motorun hata vermesi durumunda Türkiye Cumhuriyeti Merkez Bankası kurlarını indirerek XML ayrıştırıcı ile veriyi yedekler.

### 📖 Wikipedia Özetleyici (Wikipedia REST API)
* Girilen kavramı Wikipedia arama API'si ile en alakalı başlığa yönlendirir.
* İlk 3 anlamlı cümleyi ayıklayarak temiz Türkçe özet sunar.
* Konunun resmi masaüstü bağlantısını (`🔗 URL`) otomatik ekler.

### ⚡ Performans ve Güvenlik
* **RAM Tabanlı TTL Önbellek (Cache):** Verileri RAM'de tutar. Hava durumu için 30 dk, Döviz için 10 dk, Wiki için 1 saat boyunca internete çıkmadan doğrudan bellekten yanıt döner.
* **User-Agent Rotasyonu:** Her istekte farklı tarayıcı kimlikleri (Chrome, Firefox, Edge, Safari) kullanarak bot engellemesini aşar.
* **Timeout Güvencesi:** İsteklerde katı 4 saniye zaman aşımı uygulayarak asistan ana döngüsünü asla dondurmaz.

---

## 🚀 Kurulum

Projeyi yerel olarak geliştirmek ve paket olarak kurmak için kök dizinde şu komutu çalıştırmanız yeterlidir:

```bash
pip install -e .
```

---

## 💻 Kullanım Örnekleri

Kütüphaneyi projelerinize dahil etmek oldukça basittir. İşte tam kapsamlı bir kullanım örneği:

```python
import time
from melek_fetch import MelekFetchController

# Motoru başlat
melek = MelekFetchController()

print("=" * 60)
print("  MELEK AI FETCH ENGINE - ÇALIŞMA DEMOSU")
print("=" * 60)

# 1. Hava Durumu Sorgulama
print("\n🌤️ [HAVA DURUMU] İstanbul Sorgulanıyor...")
hava = melek.hava_durumu("Istanbul")
print(hava)

# 2. Döviz Kurları Sorgulama
print("\n💱 [DÖVİZ KURLARI] Güncel Durum Çekiliyor...")
doviz = melek.doviz_kurlari()
print(doviz)

# 3. Wikipedia Bilgi Sorgulama (Doğrudan Arama ve Yönlendirme)
print("\n📖 [WIKIPEDIA] Albert Einstein Hakkında Özet...")
wiki = melek.wikipedia_ozet("Albert Einstein")
print(wiki)

# 4. Önbellek (Cache) Testi (İkinci kez çağrıldığında internete çıkmaz)
print("\n⚡ [CACHE] Aynı sorgu tekrar yapılıyor...")
start_time = time.time()
wiki_cached = melek.wikipedia_ozet("Albert Einstein")
elapsed = time.time() - start_time
print(wiki_cached)
print(f"--> Yanıt süresi: {elapsed:.6f} saniye (RAM'den okundu)")

# 5. Önbellek Raporu
print("\n📦 [CACHE REPORT]")
print("-" * 20)
print(melek.cache_raporu())
print("=" * 60)
```

---

## 🛠️ Bağımlılıklar

Kütüphane minimum bağımlılık felsefesiyle yazılmıştır:
* [requests](https://pypi.org/project/requests/) (>=2.28.0)
* [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) (>=4.11.0)
