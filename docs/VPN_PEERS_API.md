VPN Peers API
===============

Коротко: фронт не должен угадывать сетевые настройки WireGuard. Бэкенд возвращает готовую конфигурацию при создании peer.

Endpoints
---------

- POST /vpn_peers/self
  - Аутентификация: Bearer token
  - Тело: (опционально) { "device_name": "MyPhone" }
  - Описание: создаёт peer для текущего пользователя. Сервер сам сгенерирует ключи/IP/allowed_ips при настройках WG_KEY_POLICY.
  - Ответ: VpnPeerOut (включая "wg_private_key" только при создании)

- GET /vpn_peers/{id}
  - Возвращает peer без приватного ключа (wg_private_key == null).

Пример интеграции (Flutter / Dart)
----------------------------------

1) Регистрация / логин, получение access_token

2) Создание peer

```dart
final resp = await http.post(Uri.parse('$API/vpn_peers/self'),
  headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
  body: jsonEncode({'device_name': 'MyPhone'}),
);
final data = jsonDecode(resp.body);
final peerId = data['id'];
final privateKey = data['wg_private_key'];
// Сохраните privateKey в secure storage и используйте его для поднятия интерфейса
```

Security notes
--------------

- Приватный ключ возвращается только один раз (при создании). Фронт должен сохранить его в защищенное хранилище (secure storage).
- В текущей реализации приватные ключи могут сохраняться в БД. Это нужно обсудить отдельно: шифрование в БД vs. не хранить приватные ключи вообще.

Configuration
-------------

- WG_KEY_POLICY: "db" (default), "host", "wg-easy"
- WG_EASY_URL, WG_EASY_PASSWORD (или WG_API_KEY) — для режима wg-easy
- WG_APPLY_ENABLED, WG_HOST_SSH — для применения на хосте (host mode)
