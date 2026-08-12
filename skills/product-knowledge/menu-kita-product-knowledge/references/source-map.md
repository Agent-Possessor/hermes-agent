# Source Map

Knowledge base ini disusun dari repository `menu-kita-app.zip`, terutama:
- Modul skill internal untuk merchant acquisition, onboarding/CRO, user acquisition, growth insight, promo, referral/ally, retention, menu pricing, shop management, menu/material management, dan voucher management.
- Dokumentasi finance yang menyebut laporan penjualan/pembayaran/customer, neraca lajur, jurnal, HPP, persediaan, refund, withdraw, dan export Excel/PDF.
- Catatan proyek yang menunjukkan domain bisnis seperti user, order, transaction, stock, voucher, material, menu-material relation, notification, serta pembayaran.
- Struktur aplikasi dan copy yang tersedia di repository.
- Implementasi health di `menu_kita_api/src/modules/health`, termasuk controller, service, DTO, repository, migration, dan client untuk Strava, Calories Ninja, AI nutrient enrichment, menu nutrition, health summary, recommendation, workout, route, club, webhook, dan challenge.
- Implementasi frontend customer health di `menu_kita/lib/data/customer_health`, `menu_kita/lib/domain/customer_health`, `menu_kita/lib/model/local/customer_health_vm.dart`, halaman `pages/customer/detail/health`, `pages/customer/detail/workout`, `pages/customer/detail/activity`, `pages/customer/detail/club`, dan status nutrisi di detail menu.
- Implementasi merchant challenge di `pages/client/detail/config_challenge` dan trigger/diagnostic nutrisi menu di `controller/page/sub_client/page/config_menu_sub_client_page_controller.dart`.

## Batasan
- Tidak semua kemampuan yang teridentifikasi berarti aktif untuk setiap merchant.
- Kebijakan harga, biaya transaksi, cakupan payment, dan SLA bukan sumber final dari repository ini.
- Integrasi health pihak ketiga bergantung pada credential, token, scope, callback/webhook, dan environment.
- Angka nutrisi otomatis bersifat estimasi dan perlu diperlakukan sebagai informasi pendukung, bukan nasihat medis.
- Dokumen ini sengaja tidak menguraikan detail teknis implementasi.
