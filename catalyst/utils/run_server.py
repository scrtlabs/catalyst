#!flask/bin/python
import base64

import requests
import pandas as pd
import json


def convert_date(date):
    """
    when transferring dates by json,
    converts it to str
    :param date:
    :return: str(date)
    """
    if isinstance(date, pd.Timestamp):
        return date.__str__()


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
        base_currency,
        live_graph,
        analyze_live,
        simulate_orders,
        auth_aliases,
        stats_output,
        ):

    # address to send
    url = 'http://sandbox.enigma.co/api/catalyst/serve'

    # argument preparation - encode the file for transfer
    if algotext:
        algotext = base64.b64encode(algotext)
    else:
        algotext = base64.b64encode(algofile.read())
        algofile = None

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
        'base_currency': base_currency,
        'live_graph': live_graph,
        'simulate_orders': simulate_orders,
        'auth_aliases': auth_aliases,
    }}

    response = requests.post(url,
                             json=json.dumps(
                                    json_file,
                                    default=convert_date
                                )
                             )
    if response.status_code == 500:
        raise Exception("issues with cloud connections, "
                        "unable to run catalyst on the cloud")
    recieved_data = response.json()
    cloud_log_tail = base64.b64decode(recieved_data["logs"])
    print(cloud_log_tail)
