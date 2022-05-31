class SendMessageError(Exception):
    """Ошибка при отправке сообщения в чат."""

    pass


class StatusCodeError(Exception):
    """Некорректный статус ответа сервера."""

    pass


class ResponseError(Exception):
    """Ошибка в ответе сервера."""
    
    pass
