# Değişiklik günlüğü

Bu dosyanın biçimi [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/)
temellidir ve proje [Semantik Sürümleme](https://semver.org/lang/tr/) kullanır.

## [Yayımlanmamış]

### Eklendi

- Cross-OS geliştirme ayarları: `.editorconfig`, satır sonlarını depoda LF'ye
  sabitleyen `.gitattributes` ve Python sürümünü sabitleyen `.python-version`.
- `.docker/python/Dockerfile` ile iki aşamalı, kök olmayan kullanıcıyla çalışan
  konteyner ve HTTP taşımasını yayımlayan `compose.yaml`.
- Dev Containers desteği ve önerilen VS Code eklentileri.
- `pre-commit` yapılandırması: ruff, mypy, satır sonu ve boşluk denetimleri.
- CLI, önbellek, yapılandırma, modeller ve ASGI uygulaması için test modülleri.
  Toplam 146 test, %99 kapsam.
- CI'da Windows ve macOS işleri, Python 3.14 sürümü, konteyner derleme adımı ve
  depoya CRLF girmediğini doğrulayan denetim.
- PyPI'ye güvenilir yayımlama (trusted publishing) yapan sürüm iş akışı.
- Katkı rehberi, davranış kuralları, güvenlik politikası, issue ve pull request
  şablonları, Dependabot yapılandırması.

### Değiştirildi

- Geliştirme bağımlılıkları PEP 735 `[dependency-groups]` altına taşındı;
  `[project.optional-dependencies]` yalnızca kullanıcıya yönelik `http` ekini
  barındırıyor.
- `uv.lock` depoya eklendi, böylece CI ve konteyner aynı sürümleri kuruyor.
- `LICENSE` yalnızca özgün İngilizce MIT metnini içeriyor; Türkçe bilgilendirme
  çevirisi [`docs/lisans.md`](docs/lisans.md) dosyasına taşındı. Bunun nedeni,
  GitHub ve PyPI'nin lisans tespitini metin eşleşmesiyle yapması.

## [0.1.0] — 2026-08-18

İlk sürüm.

### Eklendi

- TSB kasko değer listesini okuyan asenkron Python istemcisi: yeniden deneme,
  disk üstü önbellek ve Türkçe metin/sayı normalleştirmesi.
- Sekiz araç sunan MCP sunucusu; `stdio`, streamable HTTP ve SSE taşımaları.
- Tablo, JSON ve CSV çıktısı veren `tsb-kasko` komut satırı aracı.
- Aylık arşiv listelerini indiren ve içinde arama yapan Excel okuyucusu.
- Gerçek TSB yanıtlarının birebir kopyalarıyla çalışan 47 test.

[Yayımlanmamış]: https://github.com/hmtkyn/tsb-kasko-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hmtkyn/tsb-kasko-mcp/releases/tag/v0.1.0
