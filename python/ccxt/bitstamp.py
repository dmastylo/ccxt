from ccxt.base.exchange import Exchange
import math
import datetime
from ccxt.base.errors import ExchangeError


class bitstamp (Exchange):

    def nonce(self):
        return Exchange.milliseconds()

    def describe(self):
        return self.deep_extend(super(bitstamp, self).describe(), {
            'id': 'bitstamp',
            'name': 'Bitstamp',
            'countries': 'GB',
            'rateLimit': 1000,
            'version': 'v2',
            'hasCORS': False,
            'hasFetchOrder': True,
            'urls': {
                'logo': 'https://user-images.githubusercontent.com/1294454/27786377-8c8ab57e-5fe9-11e7-8ea4-2b05b6bcceec.jpg',
                'api': 'https://www.bitstamp.net/api',
                'www': 'https://www.bitstamp.net',
                'doc': 'https://www.bitstamp.net/api',
            },
            'requiredCredentials': {
                'apiKey': True,
                'secret': True,
                'uid': True,
            },
            'api': {
                'public': {
                    'get': [
                        'order_book/{pair}/',
                        'ticker_hour/{pair}/',
                        'ticker/{pair}/',
                        'transactions/{pair}/',
                        'trading-pairs-info/',
                    ],
                },
                'private': {
                    'post': [
                        'balance/',
                        'balance/{pair}/',
                        'user_transactions/',
                        'user_transactions/{pair}/',
                        'open_orders/all/',
                        'open_orders/{pair}',
                        'order_status/',
                        'cancel_order/',
                        'buy/{pair}/',
                        'buy/market/{pair}/',
                        'sell/{pair}/',
                        'sell/market/{pair}/',
                        'ltc_withdrawal/',
                        'ltc_address/',
                        'eth_withdrawal/',
                        'eth_address/',
                        'transfer-to-main/',
                        'transfer-from-main/',
                        'xrp_withdrawal/',
                        'xrp_address/',
                        'withdrawal/open/',
                        'withdrawal/status/',
                        'withdrawal/cancel/',
                        'liquidation_address/new/',
                        'liquidation_address/info/',
                    ],
                },
                'v1': {
                    'post': [
                        'bitcoin_deposit_address/',
                        'unconfirmed_btc/',
                        'bitcoin_withdrawal/',
                    ],
                },
            },
            'fees': {
                'trading': {
                    'tierBased': True,
                    'percentage': True,
                    'taker': 0.25 / 100,
                    'maker': 0.25 / 100,
                    'tiers': {
                        'taker': [
                            [0, 0.25 / 100],
                            [20000, 0.24 / 100],
                            [100000, 0.22 / 100],
                            [400000, 0.20 / 100],
                            [600000, 0.15 / 100],
                            [1000000, 0.14 / 100],
                            [2000000, 0.13 / 100],
                            [4000000, 0.12 / 100],
                            [20000000, 0.11 / 100],
                            [20000001, 0.10 / 100],
                        ],
                        'maker': [
                            [0, 0.25 / 100],
                            [20000, 0.24 / 100],
                            [100000, 0.22 / 100],
                            [400000, 0.20 / 100],
                            [600000, 0.15 / 100],
                            [1000000, 0.14 / 100],
                            [2000000, 0.13 / 100],
                            [4000000, 0.12 / 100],
                            [20000000, 0.11 / 100],
                            [20000001, 0.10 / 100],
                        ],
                    },
                },
                'funding': {
                    'tierBased': False,
                    'percentage': False,
                    'withdraw': {
                        'BTC': 0,
                        'LTC': 0,
                        'ETH': 0,
                        'XRP': 0,
                        'USD': 25,
                        'EUR': 0.90,
                    },
                    'deposit': {
                        'BTC': 0,
                        'LTC': 0,
                        'ETH': 0,
                        'XRP': 0,
                        'USD': 25,
                        'EUR': 0,
                    },
                },
            },
        })

    def fetch_markets(self):
        markets = self.publicGetTradingPairsInfo()
        result = []
        for i in range(0, len(markets)):
            market = markets[i]
            symbol = market['name']
            base, quote = symbol.split('/')
            id = market['url_symbol']
            precision = {
                'amount': market['base_decimals'],
                'price': market['counter_decimals'],
            }
            cost, currency = market['minimum_order'].split(' ')
            active = (market['trading'] == 'Enabled')
            lot = math.pow(10, -precision['amount'])
            result.append({
                'id': id,
                'symbol': symbol,
                'base': base,
                'quote': quote,
                'info': market,
                'lot': lot,
                'active': active,
                'precision': precision,
                'limits': {
                    'amount': {
                        'min': lot,
                        'max': None,
                    },
                    'price': {
                        'min': math.pow(10, -precision['price']),
                        'max': None,
                    },
                    'cost': {
                        'min': float(cost),
                        'max': None,
                    },
                },
            })
        return result

    def fetch_order_book(self, symbol, params={}):
        self.load_markets()
        orderbook = self.publicGetOrderBookPair(self.extend({
            'pair': self.market_id(symbol),
        }, params))
        timestamp = int(orderbook['timestamp']) * 1000
        return self.parse_order_book(orderbook, timestamp)

    def fetch_ticker(self, symbol, params={}):
        self.load_markets()
        ticker = self.publicGetTickerPair(self.extend({
            'pair': self.market_id(symbol),
        }, params))
        timestamp = int(ticker['timestamp']) * 1000
        vwap = float(ticker['vwap'])
        baseVolume = float(ticker['volume'])
        quoteVolume = baseVolume * vwap
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'high': float(ticker['high']),
            'low': float(ticker['low']),
            'bid': float(ticker['bid']),
            'ask': float(ticker['ask']),
            'vwap': vwap,
            'open': float(ticker['open']),
            'close': None,
            'first': None,
            'last': float(ticker['last']),
            'change': None,
            'percentage': None,
            'average': None,
            'baseVolume': baseVolume,
            'quoteVolume': quoteVolume,
            'info': ticker,
        }

    def parse_trade(self, trade, market=None):
        timestamp = None
        if 'date' in trade:
            timestamp = int(trade['date']) * 1000
        elif 'datetime' in trade:
            timestamp = self.parse8601(trade['datetime'])
            #timestamp = int(trade['datetime']) * 1000
        side = 'buy' if (trade['type'] == 0) else 'sell'
        order = None
        if 'id' in trade:
            order = str(trade['id'])
        if 'currency_pair' in trade:
            if trade['currency_pair'] in self.markets_by_id:
                market = self.markets_by_id[trade['currency_pair']]
        if market is not None and 'symbol' in market:
            symbol = market['symbol']
        if 'currency_pair' in trade:
            symbol = trade['currency_pair']

        print(market)
        print(trade)
        return {
            'id': str(trade['id']),
            'info': trade,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'symbol': symbol,
            'order': order,
            'type': None,
            'side': side,
            'price': float(trade['price']),
            'amount': float(trade['amount']),
        }

    def fetch_trades(self, symbol, since=None, limit=None, params={}):
        self.load_markets()
        market = self.market(symbol)
        response = self.publicGetTransactionsPair(self.extend({
            'pair': market['id'],
            'time': 'minute',
        }, params))
        return self.parse_trades(response, market, since, limit)

    def fetch_balance(self, params={}):
        self.load_markets()
        balance = self.privatePostBalance()
        result = {'info': balance}
        currencies = list(self.currencies.keys())
        for i in range(0, len(currencies)):
            currency = currencies[i]
            lowercase = currency.lower()
            total = lowercase + '_balance'
            free = lowercase + '_available'
            used = lowercase + '_reserved'
            account = self.account()
            if free in balance:
                account['free'] = float(balance[free])
            if used in balance:
                account['used'] = float(balance[used])
            if total in balance:
                account['total'] = float(balance[total])
            result[currency] = account
        return self.parse_balance(result)

    def create_order(self, symbol, type, side, amount, price=None, params={}):
        self.load_markets()
        method = 'privatePost' + self.capitalize(side)
        order = {
            'pair': self.market_id(symbol),
            'amount': amount,
        }
        if type == 'market':
            method += 'Market'
        else:
            order['price'] = price
        method += 'Pair'
        response = getattr(self, method)(self.extend(order, params))

        return self.parse_order(response)

    def cancel_order(self, id, symbol=None, params={}):
        self.load_markets()
        return self.privatePostCancelOrder({'id': id})

    def parse_order_status(self, order):
        if 'status' not in order:
            return 'open'
        if (order['status'] == 'Queue') or (order['status'] == 'Open'):
            return 'open'
        if order['status'] == 'Finished':
            return 'closed'
        return order['status']

    def parse_order(order):
        print("\n\n")
        print(order)
    
        status = parse_order_status(order)
    
        if 'transactions' in order:
            print("special case needed here")
    
            filled_amount = 0
            total_fees = 0
            total_price = 0
            ignore_keys = ['fee', 'price', 'datetime', 'usd', 'tid', 'type']
            for transaction in order['transactions']:
                # Fine the crypto currency
                print(transaction)
                total_fees += float(transaction['fee'])
                total_price += float(transaction['price'])
                for trans_key, trans_value in transaction.items():
                    if trans_key in ignore_keys:
                        continue
                    filled_amount += float(trans_value)
            return {
                'id': order['id'],
                'status': status,
                'filled': filled_amount,
                'total_fees': total_fees,
                'total_price': total_price,
            }
    
        # TODO: need to fix this
        timestamp = datetime.datetime.now()
        api_datetime = parse8601(order['datetime'])
        price = safe_float(order, 'price')
        amount = safe_float(order, 'amount')
        filled = safe_float(order, 'executed_amount')
        remaining = safe_float(order, 'amount')
    
        symbol = ""
        if 'currency_pair' in order:
            symbol = order['currency_pair']
    
        if order['type'] == "0":
            order_type = "buy"
        else:
            order_type = "sell"
    
        return {
            'id': str(order['id']),
            'info': order,
            'timestamp': timestamp,
            'datetime': api_datetime,
            'status': status,
            'symbol': symbol,
            'type': order_type,
            'side': order_type,
            'price': price,
            'filled': filled,
            'remaining': remaining,
            'amount': amount,
        }

    def fetch_order_status(self, id, symbol=None):
        self.load_markets()
        response = self.privatePostOrderStatus({'id': id})
        return self.parse_order_status(response)

    def fetch_my_trades(self, symbol=None, since=None, limit=None, params={}):
        self.load_markets()
        market = None
        if symbol:
            market = self.market(symbol)
        pair = market['id'] if market else 'all'
        if pair == 'all':
            response = self.privatePostOpenOrdersAll(params)
        else:
            request = self.extend({'pair': pair}, params)
            response = self.privatePostOpenOrdersPair(request)
        #response = self.privatePostOpenOrdersPair(request)

        return self.parse_trades(response, market, since, limit)

    def fetch_order(self, id, symbol=None, params={}):
        self.load_markets()
        response = self.privatePostOrderStatus(self.extend({
            'id': id,
        }, params))
        return self.parse_order(response)

    def sign(self, path, api='public', method='GET', params={}, headers=None, body=None):
        url = self.urls['api'] + '/'
        if api != 'v1':
            url += self.version + '/'
        url += self.implode_params(path, params)
        query = self.omit(params, self.extract_params(path))
        if api == 'public':
            if query:
                url += '?' + self.urlencode(query)
        else:
            self.check_required_credentials()
            nonce = str(self.nonce())
            auth = nonce + self.uid + self.apiKey
            signature = self.encode(self.hmac(self.encode(auth), self.encode(self.secret)))
            query = self.extend({
                'key': self.apiKey,
                'signature': signature.upper(),
                'nonce': nonce,
            }, query)
            body = self.urlencode(query)
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        return {'url': url, 'method': method, 'body': body, 'headers': headers}

    def request(self, path, api='public', method='GET', params={}, headers=None, body=None):
        response = self.fetch2(path, api, method, params, headers, body)
        if 'status' in response:
            if response['status'] == 'error':
                raise ExchangeError(self.id + ' ' + self.json(response))
        return response
