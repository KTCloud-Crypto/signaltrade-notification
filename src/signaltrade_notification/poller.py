import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from signaltrade_notification.config import settings
from signaltrade_notification.identity_client import get_telegram_user, link_telegram_chat
from signaltrade_notification.portfolio_client import get_open_positions, get_user_balance
from signaltrade_notification.strategy_client import get_subscriptions, set_subscriptions_paused
from signaltrade_notification.trading_client import request_manual_liquidations

logger = logging.getLogger(__name__)
COMMAND_TIMEOUT = timedelta(minutes=2)


@dataclass(frozen=True)
class PendingCommand:
    action: str
    expires_at: datetime
    subscription_ids: tuple[int, ...] = ()


def _user_and_subscriptions(chat_id: str):
    user = get_telegram_user(chat_id)
    return user, (get_subscriptions(user.id) if user else None)


def status_text(chat_id: str) -> str:
    user, rows = _user_and_subscriptions(chat_id)
    if user is None:
        return "🔗 먼저 SignalTrade 대시보드에서 Telegram을 연동해 주세요."
    if rows is None:
        return "⚠️ 전략 상태를 조회하지 못했습니다. 잠시 후 다시 시도해 주세요."
    lines = ["📊 [자동매매 상태]"]
    for row in rows:
        state = "⏸️ 신규 매수 중지" if row["paused"] else "🟢 실행 중"
        mode = "모의" if row["mode"] == "simulated" else "실전"
        lines.append(f"\n{state} · [{mode}] {row['market']} · {row['strategy_name']}")
    if not rows:
        lines.append("\n📭 실행 중인 전략이 없습니다.")
    return "\n".join(lines)


def balance_text(chat_id: str) -> str:
    user = get_telegram_user(chat_id)
    if user is None:
        return "🔗 먼저 SignalTrade 대시보드에서 Telegram을 연동해 주세요."
    accounts = get_user_balance(user.id)
    if accounts is None:
        return "⚠️ 잔고를 조회하지 못했습니다. 잠시 후 다시 시도해 주세요."
    lines = ["💰 [Upbit 보유 잔고]"]
    for account in accounts:
        balance, locked = float(account.get("balance") or 0), float(account.get("locked") or 0)
        if balance > 0 or locked > 0:
            lines.append(f"\n{account.get('currency')}: {balance:.8f}".rstrip("0").rstrip("."))
    return "\n".join(lines)


def pause_menu(chat_id: str, action: str) -> tuple[str, tuple[int, ...]]:
    user, rows = _user_and_subscriptions(chat_id)
    if user is None:
        return "🔗 먼저 SignalTrade 대시보드에서 Telegram을 연동해 주세요.", ()
    if rows is None:
        return "⚠️ 전략 상태를 조회하지 못했습니다.", ()
    target = action == "pause"
    ids = tuple(row["id"] for row in rows if bool(row["paused"]) is not target)
    label = "일시정지" if target else "재개"
    return (f"{'⏸️' if target else '▶️'} {label}할 전략 {len(ids)}개가 있습니다.\n/all - 모든 전략 {label}\n/cancel - 취소"
            if ids else f"ℹ️ 현재 {label}할 전략이 없습니다."), ids


def apply_pause(chat_id: str, action: str, ids: tuple[int, ...]) -> str:
    user = get_telegram_user(chat_id)
    if user is None:
        return "🔗 먼저 연동해 주세요."
    updated = set_subscriptions_paused(user.id, list(ids), action == "pause")
    return (f"✅ 전략 {updated}개를 {'일시정지' if action == 'pause' else '재개'}했습니다."
            if updated is not None else "⚠️ 전략 상태 변경에 실패했습니다.")


