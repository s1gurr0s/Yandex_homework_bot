import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (HomeworkExceptionError, StatusCodeError,
                        RequestError)

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(time)s'
)

logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logging.error('Сбой при отправке сообщения')


def get_api_answer(current_timestamp):
    """Отправка GET запроса и проверка ответа от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            logger.error(f'Сбой в работе программы: Эндпоинт {ENDPOINT} '
                         f'недоступен. Код ответа API: {response.status_code}')
            raise StatusCodeError('Код ответа сервера. '
                                  f'{response.status_code}')
    except requests.exceptions.RequestException as request_error:
        logger.error(f'Код ответа API: {request_error}')
        raise RequestError(request_error)
    try:
        return response.json()
    except ValueError as error:
        logger.error(error)
        raise ValueError('Пришёл некорректный json')


def check_response(response):
    """Проверка данных homework в ответе."""
    if not isinstance(response, dict):
        message = 'В ответе пришёл не словарь'
        logger.error(message)
        raise TypeError(message)
    try:
        homework = response['homeworks']
    except KeyError:
        raise KeyError('Отсутствует ключ homework')
    if not isinstance(homework, list):
        raise HomeworkExceptionError('Ошибка в данных')
    return homework


def parse_status(homework):
    """Парсинг информации о домашке."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_name is not None and homework_status is not None:
        if homework_status in HOMEWORK_STATUSES:
            verdict = HOMEWORK_STATUSES.get(homework_status)
            return ('Изменился статус проверки '
                    + f'работы "{homework_name}". {verdict}')
        else:
            raise SystemError('неизвестный статус')
    else:
        raise KeyError('нет нужных ключей в словаре')


def check_tokens():
    """Проверка токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for token in tokens:
        if tokens[token] is None:
            logger.critical(f'Отсутствует или некорректна переменная: {token}')
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует переменная(-ные)')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    hw_status = 'reviewing'
    errors = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework and hw_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                hw_status = homework['status']
            logger.info('Нет изменений, повторная проверка через 10 минут')
            current_timestamp = response.get('current_date', current_timestamp)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if errors != message:
                errors = message
                send_message(bot, errors)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
