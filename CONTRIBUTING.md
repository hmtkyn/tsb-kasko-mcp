# Katkı rehberi

Katkıya açığız. Hata bildirimi, belge düzeltmesi ve kod katkısı; hepsi işe yarar.

Bu depoda tek bir dil kuralı var ve karışık görünse de nedeni basit:

- **Türkçe:** README, bu rehber, issue ve pull request açıklamaları, commit
  mesajları, CHANGELOG girdileri.
- **İngilizce:** kod içindeki her şey — docstring'ler, satır içi yorumlar,
  değişken ve fonksiyon adları, test adları, hata mesajları, MCP araç
  açıklamaları.

Kod İngilizce çünkü MCP araç açıklamalarını okuyan taraf bir dil modeli ve
paketi kuran herkes Türkçe bilmiyor. Belgeler Türkçe çünkü bu verinin kullanıcısı
Türkiye'de.

## Geliştirme ortamı

Tek ön koşul [uv](https://docs.astral.sh/uv/). Python'u da o kuruyor, ayrıca bir
Python kurulumuna gerek yok.

```bash
git clone https://github.com/hmtkyn/tsb-kasko-mcp.git
cd tsb-kasko-mcp
uv sync --all-extras --all-groups
uv run pre-commit install
```

`uv sync`, depodaki [`.python-version`](.python-version) dosyasını okur ve
gerekiyorsa o sürümü indirir. Yani Windows, macOS ve Linux'ta aynı Python
sürümüyle çalışırsınız.

### Python sürümü politikası

İki ayrı sayı var, karıştırmayın:

| Nerede | Sürüm | Neden |
| --- | --- | --- |
| `.python-version`, Dockerfile, CI'ın lint adımı | **3.14** | Geliştirme ve derleme hep tek sürümde olsun diye sabitlendi. |
| `pyproject.toml` içindeki `requires-python` | **>=3.11** | Paketi kuran kullanıcıyı en yeni sürüme zorlamamak için. |

CI, testleri 3.11'den 3.14'e kadar dört sürümde birden çalıştırır. Yani
`requires-python` bir temenni değil, ölçülen bir söz.

## Günlük komutlar

Hepsi her işletim sisteminde aynı; `make` gibi platforma bağlı bir ara katman
bilerek eklenmedi.

```bash
uv run pytest                                  # testler
uv run pytest --cov --cov-report=term-missing  # kapsam raporuyla
uv run ruff check .                            # lint
uv run ruff format .                           # biçimlendirme
uv run mypy src/tsb_kasko                      # strict tip denetimi
uv run pre-commit run --all-files              # CI'ın yaptığının tamamı
```

Son komut yerelde geçiyorsa CI'da da geçer. Kurulumu buna göre yapıldı.

## Editör ve satır sonu ayarları

Depo Windows, macOS ve Linux'ta birlikte çalışacak şekilde ayarlandı:

- [`.gitattributes`](.gitattributes) her metin dosyasını depoda **LF** ile
  saklar. Windows'ta `core.autocrlf` açık olsa bile depoya CRLF girmez. Tek
  istisna `.bat`, `.cmd` ve `.ps1` dosyaları; onlar CRLF olmadan çalışmaz.
- [`.editorconfig`](.editorconfig) girinti, kodlama ve satır sonunu editör
  bağımsız sabitler. VS Code, PyCharm, Vim ve Sublime bunu kutudan okur.
- CI'da bir adım, depoya CRLF ile giren dosya olup olmadığını denetler.

Eski bir kopyada satır sonları karıştıysa:

```bash
git add --renormalize .
```

## Docker ile geliştirme

Yerelde Python kurmak istemiyorsanız:

```bash
docker compose up --build      # HTTP taşımasıyla sunucu, http://127.0.0.1:8000/mcp
```

VS Code veya başka bir Dev Containers istemcisi kullanıyorsanız
[`.devcontainer/`](.devcontainer/) hazır; "Reopen in Container" demeniz yeterli.

## Pull request açmadan önce

1. `main` üzerinden bir dal açın: `git switch -c ozellik/kisa-ad`.
2. Değişikliğinizi test edin. Yeni davranışın testi yoksa PR eksiktir.
3. `uv run pre-commit run --all-files` çalıştırın.
4. Kullanıcıya görünen bir değişiklikse [`CHANGELOG.md`](CHANGELOG.md) içindeki
   `Yayımlanmamış` başlığına bir satır ekleyin.
5. PR açıklamasında **ne** değiştiğini değil **neden** değiştiğini yazın.

Commit mesajları [Conventional Commits](https://www.conventionalcommits.org/tr/)
biçiminde ve Türkçe:

```
feat: arşiv listesine model yılı sütunu eklendi
fix: ondalık ayırıcısı virgül olan bedeller yanlış okunuyordu
docs: MCP kurulum bölümü Gemini CLI için güncellendi
```

## Testler hakkında

Testler ağa çıkmaz. `tests/payloads.py` içindeki veriler TSB'den alınmış
**birebir** yanıtlardır; elle sadeleştirilmiş taklitleri değil. Bunun bir amacı
var: TSB bir alanı yeniden adlandırdığında test kırılsın istiyoruz.

Yeni bir uç eklerken:

1. Gerçek yanıtı `tests/payloads.py` dosyasına olduğu gibi ekleyin.
2. Ucu [`src/tsb_kasko/endpoints.py`](src/tsb_kasko/endpoints.py) içinde
   tanımlayın; URL'yi başka bir yere yazmayın.
3. İstemci, CLI ve MCP aracı için ayrı ayrı test yazın.

Kapsam oranı %95'in altına düşerse test adımı başarısız olur.

## TSB uçları değişirse

Uçların tamamı [`src/tsb_kasko/endpoints.py`](src/tsb_kasko/endpoints.py)
dosyasında toplandı. TSB bir yol veya parametre adını değiştirirse düzeltme tek
dosyada yapılır. Böyle bir durumu fark ederseniz issue açarken tarayıcının ağ
sekmesinden aldığınız isteği de ekleyin; düzeltmeyi hızlandırır.

## Davranış kuralları

Bu projeye katkı verirken [Davranış Kuralları](CODE_OF_CONDUCT.md) belgesini
kabul etmiş sayılırsınız.
