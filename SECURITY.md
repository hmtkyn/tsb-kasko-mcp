# Güvenlik politikası

## Desteklenen sürümler

| Sürüm | Destek |
| --- | --- |
| 0.1.x | ✅ |

Proje 1.0 öncesi olduğu için güvenlik düzeltmeleri yalnızca en son yayımlanan
sürüme uygulanır.

## Açık bildirme

Bir güvenlik açığı bulduysanız **issue açmayın**. Bunun yerine
[GitHub Security Advisories](https://github.com/hmtkyn/tsb-kasko-mcp/security/advisories/new)
üzerinden özel bildirim gönderin.

Bildiriminize şunları eklerseniz süreç hızlanır:

- Açığın türü ve etkisi.
- Yeniden üretme adımları veya kavram kanıtı.
- Etkilenen sürüm ve işletim sistemi.
- Varsa önerdiğiniz düzeltme.

İlk yanıtı **72 saat** içinde vermeyi hedefliyoruz. Doğrulanan bir açık için
düzeltme yayımlandıktan sonra, aksini istemediğiniz sürece bildirimi yapan kişiye
teşekkür notu eklenir.

## Bu projenin güvenlik yüzeyi

Kapsamı önceden bilmek, neyin açık sayıldığını netleştirir.

**Bu paket:**

- TSB'nin herkese açık uçlarına yalnızca `GET` isteği atar.
- Kimlik doğrulaması kullanmaz; saklanan bir kimlik bilgisi, anahtar veya jeton
  yoktur.
- Yanıtları `TSB_KASKO_CACHE_DIR` altına düz JSON olarak yazar. Bu dizinde
  yalnızca herkese açık araç değerleme verisi bulunur.
- `kasko_download_archive` aracı ve `tsb-kasko archive download` komutu dışında
  diske yazmaz.

**Bu yüzden ilgilendiğimiz sınıflar:**

- İndirme veya önbellek yollarında dizin dışına çıkma (path traversal).
- MCP araç girdilerinin dosya sistemine veya alt sürece sızması.
- Bağımlılıklardaki bilinen açıklar.
- HTTP taşıması açıkken sunucunun beklenmedik bir yüzey açması.

**Kapsam dışı:**

- TSB'nin kendi altyapısındaki sorunlar. Bunları doğrudan
  [TSB](https://www.tsb.org.tr) ile paylaşın.
- Yayımlanan kasko değerlerinin doğruluğu. Bu proje veriyi aktarır, üretmez.
- Sunucuyu kendi isteğiyle `0.0.0.0` üzerinde ve kimlik doğrulaması olmadan
  açan kurulumlar. HTTP taşıması varsayılan olarak `127.0.0.1` dinler; dışarı
  açıyorsanız önüne bir ters vekil ve kimlik doğrulama koymak sizin
  sorumluluğunuzdadır.

## Bağımlılıklar

Bağımlılıklar [`uv.lock`](uv.lock) ile sabitlenir ve Dependabot tarafından
haftalık taranır. Güvenlik güncellemeleri öncelikli olarak birleştirilir.
