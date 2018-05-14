# -*- coding: utf-8 -*-

from decimal import *
from ccxt.base.exchange import Exchange
import base64
import hashlib
from ccxt.base.errors import ExchangeError


class gemini (Exchange):

    def nonce(self):
        return Exchange.milliseconds()

    def describe(self):
        return self.deep_extend(super(gemini, self).describe(), {
            'id': 'gemini',
            'name': 'Gemini',
            'countries': 'US',
            'rateLimit': 1500,  # 200 for private API
            'version': 'v1',
            # obsolete metainfo interface
            'hasCORS': False,
            'hasFetchOrder': True,
            'hasWithdraw': True,
            # new metainfo interface
            'has': {
                'CORS': False,
                'withdraw': True,
            },
            'urls': {
                'logo': 'https://user-images.githubusercontent.com/1294454/27816857-ce7be644-6096-11e7-82d6-3c257263229c.jpg',
                'api': 'https://api.gemini.com',
                'www': 'https://gemini.com',
                'doc': [
                    'https://docs.gemini.com/rest-api',
                    'https://docs.sandbox.gemini.com',
                ],
                'test': 'https://api.sandbox.gemini.com',
                'fees': [
                    'https://gemini.com/fee-schedule/',
                    'https://gemini.com/transfer-fees/',
                ],
            },
            'api': {
                'public': {
                    'get': [
                        'symbols',
                        'pubticker/{symbol}',
                        'book/{symbol}',
                        'trades/{symbol}',
                        'auction/{symbol}',
                        'auction/{symbol}/history',
                    ],
                },
                'private': {
                    'post': [
                        'order/new',
                        'order/cancel',
                        'order/cancel/session',
                        'order/cancel/all',
                        'order/status',
                        'orders',
                        'mytrades',
                        'tradevolume',
                        'balances',
                        'deposit/{currency}/newAddress',
                        'withdraw/{currency}',
                        'heartbeat',
                    ],
                },
            },
        })

    def fetch_markets(self):
        markets = self.publicGetSymbols()
        result = []
        for p in range(0, len(markets)):
            id = markets[p]
            market = id
            uppercase = market.upper()
            base = uppercase[0:3]
            quote = uppercase[3:6]
            symbol = base + '/' + quote
            result.append({
                'id': id,
                'symbol': symbol,
                'base': base,
                'quote': quote,
                'info': market,
                'taker': 0.0025,
            })
        return result

    def fetch_order_book(self, symbol, params={}):
        self.load_markets()
        orderbook = self.publicGetBookSymbol(self.extend({
            'symbol': self.market_id(symbol),
        }, params))
        return self.parse_order_book(orderbook, None, 'bids', 'asks', 'price', 'amount')

    def fetch_ticker(self, symbol, params={}):
        self.load_markets()
        market = self.market(symbol)
        ticker = self.publicGetPubtickerSymbol(self.extend({
            'symbol': market['id'],
        }, params))
        timestamp = ticker['volume']['timestamp']
        baseVolume = market['base']
        quoteVolume = market['quote']
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'high': None,
            'low': None,
            'bid': float(ticker['bid']),
            'ask': float(ticker['ask']),
            'vwap': None,
            'open': None,
            'close': None,
            'first': None,
            'last': float(ticker['last']),
            'change': None,
            'percentage': None,
            'average': None,
            'baseVolume': float(ticker['volume'][baseVolume]),
            'quoteVolume': float(ticker['volume'][quoteVolume]),
            'info': ticker,
        }

    def parse_trade(self, trade, market):
        timestamp = trade['timestampms']
        return {
            'id': str(trade['order_id']),
            'info': trade,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'symbol': market['symbol'],
            'type': None,
            'side': trade['type'],
            'price': float(trade['price']),
            'filled': float(trade['executed_amount']),
            'remaining': float(trade['remaining_amount']),
            'amount': float(trade['original_amount']),
        }

    def fetch_trades(self, symbol, since=None, limit=None, params={}):
        self.load_markets()
        market = self.market(symbol)
        response = self.publicGetTradesSymbol(self.extend({
            'symbol': market['id'],
        }, params))
        return self.parse_trades(response, market, since, limit)

    def fetch_balance(self, params={}):
        self.load_markets()
        balances = self.privatePostBalances()
        result = {'info': balances}
        for b in range(0, len(balances)):
            balance = balances[b]
            currency = balance['currency']
            account = {
                'free': Decimal(balance['available']),
                'used': Decimal(0.0),
                'total': Decimal(balance['amount']),
            }
            account['used'] = account['total'] - account['free']
            result[currency] = account
        return self.parse_balance(result)

    def parse_order_status(self, order):
        if order["is_cancelled"]:
            return 'canceled'
        elif not order["is_live"]:
            return 'closed'
        elif order["remaining_amount"] > "0":
            return 'open'
        else:
            # What should be done?
            return 'open'

    def parse_order(self, order):
        timestamp = order['timestampms']
        status = self.parse_order_status(order)
        price = self.safe_float(order, 'price')
        amount = self.safe_float(order, 'original_amount')
        filled = self.safe_float(order, 'executed_amount')
        remaining = self.safe_float(order, 'remaining_amount')
        return {
            'id': str(order['order_id']),
            'info': order,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'status': status,
            'symbol': order['symbol'],
            'type': None,
            'side': order['type'],
            'price': price,
            'filled': filled,
            'remaining': remaining,
            'amount': amount,
        }

    def fetch_order(self, id, symbol=None, params={}):
        self.load_markets()
        response = self.privatePostOrderStatus(self.extend({
            'order_id': id,
        }, params))
        return self.parse_order(response)

    def create_order(self, symbol, type, side, amount, price=None, params={}):
        self.load_markets()
        if type == 'market':
            raise ExchangeError(self.id + ' allows limit orders only')
        nonce = self.nonce()
        order = {
            'client_order_id': str(nonce),
            'symbol': self.market_id(symbol),
            'amount': str(amount),
            'price': str(price),
            'side': side,
            'type': 'exchange limit',  # gemini allows limit orders only
        }
        response = self.privatePostOrderNew(self.extend(order, params))
        return self.parse_order(response)

    def cancel_order(self, id, symbol=None, params={}):
        self.load_markets()
        response = self.privatePostOrderCancel({'order_id': id})
        return {
            'info': response,
        }

    def deposit_address(self, currency, params={}):
        self.load_markets()
        request = {
            'currency': currency,
        }
        if 'label' in params:
            request['label'] = params['label']

        response = self.privatePostDepositCurrencyNewAddress(self.extend(request, params))
        return {
            'info': response,
        }

    def withdraw(self, currency, amount, address, params={}):
        self.load_markets()
        request = {
            'currency': currency,
            'amount': amount,
            'address': address,
        }
        method = 'privatePostWithdrawals'
        response = self.privatePostWithdrawCurrency(self.extend(request, params))
        return {
            'info': response,
        }

    def withdraw(self, code, amount, address, params={}):
        self.load_markets()
        currency = self.currency(code)
        response = self.privatePostWithdrawCurrency(self.extend({
            'currency': currency['id'],
            'amount': amount,
            'address': address,
        }, params))
        return {
            'info': response,
            'id': self.safe_string(response, 'txHash'),
        }

    def sign(self, path, api='public', method='GET', params={}, headers=None, body=None):
        url = '/' + self.version + '/' + self.implode_params(path, params)
        query = self.omit(params, self.extract_params(path))
        if api == 'public':
            if query:
                url += '?' + self.urlencode(query)
        else:
            self.check_required_credentials()
            nonce = self.nonce()
            request = self.extend({
                'request': url,
                'nonce': nonce,
            }, query)
            payload = self.json(request)
            payload = base64.b64encode(self.encode(payload))
            signature = self.hmac(payload, self.encode(self.secret), hashlib.sha384)
            headers = {
                'Content-Type': 'text/plain',
                'X-GEMINI-APIKEY': self.apiKey,
                'X-GEMINI-PAYLOAD': self.decode(payload),
                'X-GEMINI-SIGNATURE': signature,
            }
        url = self.urls['api'] + url
        return {'url': url, 'method': method, 'body': body, 'headers': headers}

    def request(self, path, api='public', method='GET', params={}, headers=None, body=None):
        response = self.fetch2(path, api, method, params, headers, body)
        if 'result' in response:
            if response['result'] == 'error':
                raise ExchangeError(self.id + ' ' + self.json(response))
        return response
