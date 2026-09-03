# signaltrade-notification

`NotificationRequested` 메시지를 SQS에서 소비해 Telegram으로 전달하는 독립 Worker입니다.
전달에 성공한 메시지만 ACK하며 실패한 메시지는 SQS visibility timeout과 DLQ 정책에 맡깁니다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
```

기준 코드는 `KTCloud-Crypto`의 `feat/132`, 커밋
`013107ae8ddd08bed02d88db89af7eeb0cf65bba`입니다.
