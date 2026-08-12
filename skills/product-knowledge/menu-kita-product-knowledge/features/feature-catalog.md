# Feature Catalog & Business Value

## 1. Menu Digital dan Katalog
**Apa yang dilakukan:** merchant mengelola daftar menu, kategori, harga, ketersediaan, dan status aktif/nonaktif.  
**Masalah yang diselesaikan:** menu cetak cepat usang, perubahan harga lambat, pelanggan mendapat informasi berbeda.  
**Nilai bisnis:** merchant lebih mudah menjaga informasi menu tetap konsisten dan siap dijual.

Gunakan bahasa: “Pelanggan dapat melihat pilihan menu yang lebih jelas, sementara merchant bisa memperbarui katalog saat diperlukan.”

## 2. Pemesanan dan Alur Order
**Apa yang dilakukan:** mendukung alur pelanggan memilih produk dan membuat pesanan.  
**Masalah:** antrean, pencatatan manual, salah dengar/salah tulis, order sulit ditelusuri.  
**Nilai:** order menjadi lebih terstruktur sehingga kasir dan operasional lebih mudah menindaklanjuti.

## 3. Kasir dan Transaksi
**Apa yang dilakukan:** membantu pencatatan transaksi dan metode pembayaran dalam alur penjualan.  
**Nilai:** owner memiliki dasar data penjualan yang lebih rapi dan kasir memiliki proses kerja yang lebih jelas.

Jangan klaim semua metode pembayaran tersedia di setiap merchant. Sebutkan: “Metode yang tersedia bergantung pada konfigurasi merchant dan layanan pembayaran yang digunakan.”

## 4. QR untuk Pengalaman di Meja
**Apa yang dilakukan:** memungkinkan pelanggan memulai pengalaman menu/order melalui QR sesuai konteks merchant/meja.  
**Nilai:** mengurangi ketergantungan pada staf untuk langkah awal pemesanan dan membantu mempercepat akses menu.

## 5. Promo dan Voucher
**Apa yang dilakukan:** merchant dapat menyusun program diskon atau voucher dengan aturan penggunaan.  
**Nilai:** mendukung akuisisi, aktivasi, dan kunjungan ulang pelanggan.

Guardrail: Jangan sarankan diskon besar tanpa tujuan, margin, periode, dan batas penggunaan yang jelas.

## 6. Customer, Retention, dan Loyalty
**Apa yang dilakukan:** mendukung pemahaman customer dan strategi untuk mendorong pembelian ulang.  
**Nilai:** merchant dapat berpindah dari sekadar mengejar transaksi baru ke membangun hubungan dengan pelanggan.

## 7. Material, Resep, dan Persediaan
**Apa yang dilakukan:** menghubungkan menu dengan material/bahan dan mendukung pengelolaan kuantitas/persediaan.  
**Nilai:** membantu merchant memahami dampak bahan terhadap ketersediaan menu dan biaya pokok.

Gunakan bahasa hati-hati: “Membantu memperkirakan dan memantau” kecuali data yang lengkap telah tersedia.

## 8. Harga dan Menu Engineering
**Apa yang dilakukan:** membantu merchant meninjau harga menu dalam kaitan dengan biaya, margin, popularitas, dan strategi penjualan.  
**Nilai:** keputusan harga lebih berbasis data daripada sekadar mengikuti kompetitor.

## 9. Laporan Penjualan dan Keuangan
**Apa yang dilakukan:** menyediakan permukaan laporan terkait penjualan, pembayaran, customer, jurnal, laba-rugi, neraca, serta periode analisis.  
**Nilai:** owner memperoleh gambaran bisnis yang lebih terstruktur untuk evaluasi.

Penting: laporan adalah alat keputusan, bukan pengganti akuntan atau penasihat pajak.

## 10. Pengeluaran, Penarikan, dan Pengelolaan Keuangan
**Apa yang dilakukan:** mendukung pencatatan transaksi bisnis termasuk biaya, pengaruh payment fee, stok/HPP, refund, dan penarikan.  
**Nilai:** membantu memisahkan omzet dari uang yang benar-benar tersedia atau laba usaha.

