#!flask/bin/python
import base64
import json
import zlib
import pickle
import requests

import pandas as pd
from hashlib import md5

AUTH_SERVER = 'http://localhost:5000'
key = '823fu8d4g'
secret = 'iu4f9f4iou3hf3498hf'


def prepare_args(file, text):
    """
    send the algo as a base64 decoded text object

    :param file: File
    :param text: str
    :return: None, text: str
    """

    if text:
        text = base64.b64encode(text)
    else:
        text = base64.b64encode(bytes(file.read(), 'utf-8')).decode('utf-8')
        file = None
    return file, text


def convert_date(date):
    """
    when transferring dates by json,
    converts it to str
    # any instances which need a conversion,
    # must be done here

    :param date:
    :return: str(date)
    """

    if isinstance(date, pd.Timestamp):
        return date.__str__()


def handle_response(response):
    """
    handles the response given by the server according to it's status code

    :param response: the format returned from a request
    :return: DataFrame/ str
    """
    if response.status_code == 500:
        raise Exception("issues with cloud connections, "
                        "unable to run catalyst on the cloud")
    elif response.status_code == 502:
        raise Exception("The server is down at the moment, please contact "
                        "Catalyst support to fix this issue at "
                        "https://github.com/enigmampc/catalyst/issues/")
    elif response.status_code == 202 or response.status_code == 400:
        lf = json_to_file(response.json()['logs'])
        print(lf.decode('utf-8'))
        return response.json()['error'] if response.json()['error'] else None

    else:  # if the run was successful
        return load_response(response.json())


def load_response(json):
    lf = json_to_file(json['logs'])
    print(lf.decode('utf-8'))
    data_df = pickle.loads(json_to_file(json['data']))
    return data_df

def json_to_file(encoded_data):
    compressed_file = base64.b64decode(encoded_data)
    return zlib.decompress(compressed_file)


def run_server(
        initialize,
        handle_data,
        before_trading_start,
        analyze,
        algofile,
        algotext,
        defines,
        data_frequency,
        capital_base,
        data,
        bundle,
        bundle_timestamp,
        start,
        end,
        output,
        print_algo,
        local_namespace,
        environ,
        live,
        exchange,
        algo_namespace,
        quote_currency,
        live_graph,
        analyze_live,
        simulate_orders,
        auth_aliases,
        stats_output,
):
    if algotext or algofile:
        # argument preparation - encode the file for transfer
        algofile, algotext = prepare_args(algofile, algotext)

    json_file = {'arguments': {
        'initialize': initialize,
        'handle_data': handle_data,
        'before_trading_start': before_trading_start,
        'analyze': analyze,
        'algotext': algotext,
        'defines': defines,
        'data_frequency': data_frequency,
        'capital_base': capital_base,
        'data': data,
        'bundle': bundle,
        'bundle_timestamp': bundle_timestamp,
        'start': start,
        'end': end,
        'local_namespace': local_namespace,
        'environ': None,
        'analyze_live': analyze_live,
        'stats_output': stats_output,
        'algofile': algofile,
        'output': output,
        'print_algo': print_algo,
        'live': live,
        'exchange': exchange,
        'algo_namespace': algo_namespace,
        'quote_currency': quote_currency,
        'live_graph': live_graph,
        'simulate_orders': simulate_orders,
        'auth_aliases': auth_aliases,
    }}

    session = requests.Session()
    response = session.post('{}/backtest/run'.format(AUTH_SERVER), headers={
        'Authorization': 'Digest username="{0}",password="{1}"'.
                            format(key, secret)})

    header = response.headers.get('WWW-Authenticate')
    auth_type, auth_info = header.split(None, 1)
    d = requests.utils.parse_dict_header(auth_info)

    a1 = key + ":" + d['realm'] + ":" + secret
    ha1 = md5(a1.encode('utf-8')).hexdigest()
    a2 = "POST:/backtest/run"
    ha2 = md5(a2.encode('utf-8')).hexdigest()
    a3 = ha1 + ":" + d['nonce'] + ":" + ha2
    result = md5(a3.encode('utf-8')).hexdigest()

    response = session.post('{}/backtest/run'.format(AUTH_SERVER),
                            json=json.dumps(json_file, default=convert_date),
                            verify=False,
                            headers={
                                'Authorization': 'Digest username="{0}",'
                                                 'realm="{1}",nonce="{2}",'
                                                 'uri="/backtest/run",'
                                                 'response="{3}",'
                                                 'opaque="{4}"'.
                            format(key, d['realm'], d['nonce'],
                                   result, d['opaque'])})

    return handle_response(response)
