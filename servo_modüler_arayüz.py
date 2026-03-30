import sys
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QComboBox, QPushButton, 
                             QTableWidget, QTableWidgetItem, QLineEdit, 
                             QLabel, QTextEdit, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

class ServoArayuzu(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("STM32 Çoklu Modüler Kontrol Merkezi (ST3020 / JKID)")
        self.resize(1300, 680)

        self.seri_port = serial.Serial()
        self.tampon_veri = bytearray() 
        self.son_gonderilenler = {}
        self.mevcut_mod = ""
        self.mevcut_cihaz = "ST3020 Servo"  # Varsayılan cihaz tipi
        
        self.timer_oku = QTimer()
        self.timer_oku.timeout.connect(self.seri_porttan_oku)

        # --- ARAYÜZ RENKLENDİRME (QSS) ---
        stil_dosyasi = """
            QMainWindow { background-color: #2b2b2b; }
            QGroupBox {
                font-weight: bold; font-size: 14px;
                border: 2px solid #555555; border-radius: 6px; margin-top: 15px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }
            QGroupBox#grup_okuma { color: #00FF7F; border-color: #008040; }
            QGroupBox#grup_yazma { color: #FF9900; border-color: #B36B00; }
            
            QLabel { color: #E0E0E0; font-weight: bold; font-size: 12px; }
            QComboBox {
                background-color: #3b3b3b; color: #ffffff; border: 1px solid #777777; padding: 6px; border-radius: 4px; font-size: 12px; min-width: 150px;
            }
            QPushButton { color: white; padding: 8px; border-radius: 5px; font-weight: bold; font-size: 12px; }
            
            QTableWidget { background-color: #1e1e1e; color: #ffffff; gridline-color: #444444; font-size: 12px; border: none; }
            QHeaderView::section { background-color: #333333; color: #E0E0E0; padding: 5px; border: 1px solid #444444; font-weight: bold; }
            
            QLineEdit { background-color: #3b3b3b; color: #ffffff; font-weight: bold; border: 1px solid #777777; border-radius: 3px; padding: 2px 5px; }
            QLineEdit:focus { background-color: #505050; border: 1px solid #FF9900; }
            QTextEdit { background-color: #0c0c0c; color: #00FF00; font-family: 'Consolas'; font-size: 13px; border: 1px solid #555555; }
        """
        self.setStyleSheet(stil_dosyasi)

        merkez_widget = QWidget()
        self.setCentralWidget(merkez_widget)
        ana_layout = QVBoxLayout(merkez_widget)

        # ==========================================
        # 1. BÖLÜM: BAĞLANTI AYARLARI
        # ==========================================
        baglanti_layout = QHBoxLayout()
        self.combo_port = QComboBox()
        self.portlari_listele() 
        
        self.combo_baud = QComboBox()
        self.combo_baud.addItems(["9600", "14400", "19200", "28800", "38400", "56000", 
                                  "57600", "115200", "128000", "230400", "256000", "460800", "912600"])
        self.combo_baud.setCurrentText("115200")
        
        self.btn_baglanti = QPushButton("BAĞLAN")
        self.btn_baglanti.setStyleSheet("background-color: #28a745;") 
        self.btn_baglanti.clicked.connect(self.baglanti_tetikle)
        
        baglanti_layout.addWidget(QLabel("Port:"))
        baglanti_layout.addWidget(self.combo_port)
        baglanti_layout.addWidget(QLabel("Baud Rate:"))
        baglanti_layout.addWidget(self.combo_baud)
        baglanti_layout.addWidget(self.btn_baglanti)
        baglanti_layout.addStretch()
        ana_layout.addLayout(baglanti_layout)

        # ==========================================
        # 2. BÖLÜM: CİHAZ TİPİ SEÇİMİ
        # ==========================================
        cihaz_layout = QHBoxLayout()
        cihaz_layout.addWidget(QLabel("Cihaz Tipi:"))
        
        self.combo_cihaz = QComboBox()
        self.combo_cihaz.addItems(["ST3020 Servo", "JKID Motor"])
        self.combo_cihaz.setStyleSheet("background-color: #8B008B; font-weight: bold; font-size: 14px; min-width: 200px;")
        self.combo_cihaz.currentTextChanged.connect(self.cihaz_degisti)
        
        cihaz_layout.addWidget(self.combo_cihaz)
        cihaz_layout.addStretch()
        ana_layout.addLayout(cihaz_layout)

        # ==========================================
        # 3. BÖLÜM: MOD SEÇİMİ
        # ==========================================
        mod_layout = QHBoxLayout()
        mod_layout.addWidget(QLabel("Mevcut Çalışma Modu:"))
        
        self.combo_mod = QComboBox()
        self.combo_mod.addItems(["Multi-Turn Modu", "Motor Modu", "Servo Modu", "ID Değiştirme Modu"])
        self.combo_mod.setStyleSheet("background-color: #0055a4; font-weight: bold; font-size: 14px;")
        self.combo_mod.currentTextChanged.connect(self.arayuzu_guncelle) 
        
        mod_layout.addWidget(self.combo_mod)
        mod_layout.addStretch()
        ana_layout.addLayout(mod_layout)

        # ==========================================
        # 4. BÖLÜM: TABLOLAR
        # ==========================================
        orta_layout = QHBoxLayout() 

        grup_okuma = QGroupBox("← Gelen Veriler (Okuma)")
        grup_okuma.setObjectName("grup_okuma")
        okuma_layout = QVBoxLayout()
        self.tablo_okuma = QTableWidget()
        self.tablo_okuma.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        okuma_layout.addWidget(self.tablo_okuma)
        grup_okuma.setLayout(okuma_layout)

        grup_yazma = QGroupBox("Giden Komutlar (Yazma) →")
        grup_yazma.setObjectName("grup_yazma")
        yazma_layout = QVBoxLayout()
        self.tablo_yazma = QTableWidget()
        self.tablo_yazma.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        yazma_layout.addWidget(self.tablo_yazma)
        grup_yazma.setLayout(yazma_layout)

        orta_layout.addWidget(grup_okuma)
        orta_layout.addWidget(grup_yazma)
        ana_layout.addLayout(orta_layout, stretch=2)

        self.tablo_okuma.verticalScrollBar().valueChanged.connect(self.tablo_yazma.verticalScrollBar().setValue)
        self.tablo_yazma.verticalScrollBar().valueChanged.connect(self.tablo_okuma.verticalScrollBar().setValue)

        # ==========================================
        # 5. BÖLÜM: LOG EKRANI
        # ==========================================
        grup_log = QGroupBox("Terminal & Sistem Monitörü")
        log_layout = QVBoxLayout()
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.append("[SİSTEM] Sistem Hazır. Cihazlar yalnızca seri porttan veri geldiğinde görünür.")
        log_layout.addWidget(self.text_log)
        grup_log.setLayout(log_layout)
        ana_layout.addWidget(grup_log, stretch=1)

        self.arayuzu_guncelle(self.combo_mod.currentText())

    # ==========================================
    # --- CİHAZ TİPİ DEĞİŞİM ---
    # ==========================================
    def cihaz_degisti(self, secilen_cihaz):
        self.mevcut_cihaz = secilen_cihaz
        
        # Mod listesini cihaz tipine göre güncelle
        self.combo_mod.blockSignals(True)
        self.combo_mod.clear()
        
        if secilen_cihaz == "ST3020 Servo":
            self.combo_mod.addItems(["Multi-Turn Modu", "Motor Modu", "Servo Modu", "ID Değiştirme Modu"])
        elif secilen_cihaz == "JKID Motor":
            self.combo_mod.addItems(["Absolute Pozisyon Modu", "Relative Pozisyon Modu", 
                                     "Hız Kontrol Modu", "Tork Kontrol Modu", "Fault Reset Modu"])
        
        self.combo_mod.blockSignals(False)
        
        # Tabloları temizle ve yeni cihaz için sıfırla
        self.tablo_okuma.clear()
        self.tablo_yazma.clear()
        self.tablo_okuma.setRowCount(0)
        self.tablo_yazma.setRowCount(0)
        self.son_gonderilenler.clear()
        
        self.text_log.append(f"[CİHAZ DEĞİŞİMİ] Cihaz tipi '{secilen_cihaz}' olarak değiştirildi.")
        self.arayuzu_guncelle(self.combo_mod.currentText())

    # ==========================================
    # --- DİNAMİK ARAYÜZ YAPILANDIRMASI (HAFIZALI) ---
    # ==========================================
    def arayuzu_guncelle(self, secilen_mod):
        self.mevcut_mod = secilen_mod
        self.son_gonderilenler.clear() 
        
        # 1. ADIM: Tabloları silmeden önce ekrandaki mevcut ID'leri yedekle
        mevcut_idler = []
        for satir in range(self.tablo_okuma.rowCount()):
            item = self.tablo_okuma.item(satir, 0)
            if item:
                mevcut_idler.append(item.text())
        
        # 2. ADIM: Tabloları güvenle temizle
        self.tablo_okuma.clear()
        self.tablo_yazma.clear()
        self.tablo_okuma.setRowCount(0)
        self.tablo_yazma.setRowCount(0)
        
        # 3. ADIM: Cihaz tipine ve moda göre sütun başlıklarını ayarla
        if self.mevcut_cihaz == "ST3020 Servo":
            sutun_oku, sutun_yaz = self._st3020_sutunlari(secilen_mod)
        elif self.mevcut_cihaz == "JKID Motor":
            sutun_oku, sutun_yaz = self._jkid_sutunlari(secilen_mod)
        else:
            sutun_oku = ["ID"]
            sutun_yaz = ["ID", "İşlem"]

        self.tablo_okuma.setColumnCount(len(sutun_oku))
        self.tablo_okuma.setHorizontalHeaderLabels(sutun_oku)
        
        self.tablo_yazma.setColumnCount(len(sutun_yaz))
        self.tablo_yazma.setHorizontalHeaderLabels(sutun_yaz)
        
        # 4. ADIM: Hafızaya aldığımız ID'leri yeni tablo formatında geri yükle!
        if mevcut_idler:
            for s_id in mevcut_idler:
                self.satir_ekle(s_id)
                
        self.text_log.append(f"[MOD DEĞİŞİMİ] [{self.mevcut_cihaz}] Arayüz '{secilen_mod}' için yapılandırıldı.")

    # --- ST3020 Sütun Tanımları ---
    def _st3020_sutunlari(self, mod):
        if mod == "ID Değiştirme Modu":
            return ["Mevcut ID", "Durum"], ["Hedef ID", "YENİ ID Gönder", "İşlem"]
        elif mod == "Multi-Turn Modu":
            return ["ID", "Mod", "Açı (°)", "Sıcaklık (°C)", "Voltaj (V)"], ["Hedef ID", "POZİSYON (0-65535)", "HIZ (%)", "İVME", "İşlem"]
        elif mod == "Motor Modu":
            return ["ID", "Mod", "Açı (°)", "Sıcaklık (°C)", "Voltaj (V)"], ["Hedef ID", "HIZ (%)", "İVME", "İşlem"]
        elif mod == "Servo Modu":
            return ["ID", "Mod", "Açı (°)", "Sıcaklık (°C)", "Voltaj (V)"], ["Hedef ID", "POZİSYON (0-65535)", "HIZ (%)", "İşlem"]
        return ["ID"], ["ID", "İşlem"]

    # --- JKID Sütun Tanımları ---
    def _jkid_sutunlari(self, mod):
        # Okuma sütunları: STM32'den gelen 19-byte paket verilerine göre
        okuma_temel = ["ID", "Mod", "Pozisyon", "Hız", "Tork", "Durum", "Hata Kodu"]
        
        if mod == "Absolute Pozisyon Modu":
            return okuma_temel, ["Hedef ID", "POZİSYON (int32)", "HIZ (RPM)", "İVME (ACC)", "YAVAŞLAMA (DEC)", "İşlem"]
        elif mod == "Relative Pozisyon Modu":
            return okuma_temel, ["Hedef ID", "POZİSYON (int32)", "HIZ (RPM)", "İVME (ACC)", "YAVAŞLAMA (DEC)", "İşlem"]
        elif mod == "Hız Kontrol Modu":
            return okuma_temel, ["Hedef ID", "HIZ (RPM)", "İVME (ACC)", "YAVAŞLAMA (DEC)", "İşlem"]
        elif mod == "Tork Kontrol Modu":
            return okuma_temel, ["Hedef ID", "TORK", "HIZ LİMİT (RPM)", "TORK SLOPE", "İşlem"]
        elif mod == "Fault Reset Modu":
            return okuma_temel, ["Hedef ID", "İşlem"]
        return ["ID"], ["ID", "İşlem"]

    # ==========================================
    # --- SATIR EKLEME (Cihaz Tipine Göre) ---
    # ==========================================
    def satir_ekle(self, cihaz_id):
        if self.mevcut_cihaz == "ST3020 Servo":
            self._st3020_satir_ekle(cihaz_id)
        elif self.mevcut_cihaz == "JKID Motor":
            self._jkid_satir_ekle(cihaz_id)

    def _st3020_satir_ekle(self, servo_id):
        satir = self.tablo_okuma.rowCount()
        self.tablo_okuma.insertRow(satir)
        self.tablo_yazma.insertRow(satir)
        
        if self.mevcut_mod == "ID Değiştirme Modu":
            okuma_verileri = [servo_id, "Bekleniyor..."]
        else:
            mod_kisaltmasi = self.mevcut_mod.replace(" Modu", "")
            okuma_verileri = [servo_id, mod_kisaltmasi, "0", "0", "0.0"]
            
        for sutun, veri in enumerate(okuma_verileri):
            item = QTableWidgetItem(veri)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tablo_okuma.setItem(satir, sutun, item)

        id_item = QTableWidgetItem(servo_id)
        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tablo_yazma.setItem(satir, 0, id_item)

        buton_sutunu = 0
        if self.mevcut_mod == "ID Değiştirme Modu":
            self.gonderim_hucresi_olustur(satir, 1, "Yeni ID")
            buton_sutunu = 2
        elif self.mevcut_mod == "Multi-Turn Modu":
            self.gonderim_hucresi_olustur(satir, 1, "Pozisyon Gir")
            self.gonderim_hucresi_olustur(satir, 2, "Hız Gir")
            self.gonderim_hucresi_olustur(satir, 3, "İvme Gir")
            buton_sutunu = 4
        elif self.mevcut_mod == "Motor Modu":
            self.gonderim_hucresi_olustur(satir, 1, "Hız Gir")
            self.gonderim_hucresi_olustur(satir, 2, "İvme Gir")
            buton_sutunu = 3
        elif self.mevcut_mod == "Servo Modu":
            self.gonderim_hucresi_olustur(satir, 1, "Pozisyon Gir")
            self.gonderim_hucresi_olustur(satir, 2, "Hız Gir")
            buton_sutunu = 3

        btn_gonder = QPushButton("GÖNDER")
        btn_gonder.setStyleSheet("background-color: #007BFF; color: white; border-radius: 4px; padding: 4px;")
        btn_gonder.clicked.connect(lambda _, r=satir: self.satiri_gonder(r))
        self.tablo_yazma.setCellWidget(satir, buton_sutunu, btn_gonder)

    def _jkid_satir_ekle(self, motor_id):
        satir = self.tablo_okuma.rowCount()
        self.tablo_okuma.insertRow(satir)
        self.tablo_yazma.insertRow(satir)
        
        # Okuma tablosu: [ID, Mod, Pozisyon, Hız, Tork, Durum, Hata Kodu]
        mod_kisaltmasi = self.mevcut_mod.replace(" Modu", "")
        okuma_verileri = [motor_id, mod_kisaltmasi, "0", "0", "0", "---", "---"]
            
        for sutun, veri in enumerate(okuma_verileri):
            item = QTableWidgetItem(veri)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tablo_okuma.setItem(satir, sutun, item)

        id_item = QTableWidgetItem(motor_id)
        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tablo_yazma.setItem(satir, 0, id_item)

        buton_sutunu = 0
        if self.mevcut_mod in ["Absolute Pozisyon Modu", "Relative Pozisyon Modu"]:
            # P1=Pozisyon(int32), P2=Hız(int16/RPM), P3=Acc(uint16), P4=Dec(uint16)
            self.gonderim_hucresi_olustur(satir, 1, "Pozisyon Gir")
            self.gonderim_hucresi_olustur(satir, 2, "Hız (RPM)")
            self.gonderim_hucresi_olustur(satir, 3, "İvme (ACC)")
            self.gonderim_hucresi_olustur(satir, 4, "Yavaşlama (DEC)")
            buton_sutunu = 5
        elif self.mevcut_mod == "Hız Kontrol Modu":
            # P2=Hız(int16/RPM), P3=Acc(uint16), P4=Dec(uint16)
            self.gonderim_hucresi_olustur(satir, 1, "Hız (RPM)")
            self.gonderim_hucresi_olustur(satir, 2, "İvme (ACC)")
            self.gonderim_hucresi_olustur(satir, 3, "Yavaşlama (DEC)")
            buton_sutunu = 4
        elif self.mevcut_mod == "Tork Kontrol Modu":
            # P1=Tork(int32), P2=Hız Limit(int16/RPM), P3=Tork Slope(uint16)
            self.gonderim_hucresi_olustur(satir, 1, "Tork Gir")
            self.gonderim_hucresi_olustur(satir, 2, "Hız Limit (RPM)")
            self.gonderim_hucresi_olustur(satir, 3, "Tork Slope")
            buton_sutunu = 4
        elif self.mevcut_mod == "Fault Reset Modu":
            # Parametre yok, sadece GÖNDER butonu
            buton_sutunu = 1

        btn_gonder = QPushButton("GÖNDER")
        btn_gonder.setStyleSheet("background-color: #E67300; color: white; border-radius: 4px; padding: 4px;")
        btn_gonder.clicked.connect(lambda _, r=satir: self.satiri_gonder(r))
        self.tablo_yazma.setCellWidget(satir, buton_sutunu, btn_gonder)

    def gonderim_hucresi_olustur(self, satir, sutun, placeholder):
        txt_girdi = QLineEdit()
        txt_girdi.setPlaceholderText(placeholder)
        txt_girdi.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Sadece sayısal giriş (negatif dahil): opsiyonel eksi işareti + rakamlar
        regex = QRegularExpression(r"^-?\d*$")
        validator = QRegularExpressionValidator(regex)
        txt_girdi.setValidator(validator)
        self.tablo_yazma.setCellWidget(satir, sutun, txt_girdi)

    # ==========================================
    # --- EVRENSEL GÖNDERME MOTORU (Cihaz Tipine Göre) ---
    # ==========================================
    def satiri_gonder(self, satir):
        if not self.seri_port.is_open:
            QMessageBox.warning(self, "Uyarı", "Veri göndermek için önce seri porta bağlanmalısınız!")
            return

        if self.mevcut_cihaz == "ST3020 Servo":
            self._st3020_gonder(satir)
        elif self.mevcut_cihaz == "JKID Motor":
            self._jkid_gonder(satir)

    # --- ST3020 Gönderme ---
    def _st3020_gonder(self, satir):
        try:
            hedef_id = int(self.tablo_yazma.item(satir, 0).text())
        except ValueError:
            return

        mod_byte = 0x00
        pos, hiz, ivme = 0, 0, 0

        try:
            if self.mevcut_mod == "ID Değiştirme Modu":
                mod_byte = 0x01
                txt_id = self.tablo_yazma.cellWidget(satir, 1).text().strip()
                if not txt_id:
                    QMessageBox.warning(self, "Hata", "Lütfen yeni ID değeri girin!")
                    return
                yeni_id = int(txt_id)
                pos = yeni_id
                
            elif self.mevcut_mod == "Multi-Turn Modu":
                mod_byte = 0x02
                txt_p = self.tablo_yazma.cellWidget(satir, 1).text().strip()
                txt_h = self.tablo_yazma.cellWidget(satir, 2).text().strip()
                txt_i = self.tablo_yazma.cellWidget(satir, 3).text().strip()
                pos  = int(txt_p) if txt_p else 0
                hiz  = int(txt_h) if txt_h else 0
                ivme = int(txt_i) if txt_i else 0
                
            elif self.mevcut_mod == "Motor Modu":
                mod_byte = 0x03
                txt_h = self.tablo_yazma.cellWidget(satir, 1).text().strip()
                txt_i = self.tablo_yazma.cellWidget(satir, 2).text().strip()
                hiz  = int(txt_h) if txt_h else 0
                ivme = int(txt_i) if txt_i else 0
                
            elif self.mevcut_mod == "Servo Modu":
                mod_byte = 0x04
                txt_p = self.tablo_yazma.cellWidget(satir, 1).text().strip()
                txt_h = self.tablo_yazma.cellWidget(satir, 2).text().strip()
                pos  = int(txt_p) if txt_p else 0
                hiz  = int(txt_h) if txt_h else 0

        except ValueError:
            QMessageBox.warning(self, "Hata", "Lütfen sadece sayısal (tam sayı) değerler girin!")
            return

        # Negatif değerleri signed int16 olarak 0-65535 aralığına dönüştür
        def to_uint16(val):
            if val < -32768 or val > 65535:
                return None
            return val & 0xFFFF
        
        pos_u = to_uint16(pos)
        hiz_u = to_uint16(hiz)
        ivme_u = to_uint16(ivme)
        
        if pos_u is None or hiz_u is None or ivme_u is None:
            QMessageBox.warning(self, "Sınır Hatası", "Değerler -32768 ile 65535 arasında olmalıdır!")
            return

        mevcut_durum = (mod_byte, pos, hiz, ivme)
        onceki_durum = self.son_gonderilenler.get(satir)
        
        if mevcut_durum == onceki_durum:
            self.text_log.append(f"[BİLGİ] Hedef ID {hedef_id} için tüm değerler aynı. Gönderim atlandı.")
            return

        pos_h, pos_l = (pos_u >> 8) & 0xFF, pos_u & 0xFF
        hiz_h, hiz_l = (hiz_u >> 8) & 0xFF, hiz_u & 0xFF
        ivme_h, ivme_l = (ivme_u >> 8) & 0xFF, ivme_u & 0xFF

        checksum = (hedef_id + mod_byte + pos_h + pos_l + hiz_h + hiz_l + ivme_h + ivme_l) & 0xFF

        veri_paketi = bytearray([0xAA, hedef_id, mod_byte, pos_h, pos_l, hiz_h, hiz_l, ivme_h, ivme_l, checksum, 0x55])

        try:
            self.seri_port.write(veri_paketi)
            paket_hex = " ".join([f"{b:02X}" for b in veri_paketi])
            self.text_log.append(f"[ST3020 GÖNDERİLDİ] ID:{hedef_id} | Mod:{mod_byte:02X} | PAKET -> [ {paket_hex} ]")
            
            self.son_gonderilenler[satir] = mevcut_durum
            
            # ID Değiştirme modunda: başarılı gönderim sonrası mevcut satırın ID'sini güncelle
            if self.mevcut_mod == "ID Değiştirme Modu":
                yeni_id_str = str(pos)
                id_item_okuma = self.tablo_okuma.item(satir, 0)
                if id_item_okuma:
                    id_item_okuma.setText(yeni_id_str)
                id_item_yazma = self.tablo_yazma.item(satir, 0)
                if id_item_yazma:
                    id_item_yazma.setText(yeni_id_str)
                self.text_log.append(f"[ID DEĞİŞTİ] Servo ID {hedef_id} -> {pos} olarak güncellendi.")
            
        except Exception as e:
            QMessageBox.critical(self, "Gönderme Hatası", f"Veri STM32'ye iletilemedi!\n{e}")

    # --- JKID Gönderme (15-Byte Paket: 0xAA, ID, CMD, P1[4], P2[2], P3[2], P4[2], CS, 0x55) ---
    def _jkid_gonder(self, satir):
        try:
            hedef_id = int(self.tablo_yazma.item(satir, 0).text())
        except ValueError:
            return

        cmd_byte = 0x00
        p1, p2, p3, p4 = 0, 0, 0, 0  # P1:int32, P2:int16, P3:uint16, P4:uint16

        try:
            if self.mevcut_mod == "Absolute Pozisyon Modu":
                cmd_byte = 0x01
                txt_pos = self.tablo_yazma.cellWidget(satir, 1).text().strip()
                txt_hiz = self.tablo_yazma.cellWidget(satir, 2).text().strip()
                txt_acc = self.tablo_yazma.cellWidget(satir, 3).text().strip()
                txt_dec = self.tablo_yazma.cellWidget(satir, 4).text().strip()
                p1 = int(txt_pos) if txt_pos else 0   # Pozisyon (int32)
                p2 = int(txt_hiz) if txt_hiz else 0   # Hız RPM (int16)
                p3 = int(txt_acc) if txt_acc else 0   # Acc (uint16)
                p4 = int(txt_dec) if txt_dec else 0   # Dec (uint16)

            elif self.mevcut_mod == "Relative Pozisyon Modu":
                cmd_byte = 0x02
                txt_pos = self.tablo_yazma.cellWidget(satir, 1).text().strip()
                txt_hiz = self.tablo_yazma.cellWidget(satir, 2).text().strip()
                txt_acc = self.tablo_yazma.cellWidget(satir, 3).text().strip()
                txt_dec = self.tablo_yazma.cellWidget(satir, 4).text().strip()
                p1 = int(txt_pos) if txt_pos else 0
                p2 = int(txt_hiz) if txt_hiz else 0
                p3 = int(txt_acc) if txt_acc else 0
                p4 = int(txt_dec) if txt_dec else 0

            elif self.mevcut_mod == "Hız Kontrol Modu":
                cmd_byte = 0x03
                txt_hiz = self.tablo_yazma.cellWidget(satir, 1).text().strip()
                txt_acc = self.tablo_yazma.cellWidget(satir, 2).text().strip()
                txt_dec = self.tablo_yazma.cellWidget(satir, 3).text().strip()
                p2 = int(txt_hiz) if txt_hiz else 0   # Hız RPM (int16)
                p3 = int(txt_acc) if txt_acc else 0   # Acc (uint16)
                p4 = int(txt_dec) if txt_dec else 0   # Dec (uint16)

            elif self.mevcut_mod == "Tork Kontrol Modu":
                cmd_byte = 0x04
                txt_trq = self.tablo_yazma.cellWidget(satir, 1).text().strip()
                txt_hiz = self.tablo_yazma.cellWidget(satir, 2).text().strip()
                txt_slp = self.tablo_yazma.cellWidget(satir, 3).text().strip()
                p1 = int(txt_trq) if txt_trq else 0   # Tork (int32)
                p2 = int(txt_hiz) if txt_hiz else 0   # Hız Limit RPM (int16)
                p3 = int(txt_slp) if txt_slp else 0   # Tork Slope (uint16)

            elif self.mevcut_mod == "Fault Reset Modu":
                cmd_byte = 0x05
                # Parametre gerekmez

        except ValueError:
            QMessageBox.warning(self, "Hata", "Lütfen sadece sayısal (tam sayı) değerler girin!")
            return

        # P1: int32 → 4 byte Big-Endian
        p1_u = p1 & 0xFFFFFFFF
        p1_b3 = (p1_u >> 24) & 0xFF
        p1_b2 = (p1_u >> 16) & 0xFF
        p1_b1 = (p1_u >> 8) & 0xFF
        p1_b0 = p1_u & 0xFF

        # P2: int16 → 2 byte Big-Endian
        p2_u = p2 & 0xFFFF
        p2_h = (p2_u >> 8) & 0xFF
        p2_l = p2_u & 0xFF

        # P3: uint16 → 2 byte Big-Endian
        p3_u = p3 & 0xFFFF
        p3_h = (p3_u >> 8) & 0xFF
        p3_l = p3_u & 0xFF

        # P4: uint16 → 2 byte Big-Endian
        p4_u = p4 & 0xFFFF
        p4_h = (p4_u >> 8) & 0xFF
        p4_l = p4_u & 0xFF

        # Checksum: byte[1] ~ byte[12] toplamı & 0xFF
        checksum = (hedef_id + cmd_byte + p1_b3 + p1_b2 + p1_b1 + p1_b0 + 
                    p2_h + p2_l + p3_h + p3_l + p4_h + p4_l) & 0xFF

        # 15-Byte Paket: [0xAA, ID, CMD, P1(4), P2(2), P3(2), P4(2), CS, 0x55]
        veri_paketi = bytearray([
            0xAA, hedef_id, cmd_byte,
            p1_b3, p1_b2, p1_b1, p1_b0,
            p2_h, p2_l,
            p3_h, p3_l,
            p4_h, p4_l,
            checksum, 0x55
        ])

        try:
            self.seri_port.write(veri_paketi)
            paket_hex = " ".join([f"{b:02X}" for b in veri_paketi])
            mod_adi = self.mevcut_mod.replace(" Modu", "")
            self.text_log.append(f"[JKID GÖNDERİLDİ] ID:{hedef_id} | {mod_adi} | CMD:0x{cmd_byte:02X} | PAKET -> [ {paket_hex} ]")
        except Exception as e:
            QMessageBox.critical(self, "Gönderme Hatası", f"Veri STM32'ye iletilemedi!\n{e}")

    # ==========================================
    # --- HABERLEŞME / PORT BAĞLANTISI ---
    # ==========================================
    def portlari_listele(self):
        self.combo_port.clear()
        portlar = serial.tools.list_ports.comports()
        for port in portlar:
            self.combo_port.addItem(port.device)
        if self.combo_port.count() == 0:
            self.combo_port.addItem("Port Bulunamadı")

    def baglanti_tetikle(self):
        if self.seri_port.is_open:
            self.timer_oku.stop()
            self.seri_port.close()
            self.text_log.append("[SİSTEM] Bağlantı kesildi.")
            self.btn_baglanti.setText("BAĞLAN")
            self.btn_baglanti.setStyleSheet("background-color: #28a745;")
            self.combo_port.setEnabled(True) 
            self.combo_baud.setEnabled(True)
            return

        secilen_port = self.combo_port.currentText()
        secilen_baud = self.combo_baud.currentText()

        if secilen_port == "Port Bulunamadı" or secilen_port == "":
            QMessageBox.warning(self, "Hata", "Geçerli bir COM portu seçilmedi!")
            return

        try:
            self.seri_port.port = secilen_port
            self.seri_port.baudrate = int(secilen_baud)
            self.seri_port.timeout = 1 
            self.seri_port.open()
            
            if self.seri_port.is_open:
                self.text_log.append(f"[BAŞARILI] {secilen_port} portuna bağlanıldı.")
                self.btn_baglanti.setText("BAĞLANTIYI KES")
                self.btn_baglanti.setStyleSheet("background-color: #dc3545;")
                self.combo_port.setEnabled(False) 
                self.combo_baud.setEnabled(False)
                
                self.tampon_veri.clear() 
                self.timer_oku.start(50) 
                
        except Exception as hata:
            QMessageBox.critical(self, "Port Hatası", f"Bağlantı açılamadı:\n{hata}")

    # ==========================================
    # --- VERİ ALMA (PARSE) MOTORU ---
    # ==========================================
    def seri_porttan_oku(self):
        if not self.seri_port.is_open:
            return
            
        try:
            if self.seri_port.in_waiting > 0:
                gelen_bytelar = self.seri_port.read(self.seri_port.in_waiting)
                self.tampon_veri.extend(gelen_bytelar) 
                
                if self.mevcut_cihaz == "ST3020 Servo":
                    self._st3020_parse()
                elif self.mevcut_cihaz == "JKID Motor":
                    self._jkid_parse()
        except Exception as e:
            pass

    # --- ST3020 Parse ---
    def _st3020_parse(self):
        while len(self.tampon_veri) >= 10:
            if self.tampon_veri[0] == 0xBB:
                if self.tampon_veri[9] == 0x55:
                    yakalanan_paket = self.tampon_veri[:10]
                    self._st3020_paketi_ayristir(yakalanan_paket)
                    self.tampon_veri = self.tampon_veri[10:]
                else:
                    self.tampon_veri.pop(0) 
            else:
                self.tampon_veri.pop(0) 

    def _st3020_paketi_ayristir(self, paket):
        gelen_id = paket[1]
        durum = paket[2]
        aci_h = paket[3]
        aci_l = paket[4]
        sicaklik_h = paket[5] 
        sicaklik_l = paket[6]
        voltaj_ham = paket[7]
        gelen_checksum = paket[8]

        hesaplanan_checksum = (gelen_id + durum + aci_h + aci_l + sicaklik_h + sicaklik_l + voltaj_ham) & 0xFF
        if gelen_checksum != hesaplanan_checksum: return 

        gercek_aci = (aci_h << 8) | aci_l
        gercek_sicaklik = (sicaklik_h << 8) | sicaklik_l
        gercek_voltaj = voltaj_ham / 10.0 
        
        durum_metni = "🟢 Aktif" if durum == 1 else "🔴 Hata"
        mod_kisaltmasi = self.mevcut_mod.replace(" Modu", "")

        id_bulundu = False
        for satir in range(self.tablo_okuma.rowCount()):
            if self.tablo_okuma.item(satir, 0).text() == str(gelen_id):
                id_bulundu = True
                if self.mevcut_mod == "ID Değiştirme Modu":
                    self.tablo_okuma.item(satir, 1).setText(durum_metni)
                else:
                    self.tablo_okuma.item(satir, 1).setText(mod_kisaltmasi)
                    self.tablo_okuma.item(satir, 2).setText(f"{gercek_aci} °")
                    self.tablo_okuma.item(satir, 3).setText(f"{gercek_sicaklik} °C")
                    self.tablo_okuma.item(satir, 4).setText(f"{gercek_voltaj} V")
                break 

        if not id_bulundu:
            self.satir_ekle(str(gelen_id))

    # --- JKID Parse (19-Byte Paket: 0xBB, ID, Pos[4], Vel[4], Torque[2], Status[2], Mode[1], ErrCode[2], CS, 0x77) ---
    def _jkid_parse(self):
        while len(self.tampon_veri) >= 19:
            if self.tampon_veri[0] == 0xBB:
                if self.tampon_veri[18] == 0x77:
                    yakalanan_paket = self.tampon_veri[:19]
                    self._jkid_paketi_ayristir(yakalanan_paket)
                    self.tampon_veri = self.tampon_veri[19:]
                else:
                    self.tampon_veri.pop(0)
            else:
                self.tampon_veri.pop(0)

    def _jkid_paketi_ayristir(self, paket):
        # Checksum doğrulama: byte[1] ~ byte[16] toplamı
        hesaplanan_cs = 0
        for i in range(1, 17):
            hesaplanan_cs += paket[i]
        hesaplanan_cs &= 0xFF
        
        if hesaplanan_cs != paket[17]:
            return  # Checksum hatalı, paketi atla

        gelen_id = paket[1]
        
        # Pozisyon: int32, Big-Endian (byte 2-5)
        pozisyon_raw = (paket[2] << 24) | (paket[3] << 16) | (paket[4] << 8) | paket[5]
        if pozisyon_raw >= 0x80000000:
            pozisyon_raw -= 0x100000000
        
        # Hız: int32, Big-Endian (byte 6-9)
        hiz_raw = (paket[6] << 24) | (paket[7] << 16) | (paket[8] << 8) | paket[9]
        if hiz_raw >= 0x80000000:
            hiz_raw -= 0x100000000
        
        # Tork: int16, Big-Endian (byte 10-11)
        tork_raw = (paket[10] << 8) | paket[11]
        if tork_raw >= 0x8000:
            tork_raw -= 0x10000
        
        # Status Word: uint16, Big-Endian (byte 12-13)
        status_word = (paket[12] << 8) | paket[13]
        
        # Mode: int8 (byte 14)
        mode_raw = paket[14]
        if mode_raw >= 0x80:
            mode_raw -= 0x100
        
        # Hata Kodu: uint16, Big-Endian (byte 15-16)
        hata_kodu = (paket[15] << 8) | paket[16]
        
        # Durum metni oluştur (Status Word'den)
        if status_word & 0x0008:
            durum_metni = "🔴 HATA"
        elif (status_word & 0x006F) == 0x0027:
            durum_metni = "🟢 Aktif"
        elif status_word & 0x0400:
            durum_metni = "✅ Hedefe Vardı"
        elif (status_word & 0x004F) == 0x0040:
            durum_metni = "🔒 Kilitli"
        elif (status_word & 0x006F) == 0x0021:
            durum_metni = "⏳ Hazır"
        elif (status_word & 0x006F) == 0x0023:
            durum_metni = "⚡ Güç Verildi"
        else:
            durum_metni = f"⚙️ 0x{status_word:04X}"
        
        # Hata kodu metni
        hata_metni = "Yok" if hata_kodu == 0 else f"0x{hata_kodu:04X}"
        
        # Mod metni
        mod_isimleri = {1: "Pozisyon", 3: "Hız", 4: "Tork"}
        mod_metni = mod_isimleri.get(mode_raw, f"Mod:{mode_raw}")
        
        # Tabloda bu ID var mı?
        id_bulundu = False
        for satir in range(self.tablo_okuma.rowCount()):
            item = self.tablo_okuma.item(satir, 0)
            if item and item.text() == str(gelen_id):
                id_bulundu = True
                # Sütunlar: [ID, Mod, Pozisyon, Hız, Tork, Durum, Hata Kodu]
                self.tablo_okuma.item(satir, 1).setText(mod_metni)
                self.tablo_okuma.item(satir, 2).setText(str(pozisyon_raw))
                self.tablo_okuma.item(satir, 3).setText(str(hiz_raw))
                self.tablo_okuma.item(satir, 4).setText(str(tork_raw))
                self.tablo_okuma.item(satir, 5).setText(durum_metni)
                self.tablo_okuma.item(satir, 6).setText(hata_metni)
                break
        
        if not id_bulundu:
            self.satir_ekle(str(gelen_id))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = ServoArayuzu()
    pencere.show()
    sys.exit(app.exec())