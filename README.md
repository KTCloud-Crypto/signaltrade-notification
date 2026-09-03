# SignalTrade Notification

Telegram 알림 전송과 Telegram 명령 처리를 맡는 Worker입니다.

```text
src/signaltrade_notification/  Queue 소비·Telegram 처리
tests/                         알림 처리 테스트
```

Notification Queue의 요청을 소비해 사용자에게 전달합니다. 사용자와 전략·주문 정보는 필요한 경우 각 서비스의 내부 HTTP API로 조회합니다.
