import requests
import base64


def run_server(
        algofile,
        algotext,
        define,
        capital_base,
        end,
        output,
        print_algo,
        live,
        exchange,
        algo_namespace,
        base_currency,
        live_graph,
        simulate_orders,
        auth_aliases,
    ):

    json_file = {'arguments': {
        '--algofile': base64.b64encode(algofile.read()),
        '--algotext': algotext,
        '--define': define,
        '--capital-base': capital_base,
        '--end': end,
        '--output': output,
        'print-algo': print_algo,
        'live': True,
        '--exchange': exchange,
        '--algo-namespace': algo_namespace,
        '--base-currency': base_currency,
        'live-graph': live_graph,
        'simulate-orders': simulate_orders,
        '--auth-aliases': auth_aliases,
    }}

    url = 'http://127.0.0.1:5000/todo/api/v1.0/tasks'
    response = requests.post(url, json=json_file)
