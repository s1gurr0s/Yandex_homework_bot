import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ResponseError, StatusCodeError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

SEND_MESSAGE_ERROR = ('Ошибка {error} при отправке сообщения '
                      '{message} в Telegram')
CONNECTION_ERROR = ('Ошибка {error} выполнения GET-запроса '
                    'к эндпоинту {url} с токеном авторизации {headers} '
                    'и временной меткой {params}')
STATUS_CODE_ERROR = ('Эндпоинт {url} недоступен. '
                     'Код ответа API: {response}. Токен авторизации: '
                     '{headers}, временная метка: {params}')
RESPONSE_ERROR = ('Ошибка {error} в ответе сервера. '
                  'Содержимое: {error_detail}. '
                  'Эндпоинт: {url}, токен авторизации: {headers}, '
                  'временная метка: {params}')
RESPONSE_TYPE_ERROR = ('В ответе пришёл не словарь, а {type}')
KEY_ERROR = 'Отсутсвует ключ homeworks'
HOMEWORKS_TYPE_ERROR = ('Домашние задания в виде {type}, а не списка')
STATUS_UNEXPECTED = 'Неожиданное значение ключа status: {status}'
STATUS_DETAIL = ('Изменился статус проверки работы "{name}". '
                 '\n\n{verdict}')
TOKEN_ERROR = 'Отсутствует или некорректна переменная: {token}'
NO_TOKEN_ERROR = 'Отсутствует переменная(-ные)'
NEXT_CHECK = 'Нет изменений, повторная проверка через 10 минут'
RUNTIME_ERROR = 'Сбой в работе программы: {error}'
SEND_MESSAGE_SUCCESSFULL = 'Сообщение {message} успешно отправлено в Telegram'


def send_message(bot, message):
    """Отправка сообщения в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(SEND_MESSAGE_SUCCESSFULL.format(message=message))
        return True
    except Exception as error:
        logging.error(SEND_MESSAGE_ERROR.format(error=error, message=message))
        return False


def get_api_answer(timestamp):
    """Отправка GET-запроса и проверка ответа от API."""
    request_params = dict(url=ENDPOINT,
                          headers=HEADERS,
                          params={'from_date': timestamp})
    try:
        response = requests.get(**request_params)
    except requests.exceptions.RequestException as request_error:
        raise ConnectionError(
            CONNECTION_ERROR.format(
                error=request_error,
                **request_params
            )
        )
    if response.status_code != 200:
        raise StatusCodeError(
            STATUS_CODE_ERROR.format(
                response=response.status_code,
                **request_params
            )
        )
    response = response.json()
    for error in ['error', 'code']:
        if error in response:
            raise ResponseError(
                RESPONSE_ERROR.format(
                    error=error,
                    error_detail=response[error],
                    **request_params
                )
            )
    return response


def check_response(response):
    """Проверка данных homeworks в ответе."""
    if not isinstance(response, dict):
        raise TypeError(
            RESPONSE_TYPE_ERROR.format(type=type(response)))
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(KEY_ERROR)
    if not isinstance(homeworks, list):
        raise TypeError(
            HOMEWORKS_TYPE_ERROR.format(type=type(homeworks)))
    return homeworks


def parse_status(homework):
    """Парсинг информации о ДЗ."""
    name = homework['homework_name']
    status = homework['status']
    if status not in VERDICTS:
        raise ValueError(STATUS_UNEXPECTED.format(status=status))
    return STATUS_DETAIL.format(name=name, verdict=VERDICTS[status])


def check_tokens():
    """Проверка токенов."""
    check_tokens = [logging.critical(TOKEN_ERROR.format(token=token))
                    for token in TOKENS if globals()[token] is None]
    return not check_tokens


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(NO_TOKEN_ERROR)
        raise ValueError(NO_TOKEN_ERROR)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    errors = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                if send_message(bot, parse_status(homeworks[0])):
                    current_timestamp = response.get(
                        'current_date', current_timestamp)
            logging.info(NEXT_CHECK)
        except Exception as error:
            message = RUNTIME_ERROR.format(error=error)
            logging.error(message)
            if message != errors:
                if send_message(bot, message):
                    errors = message
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    LOG_FILE = __file__ + '.log'
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ],
        format='%(asctime)s - %(levelname)s - %(time)s - %(message)s'
    )
    main()
