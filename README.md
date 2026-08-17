# tsb-kasko-mcp

Türkiye Sigorta Birliği'nin (TSB) yayımladığı **Kasko Değer Listesi** için MCP sunucusu, komut satırı aracı ve Python istemcisi.

Kasko değer listesi, Türkiye'de satılan her kasko poliçesinin fiyatlandığı referans bedeldir. Aynı zamanda pert ve çalınma durumlarında ödenecek tutarın da dayanağıdır. Bu proje, TSB'nin web sitesinin arka planında kullandığı ve herhangi bir kimlik doğrulaması gerektirmeyen uçları tiplenmiş bir istemciye dönüştürür.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Lisans: MIT](https://img.shields.io/badge/lisans-MIT-green)](LICENSE)

## Ne işe yarar

- **Yapay zekâ asistanlarından sorgulama.** Claude, ChatGPT ve Gemini içinden "2025 model Audi A3 Sportback'in kasko bedeli ne kadar" diye sorabilirsiniz.
- **Terminalden sorgulama.** `tsb-kasko lookup 2025 "audi a3 sportback"` komutu tabloyu, JSON'u veya CSV'yi doğrudan basar.
- **Poliçedeki araç kodu.** Sonuçlar sigortacının sorduğu `marka kodu - model kodu` ikilisini de içerir, örneğin `9-1616`.
- **Geçmiş listeler.** TSB her ay listeyi yeniden yayımlar. Geçmiş ayların Excel dosyasını indirebilir veya içinde arama yapabilirsiniz.
- **Python kütüphanesi.** Kendi projenizde `TsbKaskoClient` sınıfını doğrudan kullanabilirsiniz.

## Kurulum

Kurulum yapmadan denemek için:

```bash
uvx --from tsb-kasko-mcp tsb-kasko lookup 2025 "audi a3 sportback"
```

Kalıcı kurulum:

```bash
uv tool install tsb-kasko-mcp
```

veya

```bash
pip install tsb-kasko-mcp
```

Depodan geliştirme kurulumu:

```bash
git clone https://github.com/hmtkyn/tsb-kasko-mcp.git
cd tsb-kasko-mcp
uv venv
uv pip install -e ".[dev,http]"
```

## MCP kurulumu

Sunucu hem `stdio` hem de streamable HTTP taşımasını destekler, bu yüzden üç büyük istemcinin de beklediği biçimde çalışır.

### Claude Desktop

`claude_desktop_config.json` dosyasına ekleyin:

```json
{
  "mcpServers": {
    "tsb-kasko": {
      "command": "uvx",
      "args": ["--from", "tsb-kasko-mcp", "tsb-kasko-mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add tsb-kasko -- uvx --from tsb-kasko-mcp tsb-kasko-mcp
```

### Gemini CLI

`~/.gemini/settings.json` dosyasına ekleyin:

```json
{
  "mcpServers": {
    "tsb-kasko": {
      "command": "uvx",
      "args": ["--from", "tsb-kasko-mcp", "tsb-kasko-mcp"]
    }
  }
}
```

### ChatGPT ve diğer uzak istemciler

ChatGPT bağlayıcıları sunucuya HTTP üzerinden ulaşır. Sunucuyu HTTP modunda çalıştırın:

```bash
TSB_KASKO_TRANSPORT=http TSB_KASKO_HOST=0.0.0.0 TSB_KASKO_PORT=8000 tsb-kasko-mcp
```

veya herhangi bir ASGI sunucusuyla:

```bash
uvicorn tsb_kasko.asgi:app --host 0.0.0.0 --port 8000
```

Uç nokta varsayılan olarak `http://sunucu:8000/mcp` adresinde yayınlanır.

## MCP araçları

| Araç | Ne yapar |
| --- | --- |
| `kasko_lookup` | Serbest metinden araç bulur ve her eşleşmenin kasko bedelini döner. Ana araç budur. |
| `kasko_list_model_years` | Listenin kapsadığı model yıllarını döner. Kapsam 2012 ve sonrasıdır. |
| `kasko_list_brands` | Bir model yılındaki markaları listeler. |
| `kasko_list_models` | Bir markanın o model yılındaki tiplerini listeler. |
| `kasko_get_value` | Model kimliği bilinen tek bir aracın bedelini okur. |
| `kasko_archive_file` | Belirli bir ayın yayımlanmış Excel dosyasını çözümler. |
| `kasko_search_archive` | Geçmiş bir ayın listesi içinde arama yapar. |
| `kasko_download_archive` | Belirli bir ayın Excel dosyasını diske indirir. |

## Komut satırı kullanımı

```bash
# Kapsanan model yılları
tsb-kasko years

# Bir model yılındaki markalar
tsb-kasko brands 2025

# Bir markanın tipleri
tsb-kasko models 2025 audi

# Serbest metinle sorgulama
tsb-kasko lookup 2025 "audi a3 sportback s line"

# Markayı sabitleyerek hızlandırma
tsb-kasko lookup 2025 "corolla hybrid" --brand toyota --limit 10

# JSON veya CSV çıktısı
tsb-kasko lookup 2025 "audi a3" --format json
tsb-kasko brands 2025 --format csv > markalar.csv

# Arşiv
tsb-kasko archive months
tsb-kasko archive file 2025 2
tsb-kasko archive search 2025 2 --query "sahin" --limit 20
tsb-kasko archive download 2025 2 --output ~/Downloads

# Önbellek
tsb-kasko cache path
tsb-kasko cache clear

# MCP sunucusunu CLI üzerinden çalıştırma
tsb-kasko serve --transport http --port 8000
```

Örnek çıktı:

```
                      audi a3 sportback in 2025
┏━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Vehicle Code ┃ Brand ┃ Model                               ┃ Kasko Value    ┃
┡━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 9-1616       │ AUDI  │ A3 SPORTBACK 35 TFSI 150 S LINE ... │ 3.695.439,00 TL│
└──────────────┴───────┴─────────────────────────────────────┴────────────────┘
```

## Python kütüphanesi olarak

```python
import asyncio

from tsb_kasko import TsbKaskoClient


async def main() -> None:
    async with TsbKaskoClient() as client:
        for value in await client.lookup(2025, "audi a3 sportback"):
            print(value.vehicle_code, value.model_name, value.amount)


asyncio.run(main())
```

## Yapılandırma

Tüm ayarlar ortam değişkenleriyle geçersiz kılınabilir.

| Değişken | Varsayılan | Açıklama |
| --- | --- | --- |
| `TSB_KASKO_BASE_URL` | `https://www.tsb.org.tr` | TSB uygulamasının kök adresi. |
| `TSB_KASKO_TIMEOUT` | `30` | İstek başına zaman aşımı, saniye. |
| `TSB_KASKO_MAX_RETRIES` | `3` | Geçici hatalarda deneme sayısı. |
| `TSB_KASKO_CACHE` | `1` | `0` verilirse önbellek tamamen kapanır. |
| `TSB_KASKO_CACHE_TTL` | `21600` | Marka ve model listelerinin önbellek ömrü, saniye. |
| `TSB_KASKO_CACHE_DIR` | `~/.cache/tsb-kasko` | Önbellek dizini. |
| `TSB_KASKO_TRANSPORT` | `stdio` | MCP taşıması: `stdio`, `http` veya `sse`. |
| `TSB_KASKO_HOST` | `127.0.0.1` | HTTP taşımasının dinleme adresi. |
| `TSB_KASKO_PORT` | `8000` | HTTP taşımasının portu. |
| `TSB_KASKO_MCP_PATH` | `/mcp` | ASGI uygulamasındaki uç nokta yolu. |

## Kullanılan TSB uçları

TSB bir API sözleşmesi yayımlamıyor. Aşağıdaki uçlar sitenin ön yüzünün kullandığı, kimlik doğrulaması ve çerez gerektirmeyen uçlardır. Hepsi `src/tsb_kasko/endpoints.py` içinde tek yerde tanımlıdır.

| Uç | Parametreler | Döner |
| --- | --- | --- |
| `GET /InsuranceData/GetVehicleYearList` | yok | Kapsanan model yılları |
| `GET /InsuranceData/GetVehicleBrandList` | `VehicleYear` | Markalar |
| `GET /InsuranceData/GetVehicleModelList` | `vehicleYear`, `VehicleBrandId` | Tipler |
| `GET /InsuranceData/GetInsuranceDatas` | `VehicleYear`, `VehicleModelId` | Kasko bedeli ve araç kodu |
| `GET /InsuranceData/GetMonthList` | yok | Arşiv ayları |
| `GET /InsuranceData/GetInsuranceDataArchiveFile` | `Year`, `MonthId` | Aylık Excel dosyasının yolu |

İki ayrıntı dikkat çekicidir:

1. Marka listesindeki `VehicleBrandCode` alanı her zaman `0` gelir. Poliçede yazan gerçek marka kodu yalnızca `GetInsuranceDatas` yanıtında dolu gelir.
2. `GetMonthList` içindeki `Id` alanı takvim ayı değildir. Ocak `2`, Ekim ise `1` kimliğine sahiptir. Bu yüzden istemci ay kimliğini hesaplamaz, canlı listeden çözer.

## Geliştirme

```bash
uv pip install -e ".[dev,http]"

pytest              # 47 test, kayıtlı gerçek yanıtlarla
ruff check .        # lint
ruff format .       # biçimlendirme
mypy src/tsb_kasko  # strict tip denetimi
```

Testler TSB'den alınmış gerçek yanıtların birebir kopyalarını kullanır, bu sayede sözleşme değiştiğinde testler kırılır.

## Sorumluluk reddi

Bu proje TSB ile ilişkili değildir ve TSB tarafından desteklenmemektedir. Veriler TSB'nin herkese açık sayfasından alınır. TSB'nin kendi ifadesiyle, bu değerlerin işlemlerde kullanılmasından doğacak sonuçlardan TSB sorumluluk kabul etmemektedir. Resmî kaynak her zaman [tsb.org.tr](https://www.tsb.org.tr/tr/kasko-deger-listesi) adresidir.

Uçlar TSB tarafından belgelenmediği için haber verilmeden değişebilir. Böyle bir durumda `src/tsb_kasko/endpoints.py` dosyasını güncellemek yeterlidir.

## Lisans

[MIT](LICENSE)
