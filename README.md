# SignalTrade Notification

주문·체결·오류 같은 사용자 알림을 Telegram으로 전달하고, Telegram 명령을 처리하는 Worker입니다.

## 주요 책임

- Notification Queue의 알림 요청 소비
- Telegram 메시지 전송과 전송 결과 기록
- Telegram 명령 polling과 사용자 연결 확인
- 알림 실패 시 Queue 재시도·DLQ 정책 활용
- Token, 채팅 ID 등 민감정보 로그 차단

## 디렉터리

```text
src/signaltrade_notification/
  worker.py          Queue 소비와 Telegram 전송
  telegram_client.py Telegram HTTP 호출
  command_handler.py Telegram 명령 처리
  identity_client.py 사용자·연결 상태 내부 조회
tests/               전송, 명령, 오류 처리 테스트
```

## 다른 서비스와 통신

Trading과 Portfolio는 사용자에게 알려야 할 결과를 Outbox에 기록합니다. Messaging이 이를 Notification Queue로 보내면 이 Worker가 소비합니다.

```text
Trading / Portfolio → Outbox → Messaging
                    → Notification Queue → Notification → Telegram
```

사용자 정보, 전략 이름, 주문 상세가 더 필요하면 Identity·Strategy·Trading·Portfolio 내부 API를 조회합니다.

## 로컬 확인

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
```

Telegram 연동은 Core의 `.env`에 Bot Token과 Username을 넣은 뒤 local secret load 스크립트로 주입합니다.