def close_menu(chat_id: str) -> tuple[str, tuple[int, ...]]:
    user = get_telegram_user(chat_id)
    if user is None:
        return "🔗 먼저 SignalTrade 대시보드에서 Telegram을 연동해 주세요.", ()
    positions = get_open_positions(user.id)
    if not positions:
        return "📭 전량 매도할 전략 포지션이 없습니다.", ()
    ids = tuple(int(row["subscription_id"]) for row in positions)
    return "🚨 포지션 전량 매도\n/all - 모든 포지션\n/cancel - 취소", ids


async def execute_close(chat_id: str, ids: tuple[int, ...], idempotency_key: str) -> str:
    user = get_telegram_user(chat_id)
    result = await request_manual_liquidations(
        user.id, list(ids), idempotency_key
    ) if user else None
    if result is None:
        return "⚠️ 전량 매도 요청 전달에 실패했습니다."
    requested, failures = result
    return f"✅ 전량 매도 요청 {requested}건을 전달했습니다." + (
        f"\n❌ 처리 실패: {', '.join(failures)}" if failures else "")


def help_text() -> str:
    return ("🤖 [SignalTrade 명령어]\n\n"
            "/status - 자동매매 상태\n/pause - 전략 신규 매수 일시정지\n"
            "/resume - 일시정지 전략 재개\n/balance - Upbit 잔고 조회\n"
            "/positions - 전략별 포지션 조회\n/findid - 연결된 SignalTrade 아이디 찾기\n"
            "/close - 전략 포지션 전량 매도\n/cancel - 진행 중인 명령 취소\n"
            "/help - 명령어 다시 보기")


def find_id_text(chat_id: str) -> str:
    user = get_telegram_user(chat_id)
    if user is None:
        return "🔗 이 텔레그램에는 연결된 SignalTrade 계정이 없습니다."
    return f"👤 SignalTrade 계정 안내\n\n아이디: {user.username}\n\n로그인 화면에서 이 아이디를 사용해 주세요."


def positions_text(chat_id: str) -> str:
    user = get_telegram_user(chat_id)
    if user is None:
        return "🔗 먼저 SignalTrade 대시보드에서 Telegram을 연동해 주세요."
    positions = get_open_positions(user.id)
    if positions is None:
        return "⚠️ 포지션을 조회하지 못했습니다. 잠시 후 다시 시도해 주세요."
    lines = ["📦 [전략별 포지션]"]
    for position in positions:
        lines.append(f"\n📈 {position['strategy_name']}\n   종목: {position['market']}\n"
                     f"   수량: {float(position['volume']):.8f}\n"
                     f"   평균 매수가: {float(position.get('average_buy_price') or 0):,.0f}원")
    if not positions:
        lines.append("\n📭 현재 보유한 전략 포지션이 없습니다.")
    return "\n".join(lines)


