# BlockBlastinator

Block Blast için hamle danışmanı. Oyundan bir ekran görüntüsü alıp `index.html` sayfasına yüklüyorsun. Sayfa 8×8 tahtayı ve alttaki üç parçayı okuyor, sonra parçaları hangi sırayla ve nereye koyman gerektiğini gösteriyor.

Sayfa tek bir HTML dosyası, kurulum gerektirmiyor. Her şey tarayıcıda çalışıyor, görüntü hiçbir yere gönderilmiyor.

## iPhone'da kullanım

1. Oyundayken ekran görüntüsü al.
2. Safari'de sayfayı aç ve **Ekran görüntüsü seç** ile fotoğrafı yükle.
3. Renkli numaralar (1, 2, 3) parçaları koyma sırasını gösteriyor.

İlk seferde tahta ya da parça alanı yanlış yerde çıkabilir. Bunu bir kere ayarlaman yeterli:

- **Tahtayı işaretle** düğmesine bas, sonra görüntüde tahtanın etrafına kutu çiz.
- **Parça alanını işaretle** düğmesine bas, sonra alttaki üç parçanın durduğu bandı çiz.
- Yanlış okunan hücre olursa **Okunanı düzelt** bölümünde üzerine dokunarak düzeltebilirsin.

Ayarlar tarayıcıda saklanıyor.

## Nasıl çalışır

- **Okuma:** Tahtada en koyu hücre "boş" olarak kabul ediliyor, rengi ondan yeterince farklı olan hücreler "dolu" sayılıyor. Parçalar arka plan renginden ayrıştırılıyor, sonra parça bloğu boyutuna göre ızgaraya bölünüyor.
- **Çözücü:** Üç parçanın bütün sıraları ve konumları deneniyor. Tahta bit maskesi olarak tutuluyor, aynı durumlar tekrar hesaplanmıyor. Sonuç tahtası şu kriterlere göre puanlanıyor:
  - temizlenen satır ve sütunlar (aynı anda birden fazlası için kombo bonusu),
  - dolu hücre sayısı,
  - kapalı kalmış delikler,
  - satır ve sütunlardaki dolu-boş geçişleri,
  - 3×3 ve 1×5 gibi büyük parçaların hâlâ sığıp sığmadığı.

## Otomatik oynama (iPhone + Mac)

`bot/` klasöründeki Python botu oyunu kendi kendine oynar. Döngüsü şöyle: ekran görüntüsü al → tahtayı oku → çöz → parçayı sürükle → parçanın doğru yere düşüp düşmediğini kontrol et.

Telefona dokunma işini Apple'ın test altyapısı üzerinde çalışan **WebDriverAgent** yapar. WebDriverAgent'ı başlatmak için Mac gerekiyor. Bot da Mac'te çalışır.

### 1. Bir kerelik hazırlık

1. Mac'e **Xcode**'u App Store'dan kur. Xcode → Settings → Accounts menüsünden Apple hesabınla giriş yap. Ücretsiz hesap yeterli.
2. iPhone'u kabloyla Mac'e bağla ve "Bu bilgisayara güven" sorusunu onayla.
3. iPhone'da **Geliştirici Modu**'nu aç: Ayarlar → Gizlilik ve Güvenlik → Geliştirici Modu. Telefon yeniden başlar.
4. WebDriverAgent'ı indir:
   ```bash
   git clone https://github.com/appium/WebDriverAgent.git
   ```
5. `WebDriverAgent.xcodeproj` dosyasını Xcode'da aç. **WebDriverAgentRunner** hedefinde Signing & Capabilities sekmesine git:
   - Team olarak kendi hesabını seç.
   - Bundle Identifier'ı benzersiz bir değerle değiştir, örneğin `com.batuhan.WebDriverAgentRunner`.
   - Aynı ayarı **WebDriverAgentLib** hedefinde de yap.
6. iPhone'un UDID'sini öğren: `xcrun xctrace list devices`
7. Mac'e `iproxy` aracını kur: `brew install libimobiledevice`
8. Botun kurulumu:
   ```bash
   cd BlockBlastinator/bot
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

### 2. Her oynamada

1. WebDriverAgent'ı başlat ve bu terminali açık bırak:
   ```bash
   cd WebDriverAgent
   xcodebuild -project WebDriverAgent.xcodeproj -scheme WebDriverAgentRunner \
     -destination 'id=<UDID>' -allowProvisioningUpdates test
   ```
   İlk seferde telefon geliştiriciye güvenmeni isteyecek: Ayarlar → Genel → VPN ve Cihaz Yönetimi → kendi hesabın → Güven. Sonra komutu tekrar çalıştır. Logda `ServerURLHere` satırı görünce hazırdır.
2. İkinci bir terminalde portu bilgisayara aktar:
   ```bash
   iproxy 8100 8100
   ```
3. Telefonda Block Blast'i aç, yeni bir oyun başlat.
4. Önce sadece okuma yap, dokunma:
   ```bash
   python play.py --advise
   ```
   `debug/son.png` dosyasını aç. Sarı kutular tahtanın ve parça alanının üstüne oturmalı, beyaz noktalar dolu hücrelerin üstünde olmalı. Oturmuyorsa `config.json` dosyasındaki `board` ve `tray` değerlerini düzelt. Bunlar ekranın oranları: 0 sol/üst kenar, 1 sağ/alt kenar. Web sayfasında görüntü üzerine kutu çizerek de bulabilirsin.
5. Oynat:
   ```bash
   python play.py
   ```
   Kısa bir deneme için `--max-moves 5` ekleyebilirsin. Durdurmak için Ctrl+C.

Notlar:

- **Kaydırma ayarı:** Oyun, sürüklenen parçayı parmağın biraz yukarısında gösteriyor. Bot ilk birkaç hamlede parçanın nereye düştüğüne bakıp bu kaymayı kendisi ölçüyor ve `config.json` dosyasındaki `drag_offset_pt` değerine kaydediyor.
- **Sürükleme sorunları:** Sürükleme çalışmazsa `--drag-api wda` seçeneğini dene. Satır temizleme animasyonu yetişmiyorsa `settle_ms` değerini artır.
- **İmza süresi:** Ücretsiz Apple hesabıyla imzalanan WebDriverAgent 7 gün geçerli. Süre dolunca 1. adımdaki komutu tekrar çalıştırman yeterli.
- **Kablosuz bağlantı:** Telefon ve Mac aynı Wi-Fi'daysa `iproxy` yerine WebDriverAgent logundaki adresi kullanabilirsin: `python play.py --wda http://192.168.x.x:8100`

### Telefonsuz test

`bot/dev/mock_wda.py` sahte bir WebDriverAgent sunucusu. Basit bir blok bulmacası çiziyor ve sürüklemeleri işliyor. Botu telefona bağlamadan denemek için:

```bash
python dev/mock_wda.py            # bir terminalde
python play.py --max-moves 50     # başka bir terminalde
```

## Web sayfasını yerelde çalıştırma

```bash
npx http-server@14.1.1 . -p 8765
```

Sonra tarayıcıda `http://localhost:8765` adresini aç.
