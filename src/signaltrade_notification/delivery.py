from signaltrade_notification.envelope import MessageEnvelope
from signaltrade_notification.telegram import send_message


def deliver_notification(envelope: MessageEnvelope) -> bool:
    if envelope.message_type != "NotificationRequested":
        raise ValueError(f"unsupported notification message type: {envelope.message_type}")
    chat_id = envelope.payload.get("chat_id")
    message = envelope.payload.get("message")
    if not isinstance(chat_id, str) or not chat_id or not isinstance(message, str) or not message:
        raise ValueError("NotificationRequested requires chat_id and message")
    return send_message(chat_id, message)
