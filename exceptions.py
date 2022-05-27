class HomeworkExceptionError(Exception):
    """Ошибка в данных по ключу homework"""

    pass


class StatusCodeError(Exception):
    """Некорректный статус ответа сервера."""

    pass


class RequestError(Exception):
    """Некорректный запрос."""

    pass
