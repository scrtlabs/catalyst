#!flask/bin/python
import base64

import requests
import pandas as pd
import json
from flask import (
                    Flask, jsonify, abort,
                    make_response, request,
                    url_for,
                )

from catalyst.utils.run_algo import _run


def convert_date(date):
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

    url = 'http://127.0.0.1:5000/api/v1.0/tasks'
    response = requests.post(url, json=json.dumps(
        json_file, default=convert_date))


app = Flask(__name__)


def exec_catalyst(arguments):
    arguments['algotext'] = base64.b64decode(arguments['algotext'])
    if arguments['start'] is not None:
        arguments['start'] = pd.Timestamp(arguments['start'])
    if arguments['end'] is not None:
        arguments['end'] = pd.Timestamp(arguments['end'])
    _run(**arguments)


def make_public_task(task):
    new_task = {}
    for field in task:
        if field == 'id':
            new_task['uri'] = url_for('get_task', task_id=task['id'], _external=True)
        else:
            new_task[field] = task[field]
    return new_task


# @app.route('/')
# def index():
#     return "Hello, World!"


# @app.route('/api/v1.0/tasks/<int:task_id>', methods=['GET'])
# def get_task(task_id):
#     task = [task for task in tasks if task['id'] == task_id]
#     if len(task) == 0:
#         abort(404)
#     return jsonify({'task': make_public_task(task[0])})
#
#
# @app.route('/api/v1.0/tasks', methods=['GET'])
# def get_tasks():
#     return jsonify({'tasks': [make_public_task(task) for task in tasks]})


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 400)


@app.route('/api/v1.0/tasks', methods=['POST'])
def create_task():
    if not request.json or 'arguments' not in request.json:
        abort(400)
    arguments = json.loads(request.json)['arguments']
    exec_catalyst(arguments)
    # task = {
    #     'id': tasks[-1]['id'] + 1,
    #     'arguments': request.json['arguments'],
    #     'done': False
    # }
    # tasks.append(task)
    #
    # return jsonify({'task': [make_public_task(task)]}), 201
    return jsonify({"success": "man"}), 201

# @app.route('/api/v1.0/tasks/<int:task_id>', methods=['PUT'])
# def update_task(task_id):
#     task = [task for task in tasks if task['id'] == task_id]
#     if len(task) == 0:
#         abort(404)
#     if not request.json:
#         abort(400)
#     if 'arguments' in request.json and type(request.json['arguments']) != unicode:
#         abort(400)
#     if 'description' in request.json and type(request.json['description']) is not unicode:
#         abort(400)
#     if 'done' in request.json and type(request.json['done']) is not bool:
#         abort(400)
#     task[0]['arguments'] = request.json.get('arguments', task[0]['arguments'])
#     task[0]['done'] = request.json.get('done', task[0]['done'])
#     return jsonify({'task': [make_public_task(task[0])]})
#
#
# @app.route('/api/v1.0/tasks/<int:task_id>', methods=['DELETE'])
# def delete_task(task_id):
#     task = [task for task in tasks if task['id'] == task_id]
#     if len(task) == 0:
#         abort(404)
#     tasks.remove(task[0])
#     return jsonify({'result': True})


if __name__ == '__main__':
    app.run(debug=True, threaded=True)
