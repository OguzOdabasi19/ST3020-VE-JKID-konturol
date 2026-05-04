# ST3020 ve JKID Kontrol Arayüzü

Bu proje, seri port üzerinden çoklu servo motorların kontrolünü sağlamak amacıyla geliştirilmiş C# tabanlı bir masaüstü kullanıcı arayüzüdür. Kullanıcıların donanımla hızlı ve güvenilir bir şekilde haberleşmesini, farklı çalışma modları arasında geçiş yapmasını ve motor hareketlerini hassas bir şekilde yönetmesini sağlar.

## 🚀 Özellikler

* **Seri Port Haberleşmesi:** Bağlı cihazlarla (ST3020, JKID vb.) kesintisiz ve hızlı seri port iletişimi.
* **Çoklu Servo Motor Kontrolü:** Aynı anda birden fazla servo motorun pozisyon, hız ve ivme gibi parametrelerinin yönetimi.
* **Çalışma Modları:** Proje gereksinimlerine göre ayarlanabilen farklı operasyonel çalışma modları arasında kolay geçiş.
* **Kullanıcı Dostu Arayüz:** Karmaşık komutlara gerek kalmadan, butonlar ve sürgüler (slider) aracılığıyla görsel kontrol imkanı.
* **Hata Yakalama ve Bildirim:** Bağlantı kopuklukları veya geçersiz komut durumlarında kullanıcıyı anında bilgilendirme.

## 🛠️ Kullanılan Teknolojiler

* **Programlama Dili:** C#
* **Platform:** .NET Framework / Windows Forms (veya WPF)
* **Haberleşme Protokolü:** Serial Port (RS232/USB-Serial)

## ⚙️ Kurulum ve Kullanım

1.  Bu depoyu bilgisayarınıza klonlayın:
    ```bash
    git clone [https://github.com/OguzOdabasi19/ST3020-VE-JKID-konturol.git](https://github.com/OguzOdabasi19/ST3020-VE-JKID-konturol.git)
    ```
2.  Projeyi kullandığınız IDE (Visual Studio, SharpDevelop, VS Code vb.) ile açın.
3.  Uygulamayı derleyip çalıştırın (F5).
4.  Arayüz açıldığında, donanımınızın bağlı olduğu **COM Portunu** ve **Baud Rate** (Baud Hızı) değerini seçerek "Bağlan" butonuna tıklayın.
5.  Bağlantı sağlandıktan sonra arayüz üzerinden servo motorları kontrol etmeye başlayabilirsiniz.

## 📝 Gelecek Geliştirmeler (To-Do)

- [ ] Arayüze anlık veri akışını gösteren bir grafik (plotter) eklenmesi.
- [ ] Belirli hareket senaryolarının kaydedilip tekrar oynatılması (Makro özelliği).

