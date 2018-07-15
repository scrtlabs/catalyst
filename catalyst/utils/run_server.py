#!flask/bin/python
import base64

import requests
import pandas as pd
import json
import zlib
import pickle
from logbook.queues import ZeroMQSubscriber

subscriber = ZeroMQSubscriber(uri="tcp://34.202.72.107:5050")
# subscriber = ZeroMQSubscriber(uri="tcp://127.0.0.1:5050")
controller = subscriber.dispatch_in_background()


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

    # address to send
    url = 'http://34.202.72.107:5000/api/catalyst/serve'
    # url = 'http://127.0.0.1:5000/api/catalyst/serve'

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

    # call the server with the following arguments
    # if any issues raised related to the format of the dates, convert them
    response = requests.post(url,
                             json=json.dumps(
                                    json_file,
                                    default=convert_date
                                ),
                             verify=False,
                             )

    # close the handlers, which are not needed anymore
    controller.stop()
    subscriber.close()

    if response.status_code == 500:
        raise Exception("issues with cloud connections, "
                        "unable to run catalyst on the cloud")
    elif response.status_code == 502:
        raise Exception("The server is down at the moment, please contact "
                        "Catalyst support to fix this issue at "
                        "https://github.com/enigmampc/catalyst/issues/")
    elif response.status_code == 202 or response.status_code == 400:
        print(response.json()['error']) if response.json()['error'] else None

    else:  # if the run was successful
        received_data = response.json()
        data_perf_compressed = base64.b64decode(received_data["data"])
        data_perf_pickled = zlib.decompress(data_perf_compressed)
        data_perf = pickle.loads(data_perf_pickled)
        print(data_perf)