class TelegramPoller:
    def __init__(self, token: str):
        self._base_url = f"{settings.telegram_api_base_url.rstrip('/')}/bot{token}"
        self._offset: int | None = None
        self._pending: dict[str, PendingCommand] = {}

    async def _send_message(self, client: httpx.AsyncClient, chat_id: str, text: str) -> None:
        response = await client.post(f"{self._base_url}/sendMessage",
                                     json={"chat_id": chat_id, "text": text})
        response.raise_for_status()

    async def _handle_update(self, client: httpx.AsyncClient, update: dict) -> None:
        if update.get("callback_query"):
            return
        message = update.get("message") or {}
        text = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        if not chat_id:
            return
        command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()
        if command == "/start":
            parts = text.split(maxsplit=1)
            if len(parts) != 2:
                reply = "🔗 SignalTrade 대시보드에서 연동 코드를 발급한 뒤\n/start ABCD2345 형식으로 입력해 주세요."
            elif await asyncio.to_thread(link_telegram_chat, parts[1].strip(), chat_id):
                reply = "✅ SignalTrade 연동이 완료되었습니다!\n\n명령어를 확인하려면 /help를 입력해 주세요."
            else:
                reply = "❌ 연동 코드가 올바르지 않거나 만료되었습니다."
        elif command == "/help":
            reply = help_text()
        elif command in {"/chatid", "/findid"}:
            reply = ("🔒 아이디 찾기는 텔레그램 봇과의 개인 채팅에서만 사용할 수 있습니다."
                     if str(chat.get("type") or "private") != "private"
                     else await asyncio.to_thread(find_id_text, chat_id))
        elif command == "/positions":
            reply = await asyncio.to_thread(positions_text, chat_id)
        elif command == "/status":
            reply = await asyncio.to_thread(status_text, chat_id)
        elif command == "/balance":
            reply = await asyncio.to_thread(balance_text, chat_id)
        elif command in {"/pause", "/resume"}:
            action = command[1:]
            reply, ids = await asyncio.to_thread(pause_menu, chat_id, action)
            if ids:
                self._pending[chat_id] = PendingCommand(action, datetime.utcnow() + COMMAND_TIMEOUT, ids)
        elif command == "/close":
            reply, ids = await asyncio.to_thread(close_menu, chat_id)
            if ids:
                self._pending[chat_id] = PendingCommand("close", datetime.utcnow() + COMMAND_TIMEOUT, ids)
        elif command == "/cancel":
            reply = ("✅ 진행 중인 명령을 취소했습니다." if self._pending.pop(chat_id, None)
                     else "ℹ️ 취소할 명령이 없습니다.")
        elif command == "/all" and chat_id in self._pending:
            pending = self._pending.pop(chat_id)
            if pending.expires_at <= datetime.utcnow():
                reply = "⌛ 명령이 만료되었습니다. 다시 시작해 주세요."
            elif pending.action in {"pause", "resume"}:
                reply = await asyncio.to_thread(apply_pause, chat_id, pending.action,
                                                pending.subscription_ids)
            else:
                self._pending[chat_id] = PendingCommand(
                    "close_confirm", datetime.utcnow() + COMMAND_TIMEOUT,
                    pending.subscription_ids)
                reply = "⚠️ 선택한 포지션을 시장가로 전량 매도합니다.\n/confirm - 실행\n/cancel - 취소"
        elif command == "/confirm" and chat_id in self._pending:
            pending = self._pending.pop(chat_id)
            reply = (await execute_close(
                chat_id, pending.subscription_ids,
                f"telegram-update:{int(update['update_id'])}",
            )
                     if pending.action == "close_confirm" else "⚠️ 먼저 /close를 입력해 주세요.")
        elif text.startswith("/"):
            reply = "❓ 등록되지 않은 명령어입니다.\n사용 가능한 명령을 확인하려면 /help를 입력해 주세요."
        else:
            return
        await self._send_message(client, chat_id, reply)

    async def _process_updates(self, client: httpx.AsyncClient, updates: list[dict]) -> None:
        for update in updates:
            update_id = int(update["update_id"])
            await self._handle_update(client, update)
            # Telegram은 다음 offset을 보내면 그 이전 업데이트를 처리 완료로
            # 간주한다. 명령 처리와 답장 전송이 모두 끝난 뒤에만 전진시킨다.
            self._offset = update_id + 1

    async def run(self, stop: asyncio.Event) -> None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(35, connect=10)) as client:
            logger.info("Telegram polling started")
            while not stop.is_set():
                try:
                    response = await client.get(f"{self._base_url}/getUpdates",
                                                params={"offset": self._offset, "timeout": 25})
                    response.raise_for_status()
                    await self._process_updates(client, response.json().get("result", []))
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    logger.warning("Telegram polling failed: %s", type(error).__name__)
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        pass


async def run_telegram_poller(stop: asyncio.Event) -> None:
    if not settings.telegram_bot_token:
        logger.info("Telegram polling disabled: TELEGRAM_BOT_TOKEN is empty")
        return
    await TelegramPoller(settings.telegram_bot_token).run(stop)
