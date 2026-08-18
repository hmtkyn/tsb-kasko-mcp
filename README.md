# tsb-kasko-mcp — TSB Kasko Değer Listesi için MCP sunucusu ve CLI

Türkiye Sigorta Birliği'nin (TSB) yayımladığı **Kasko Değer Listesi**'ni sorgulayan
açık kaynak **MCP sunucusu**, **komut satırı aracı** ve **Python istemcisi**.
Claude, ChatGPT, Gemini ve Cursor içinden "2025 model Audi A3'ün kasko bedeli ne
kadar" diye sorabilir; terminalden `tsb-kasko lookup 2025 "audi a3"` yazabilir ya
da kendi Python projenizde kütüphane olarak kullanabilirsiniz.

[![CI](https://github.com/hmtkyn/tsb-kasko-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/hmtkyn/tsb-kasko-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-uyumlu-8A2BE2)](https://modelcontextprotocol.io/)
[![Lisans: MIT](https://img.shields.io/badge/lisans-MIT-green)](LICENSE)
[![Kapsam](https://img.shields.io/badge/test%20kapsam%C4%B1-%99-brightgreen)](#geliştirme)

Kasko değer listesi, Türkiye'de satılan her kasko poliçesinin fiyatlandığı
referans bedeldir. Aynı zamanda pert (tam hasar) ve çalınma durumlarında ödenecek
tutarın da dayanağıdır. Bu proje, TSB'nin web sitesinin arka planında kullandığı
ve kimlik doğrulaması gerektirmeyen uçları tiplenmiş bir istemciye dönüştürür.

| Arayüz | Nasıl çalıştırılır | Kime göre |
| --- | --- | --- |
| MCP sunucusu | `tsb-kasko-mcp` | Claude, ChatGPT, Gemini, Cursor |
| Komut satırı | `tsb-kasko lookup 2025 "audi a3"` | Terminal, betik, CI |
| Python istemcisi | `from tsb_kasko import TsbKaskoClient` | Kendi uygulamanız |

Paket kurulduğunda iki komut birden gelir; ayrı bir CLI paketi kurmanıza gerek yoktur.

## İçindekiler

- [Ne işe yarar](#ne-işe-yarar)
- [Kurulum](#kurulum)
- [MCP kurulumu](#mcp-kurulumu)
- [MCP araçları](#mcp-araçları)
- [Komut satırı kullanımı](#komut-satırı-kullanımı)
- [Python kütüphanesi olarak](#python-kütüphanesi-olarak)
- [Docker](#docker)
- [Yapılandırma](#yapılandırma)
- [Kullanılan TSB uçları](#kullanılan-tsb-uçları)
- [Proje yapısı](#proje-yapısı)
- [Geliştirme](#geliştirme)
- [Sık sorulanlar](#sık-sorulanlar)
- [Sorumluluk reddi](#sorumluluk-reddi)

## Ne işe yarar

- **Yapay zekâ asistanından kasko bedeli sorgulama.** Claude, ChatGPT ve Gemini
  içinden doğal dille sorarsınız, model aracı çağırır, güncel bedeli döner.
- **Terminalden sorgulama.** `tsb-kasko lookup 2025 "audi a3 sportback"` komutu
  tabloyu, JSON'u veya CSV'yi doğrudan basar.
- **Poliçedeki araç kodu.** Sonuçlar sigortacının sorduğu `marka kodu - model kodu`
  ikilisini de içerir, örneğin `9-1616`.
- **Geçmiş listeler.** TSB her ay listeyi yeniden yayımlar. Geçmiş ayların Excel
  dosyasını indirebilir veya içinde arama yapabilirsiniz.
- **Python kütüphanesi.** Kendi projenizde `TsbKaskoClient` sınıfını doğrudan
  kullanabilirsiniz.

## Kurulum

Ön koşul: [uv](https://docs.astral.sh/uv/). Python'u da o kurar.

Kurulum yapmadan denemek için:

```bash
uvx --from git+https://github.com/hmtkyn/tsb-kasko-mcp tsb-kasko lookup 2025 "audi a3 sportback"
```

Kalıcı kurulum:

```bash
uv tool install git+https://github.com/hmtkyn/tsb-kasko-mcp
```

veya pip ile:

```bash
pip install git+https://github.com/hmtkyn/tsb-kasko-mcp
```

> Paket henüz PyPI'de yayımlanmadı. Yayımlandığında `uv tool install tsb-kasko-mcp`
> ve `pip install tsb-kasko-mcp` de çalışacak; yayımlama iş akışı depoda hazır.

Depodan geliştirme kurulumu için [Geliştirme](#geliştirme) bölümüne bakın.

## MCP kurulumu

Sunucu hem `stdio` hem de streamable HTTP taşımasını destekler, bu yüzden hem
masaüstü istemcileri hem de barındırılan bağlayıcılar için çalışır.

### Claude Code

```bash
claude mcp add tsb-kasko -- uvx --from git+https://github.com/hmtkyn/tsb-kasko-mcp tsb-kasko-mcp
```

### Claude Desktop

`claude_desktop_config.json` dosyasına ekleyin:

```json
{
  "mcpServers": {
    "tsb-kasko": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/hmtkyn/tsb-kasko-mcp", "tsb-kasko-mcp"]
    }
  }
}
```

### Cursor / VS Code

`.cursor/mcp.json` veya çalışma alanındaki `.vscode/mcp.json` dosyasına aynı
`mcpServers` bloğunu ekleyin.

### Gemini CLI

`~/.gemini/settings.json` dosyasına ekleyin:

```json
{
  "mcpServers": {
    "tsb-kasko": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/hmtkyn/tsb-kasko-mcp", "tsb-kasko-mcp"]
    }
  }
}
```

### ChatGPT ve diğer uzak istemciler

ChatGPT bağlayıcıları sunucuya HTTP üzerinden ulaşır. Sunucuyu HTTP modunda
çalıştırın:

```bash
TSB_KASKO_TRANSPORT=http TSB_KASKO_HOST=0.0.0.0 TSB_KASKO_PORT=8000 tsb-kasko-mcp
```

veya herhangi bir ASGI sunucusuyla:

```bash
uvicorn tsb_kasko.asgi:app --host 0.0.0.0 --port 8000
```

Uç nokta varsayılan olarak `http://sunucu:8000/mcp` adresinde yayınlanır. En
kolay yol için [Docker](#docker) bölümüne bakın.

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

`kasko_download_archive` dışındaki tüm araçlar `readOnlyHint` ile işaretlidir;
yani istemci onlar için onay istemeden çağrı yapabilir.

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

## Docker

Konteyner, MCP sunucusunu HTTP taşımasıyla yayımlar. İki aşamalı derleme kullanır,
kök olmayan bir kullanıcıyla çalışır ve dosya sistemi salt okunurdur.

```bash
docker compose up --build
# -> http://127.0.0.1:8000/mcp
```

Yalnızca imajı derleyip CLI'yi çalıştırmak için:

```bash
docker build -f .docker/python/Dockerfile -t tsb-kasko-mcp .
docker run --rm --entrypoint tsb-kasko tsb-kasko-mcp lookup 2025 "audi a3"
```

Python sürümü imaja `ARG PYTHON_VERSION` ile sabitlenmiştir ve depodaki
`.python-version` ile aynı sürümü kullanır.

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

TSB bir API sözleşmesi yayımlamıyor. Aşağıdaki uçlar sitenin ön yüzünün
kullandığı, kimlik doğrulaması ve çerez gerektirmeyen uçlardır. Hepsi
[`src/tsb_kasko/endpoints.py`](src/tsb_kasko/endpoints.py) içinde tek yerde
tanımlıdır.

| Uç | Parametreler | Döner |
| --- | --- | --- |
| `GET /InsuranceData/GetVehicleYearList` | yok | Kapsanan model yılları |
| `GET /InsuranceData/GetVehicleBrandList` | `VehicleYear` | Markalar |
| `GET /InsuranceData/GetVehicleModelList` | `vehicleYear`, `VehicleBrandId` | Tipler |
| `GET /InsuranceData/GetInsuranceDatas` | `VehicleYear`, `VehicleModelId` | Kasko bedeli ve araç kodu |
| `GET /InsuranceData/GetMonthList` | yok | Arşiv ayları |
| `GET /InsuranceData/GetInsuranceDataArchiveFile` | `Year`, `MonthId` | Aylık Excel dosyasının yolu |

İki ayrıntı dikkat çekicidir:

1. Marka listesindeki `VehicleBrandCode` alanı her zaman `0` gelir. Poliçede
   yazan gerçek marka kodu yalnızca `GetInsuranceDatas` yanıtında dolu gelir.
2. `GetMonthList` içindeki `Id` alanı takvim ayı değildir. Ocak `2`, Ekim ise `1`
   kimliğine sahiptir. Bu yüzden istemci ay kimliğini hesaplamaz, canlı listeden
   çözer.

## Proje yapısı

Üç arayüz de aynı çekirdeğin üstünde duran ince kabuklardır. Bu yüzden hepsi tek
repoda yaşar: TSB bir ucu yeniden adlandırdığında düzeltme tek dosyada yapılır,
üç ayrı sürüm senkronu gerekmez.

```
src/tsb_kasko/
├── client.py      # çekirdek: HTTP, yeniden deneme, önbellek
├── endpoints.py   # TSB uçlarının tek tanım yeri
├── models.py      # Pydantic modelleri
├── parsing.py     # zarf açma, Türkçe sayı ve metin normalleştirme
├── archive.py     # aylık Excel listelerinin okuyucusu
├── server.py      # kabuk 1: FastMCP sunucusu
├── cli.py         # kabuk 2: Typer komut satırı
└── asgi.py        # HTTP taşıması için ASGI uygulaması
```

Aynı düzen `github/github-mcp-server`, `microsoft/playwright-mcp` ve
`grafana/mcp-grafana` projelerinde de kullanılıyor: ortak çekirdek, üstünde
birden fazla giriş noktası.

## Geliştirme

```bash
git clone https://github.com/hmtkyn/tsb-kasko-mcp.git
cd tsb-kasko-mcp
uv sync --all-extras --all-groups
uv run pre-commit install
```

```bash
uv run pytest                                  # 146 test, kayıtlı gerçek yanıtlarla
uv run pytest --cov --cov-report=term-missing  # kapsam raporu
uv run ruff check .                            # lint
uv run ruff format .                           # biçimlendirme
uv run mypy src/tsb_kasko                      # strict tip denetimi
uv run pre-commit run --all-files              # CI'ın yaptığının tamamı
```

Testler TSB'den alınmış gerçek yanıtların birebir kopyalarını kullanır, bu sayede
sözleşme değiştiğinde testler kırılır. Ağa çıkan test yoktur.

### Windows, macOS ve Linux'ta aynı sonuç

Bu depo üç işletim sisteminde de aynı davranacak şekilde ayarlandı:

- [`.python-version`](.python-version) Python sürümünü **3.14**'e sabitler; `uv`
  gerekirse indirir. Paketin desteklediği aralık ise `>=3.11` ve CI dört sürümü
  birden test eder.
- [`.gitattributes`](.gitattributes) her metin dosyasını depoda **LF** ile saklar.
  Windows'ta `core.autocrlf` açık olsa bile depoya CRLF girmez. CI'da bir adım
  bunu ayrıca denetler.
- [`.editorconfig`](.editorconfig) girinti, kodlama ve satır sonunu editörden
  bağımsız sabitler.
- [`.devcontainer/`](.devcontainer/) ile hiçbir şey kurmadan konteyner içinde
  geliştirebilirsiniz.

Ayrıntılar için [CONTRIBUTING.md](CONTRIBUTING.md).

## Sık sorulanlar

**Kasko değeri nedir, neye göre belirlenir?**
TSB'nin her ay yayımladığı, marka ve tip bazında referans araç bedelidir.
Sigorta şirketleri poliçe primini ve hasar ödemesini bu bedel üzerinden hesaplar.

**Aracımın kasko bedelini nasıl öğrenirim?**
`tsb-kasko lookup <model_yılı> "<marka ve tip>"` komutunu çalıştırın ya da MCP
sunucusunu kurup asistanınıza sorun. Resmî kaynak her zaman
[tsb.org.tr](https://www.tsb.org.tr/tr/kasko-deger-listesi) adresidir.

**Poliçedeki araç kodu nedir?**
Sigortacının sorduğu `marka kodu - model kodu` ikilisidir, örneğin `9-1616`.
Sonuçlarda `vehicle_code` alanında döner.

**Hangi model yılları kapsanıyor?**
2012 ve sonrası. Güncel listeyi `tsb-kasko years` ile görebilirsiniz.

**Geçmiş bir ayın listesine ulaşabilir miyim?**
Evet. `tsb-kasko archive search 2025 2 --query "sahin"` geçmiş ayın Excel
dosyasında arar, `archive download` ise dosyanın kendisini indirir.

**Bu proje resmî mi?**
Hayır. Aşağıdaki sorumluluk reddine bakın.

## Sorumluluk reddi

Bu proje TSB ile ilişkili değildir ve TSB tarafından desteklenmemektedir. Veriler
TSB'nin herkese açık sayfasından alınır. TSB'nin kendi ifadesiyle, bu değerlerin
işlemlerde kullanılmasından doğacak sonuçlardan TSB sorumluluk kabul etmemektedir.
Resmî kaynak her zaman [tsb.org.tr](https://www.tsb.org.tr/tr/kasko-deger-listesi)
adresidir.

Uçlar TSB tarafından belgelenmediği için haber verilmeden değişebilir. Böyle bir
durumda [`src/tsb_kasko/endpoints.py`](src/tsb_kasko/endpoints.py) dosyasını
güncellemek yeterlidir.

## Katkı ve lisans

- Katkı rehberi: [CONTRIBUTING.md](CONTRIBUTING.md)
- Davranış kuralları: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Güvenlik politikası: [SECURITY.md](SECURITY.md)
- Değişiklik günlüğü: [CHANGELOG.md](CHANGELOG.md)

[MIT](LICENSE) lisansı ile yayımlanmıştır. Türkçe bilgilendirme çevirisi:
[docs/lisans.md](docs/lisans.md).
