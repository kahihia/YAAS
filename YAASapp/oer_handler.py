import requests
import json


class ExchangeRateHandler:
    def __init__(self):

        self.json = self.get_latest_rates()

def get_latest_rates():
    url = 'https://openexchangerates.org/api/latest.json'
    oer_key = '1fa7967c55a34b17bd1dd3d5ab4495f3'

    result = requests.get(url, params={'app_id': oer_key})

    if result.status_code != requests.codes.ok:
        print('some problem with connecting to oer')
        return None
    else:
        json_string = result.json()
        return json_string


def get_rate(from_currency, to_currency):
    json = get_latest_rates()

    # the exchange rate is calculated on EUR -> USD -> rate_abbreviation
    #                                    first_rate second_rate
    # first calculate the from_currency -> USD rate
    first_rate = 1
    if from_currency != 'USD':
        first_rate = float(json['rates'][from_currency])

    # then USD -> rate_abbreviation
    second_rate = 1
    if to_currency != 'USD':
        second_rate = float(json['rates'][to_currency])

    # and finally EUR -> rate_abbreviation
    final_rate = second_rate / first_rate

    print('from {} to {} rate: {}' .format(from_currency, to_currency, final_rate))
    return final_rate


def get_price(price, from_currency, to_currency):
    if from_currency == to_currency:
        return price

    rate = get_rate(from_currency, to_currency)
    return price * rate