## 11. Multi-Outlet dan Pengelolaan Toko
**Apa yang dilakukan:** mendukung pengelolaan organisasi/toko/outlet dengan lingkup data yang relevan.  
**Nilai:** owner dapat mengurangi kekacauan saat bisnis berkembang ke beberapa lokasi.

## 12. Referral / Ally
**Apa yang dilakukan:** mendukung program referensi atau kemitraan untuk membawa merchant atau pelanggan baru.  
**Nilai:** pertumbuhan dapat datang dari jaringan dan rekomendasi, bukan hanya iklan berbayar.

## 13. Insight, Marketing, dan Growth
**Apa yang dilakukan:** menyediakan kerangka untuk membaca data, menjalankan eksperimen pertumbuhan, konten lokal, akuisisi merchant, dan retensi.  
**Nilai:** pertumbuhan dibuat lebih terukur: tahu target, hipotesis, metrik, dan tindak lanjut.

## 14. Health, Nutrisi Menu, dan Rekomendasi Sehat
**Apa yang dilakukan:** menambahkan konteks nutrisi pada menu seperti kalori, protein, karbohidrat, lemak, serat, gula, dan sodium; menampilkan status nutrisi pada detail menu; serta membangun rekomendasi menu/shop/voucher berdasarkan ringkasan harian, profil health, dan konteks aktivitas.  
**Masalah:** pelanggan yang peduli kalori/protein harus menebak sendiri, sementara merchant tidak punya permukaan data untuk memosisikan menu sehat atau recovery meal.  
**Nilai:** pelanggan dapat membuat pilihan yang lebih informasional, dan merchant bisa memakai data nutrisi sebagai bahan edukasi, rekomendasi, bundle, dan kampanye.

Catatan status: nutrisi dapat diisi manual oleh role merchant yang berwenang atau diprime otomatis melalui job autofill. Estimasi otomatis membandingkan konteks menu/material dengan AI gateway dan Calories Ninja bila konfigurasi tersedia. Jangan menyebut hasil nutrisi sebagai nasihat medis atau angka laboratorium.

## 15. Strava, Aktivitas, Workout, dan Ringkasan Harian
**Apa yang dilakukan:** customer dapat menghubungkan akun Strava, melakukan sync aktivitas, melihat status koneksi, aktivitas terbaru, detail/stream aktivitas, dan ringkasan harian yang menggabungkan kalori masuk dari order dengan kalori keluar dari aktivitas. Aplikasi juga memiliki workout internal untuk run, ride, dan gym yang dapat disimpan sebagai aktivitas.  
**Masalah:** pengalaman order makanan biasanya terpisah dari konteks olahraga, sehingga rekomendasi setelah workout dan progress harian sulit dibuat.  
**Nilai:** Menu Kita bisa memberi pengalaman “eat smarter after activity”: pelanggan melihat keseimbangan kalori/protein dan merchant bisa hadir di momen setelah olahraga.

Catatan status: integrasi Strava bergantung pada OAuth, token, scope, webhook/subscription, dan konfigurasi environment. UI frontend memiliki fallback mock untuk dev/local, jadi jangan klaim data live Strava tersedia untuk semua pengguna tanpa konfirmasi.

## 16. Challenge Health dan Reward Merchant
**Apa yang dilakukan:** menyediakan challenge mingguan/customer dan challenge merchant yang bisa dikaitkan dengan target nutrisi/aktivitas/konsistensi serta reward seperti voucher, badge, atau poin. Merchant dapat membuat challenge sponsor dengan shop, voucher, target, periode, dan auto-join.  
**Masalah:** promo biasa sering transaksional dan kurang membangun kebiasaan.  
**Nilai:** challenge memberi alasan pelanggan kembali, terutama untuk komunitas olahraga, gym, kantor, sekolah, atau segmen health-conscious.

Gunakan bahasa: “Challenge membantu mengemas promo sebagai kebiasaan dan engagement, bukan sekadar diskon.”
