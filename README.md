# SignalTrade Notification

사용자에게 전달할 알림을 Telegram으로 보내고 Telegram 명령을 처리하는 Worker입니다. 주문이나 전략 로직을 직접 수행하지 않고, 다른 도메인에서 확정된 결과를 사람이 이해할 수 있는 메시지로 전달합니다.

## 주요 역할

- Notification Queue의 `NotificationRequested` 메시지 소비
- 주문 접수, 체결, 실패와 시스템 오류 알림 전송
- 메시지에 필요한 사용자·전략·거래 정보 보완
- Telegram Bot API를 이용한 메시지 전송
- Telegram 명령 polling과 연결 사용자 확인
- 일시적인 전송 실패 재시도와 반복 실패 메시지 격리
- Token, API Key, 채팅 정보 등 민감정보의 로그 노출 방지

## 데이터 권한

소유하거나 직접 쓰는 PostgreSQL 도메인 테이블이 없습니다. 사용자와 거래 정보는 필요한 시점에 각 소유 서비스에서 조회합니다. 알림 처리 결과 때문에 다른 서비스의 업무 테이블을 직접 변경하지 않습니다.

## Queue 통신

Trading 등 이벤트 생산자는 사용자에게 알려야 할 내용을 `message_outbox`에 `NotificationRequested`로 기록합니다. Messaging이 이를 Notification Queue에 보내면 Notification Worker가 소비합니다.

```text
도메인 서비스 → message_outbox → Messaging
             → Notification Queue → Notification → Telegram
```

처리에 반복해서 실패한 메시지는 Queue의 재시도 정책을 거친 뒤 DLQ로 이동합니다. DLQ는 계속 실패하는 메시지를 정상 메시지와 분리해 운영자가 원인을 확인할 수 있게 하는 별도 Queue입니다.

## HTTP와 Redis

알림 내용을 만들 때 Identity, Strategy, Trading, Portfolio의 내부 HTTP API를 조회합니다. 조회만 수행하며 해당 서비스의 데이터를 수정하지 않습니다.

SQS는 같은 메시지를 두 번 전달할 수 있으므로 Redis에 짧은 잠금과 전송 완료 표시를 저장합니다. 이를 통해 같은 알림이 동시에 또는 반복해서 Telegram으로 발송되는 것을 막습니다.
