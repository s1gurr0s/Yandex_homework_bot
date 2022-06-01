class StatusCodeError(Exception):
    """Некорректный статус ответа сервера."""

    pass


class ResponseError(Exception):
    """Ошибка в ответе сервера."""
    
    pass
