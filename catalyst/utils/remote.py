#!flask/bin/python
import json
import os
import sys

import requests
from hashlib import md5
from logbook import Logger

from catalyst.utils.remote_utils import BACKTEST_PATH, STATUS_PATH, POST, \
    GET, EXCEPTION_LOG, convert_date, prepare_args, handle_status, \
    is_valid_uuid
from catalyst.exchange.utils.exchange_utils import get_remote_auth,\
    get_remote_folder
from catalyst.exchange.exchange_errors import RemoteAuthEmpty

log = Logger('remote')

# AUTH_SERVER = 'http://localhost:5000'
AUTH_SERVER = "https://sandbox2.enigma.co"

BACKTEST = 'backtest'
STATUS = 'status'


def handle_response(response, mode):
    """
    handles the response given by the server according to it's status code

    :param response: the format returned from a request
    :param mode: Backtest/ status
    :return: DataFrame/ str
    """
    if response.status_code == 500:
        raise Exception("issues with cloud connections,\n"
                        "unable to run catalyst on the cloud,\n"
                        "try running again and if you get the same response,\n"
                        + EXCEPTION_LOG
                        )
    elif response.status_code == 502:
        raise Exception("The server is down at the moment,\n" + EXCEPTION_LOG)
    elif response.status_code == 400 or response.status_code == 401:
        raise Exception("There is a connection but it was aborted due "
                        "to wrong arguments given to the server.\n" +
                        response.content.decode('utf-8') + '\n' +
                        EXCEPTION_LOG)
    elif response.status_code == 202:
        raise Exception("The server is under maintenance. "
                        "please try again in a few minutes")
    else:  # if the run was successful
        if mode == BACKTEST:
            algo_id = response.json()['algo_id']
            log.info('In order to follow your algo run use the following id: '
                     + algo_id)
            return algo_id
        elif mode == STATUS:
            return handle_status(response.json())


def remote_backtest(
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
        mail,
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
        'mail': mail,
        'py_version': sys.version_info[0],  # the python version running on
                                            # the client's side. 2 or 3
    }}
    response = send_digest_request(
        json_file=json_file, path=BACKTEST_PATH, method=POST
    )
    return handle_response(response, BACKTEST)


def get_remote_status(algo_id):
    if not is_valid_uuid(algo_id):
        raise Exception("the id you entered is invalid! "
                        "please enter a valid id.")
    json_file = {'algo_id': algo_id}
    response = send_digest_request(
        json_file=json_file, path=STATUS_PATH, method=GET
    )
    return handle_response(response, STATUS)


def send_digest_request(json_file, path, method):
    try:
        key, secret = retrieve_remote_auth()
    except json.JSONDecodeError as e:
        log.error("your key and secret aren't stored properly\n{}".
                  format(e.msg))
        raise
    json_file['key'] = key
    session = requests.Session()
    if method == POST:
        response = session.post('{}{}'.format(AUTH_SERVER, path),
                                headers={
                                    'Authorization':
                                        'Digest username="{0}",'
                                        'password="{1}"'.format(key, secret)
                                },
                                )
    else:  # method == GET:
        response = session.get('{}{}'.format(AUTH_SERVER, path),
                               headers={'Authorization':
                                        'Digest username="{0}", '
                                        'password="{1}"'.
                                        format(key, secret)},
                               )

    header = response.headers.get('WWW-Authenticate')
    auth_type, auth_info = header.split(None, 1)
    d = requests.utils.parse_dict_header(auth_info)

    a1 = key + ":" + d['realm'] + ":" + secret
    ha1 = md5(a1.encode('utf-8')).hexdigest()
    a2 = "{}:{}".format(method, path)
    ha2 = md5(a2.encode('utf-8')).hexdigest()
    a3 = ha1 + ":" + d['nonce'] + ":" + ha2
    result = md5(a3.encode('utf-8')).hexdigest()

    if method == POST:
        return session.post('{}{}'.format(AUTH_SERVER, path),
                            json=json.dumps(json_file, default=convert_date),
                            headers={
                                'Authorization': 'Digest username="{0}",'
                                                 'realm="{1}",nonce="{2}",'
                                                 'uri="{3}",'
                                                 'response="{4}",'
                                                 'opaque="{5}"'.
                            format(key, d['realm'], d['nonce'], path,
                                   result, d['opaque'])})
    else:  # method == GET
        return session.get('{}{}'.format(AUTH_SERVER, path),
                           json=json.dumps(json_file, default=convert_date),
                           headers={'Authorization':
                                    'Digest username="{0}", realm="{1}",'
                                    'nonce="{2}",uri="{3}", '
                                    'response="{4}",opaque="{5}"'.
                                    format(key, d['realm'], d['nonce'],
                                           path, result, d['opaque'])})


def retrieve_remote_auth():
    remote_auth_dict = get_remote_auth()
    has_auth = (remote_auth_dict['key'] != '' and
                remote_auth_dict['secret'] != '')
    if not has_auth:
        raise RemoteAuthEmpty(
            filename=os.path.join(get_remote_folder(), 'remote_auth.json')
        )
    else:
        return remote_auth_dict['key'], remote_auth_dict['secret']
