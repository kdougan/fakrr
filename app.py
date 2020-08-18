# coding: utf-8
import re
import json

from flask import Flask
from flask import request
from flask import jsonify

from faker import Faker

fake = Faker()

# json_payload = '''
# {
#     "__meta": {
#         "seed": 0
#     },
#     "__collection:things": {
#         "__meta": {
#             "repeat": 3000
#         },
#         "id": "<string|md5>",
#         "name": "<string|name>"
#     },
#     "users": {
#         "__meta": {
#             "repeat": 2
#         },
#         "id": "<string|md5>",
#         "name": "<string|name>",
#         "age": "<number|range(13:45)>",
#         "date": "<date|start_date(-30d)|end_date(+30d)> <time>",
#         "favoriteThings": {
#             "__meta": {
#                 "repeat": "1:10",
#                 "collection": {
#                     "name": "things",
#                     "random": true,
#                     "unique": true
#                 }
#             }
#         }
#     }
# }
# '''


app = Flask(__name__)


@app.route('/', methods=['POST'])
def index():
    request.__collections = {}
    json_payload = request.get_json(force=True)
    data = process_payload(json_payload)
    return jsonify(data)


def process_payload(input_payload, is_collection=None):

    working_payload = input_payload.copy()
    use_collection = None
    repeat_result = False

    if '__meta' in input_payload:
        meta = input_payload.get('__meta')
        del working_payload['__meta']
        if 'seed' in meta:
            Faker.seed(meta['seed'])
        if 'repeat' in meta:
            _repeat = meta['repeat']
            if str(_repeat).isdigit():
                repeat_result = max(int(_repeat), 0)
            else:
                low, high = get_min_max(_repeat)
                repeat_result = fake.pyint(min_value=low, max_value=high)
        if 'collection' in meta:
            use_collection = meta['collection']

    return_payload = {}

    if use_collection:
        random = use_collection.get('random', False)
        unique = use_collection.get('unique', False)
        collection = request.__collections.get(use_collection.get('name'))
        if isinstance(collection, list) and random and repeat_result:
            return_payload = fake.random_elements(
                collection, length=min(repeat_result, len(collection)), unique=unique)
        else:
            return_payload = collection
        return return_payload

    if repeat_result:
        return_payload = []
        for _ in range(repeat_result):
            working_dict = {}
            for k, v in working_payload.items():
                if isinstance(v, dict):
                    working_dict[k] = process_payload(input_payload[k])
                else:
                    working_dict[k] = process_key(v)
            if is_collection is not None:
                request.__collections.setdefault(is_collection, [])
                request.__collections[is_collection].append(working_dict)
            else:
                return_payload.append(working_dict)
    else:
        for k, v in working_payload.items():
            if isinstance(v, dict):
                if '__collection' in k:
                    collection_name = k.split(':')[1]
                    processed = process_payload(
                        input_payload[k], collection_name)
                    continue
                else:
                    processed = process_payload(input_payload[k])
            else:
                processed = process_key(v)
            if is_collection is not None:
                request.__collections[is_collection] = working_dict
            else:
                return_payload[k] = processed

    return return_payload


def process_key(value):
    matches = re.finditer(r'<(.*?)>', value, re.MULTILINE)
    is_number = False
    for matchNum, match in enumerate(matches, start=1):
        for match_group in match.groups():
            opts = match_group.split('|')
            key = opts[0]
            opts = opts[1:]
            parsed = ''
            if key == 'string':
                parsed = parse_string(opts)
            elif key == 'number':
                is_number = True
                parsed = parse_number(opts)
            elif key == 'date':
                parsed = parse_date(opts)
            elif key == 'time':
                parsed = parse_time(opts)
            value = value.replace(f'<{match_group}>', str(parsed), 1)
    if is_number and value.isdigit():
        value = int(value)
    return value


def parse_date(options=[]):
    start_date = '-30d'
    end_date = 'today'
    pattern = '%Y-%m-%d'
    for option in options:
        opt = re.search(r'(\w+)(\s?\(.*?\))?', option).groups()[0]
        arg = re.search(r'\((.*?)\)', option).groups()[0]
        if opt == 'start_date':
            start_date = arg
        elif opt == 'end_date':
            end_date = arg
        elif opt == 'format':
            pattern = arg
    dte = fake.date_between(start_date=start_date, end_date=end_date)
    return dte.strftime(pattern)


def parse_time(options=[]):
    dte = fake.time_object()
    pattern = '%H:%M:%S'
    for option in options:
        opt = re.search(r'(\w+)(\s?\(.*?\))?', option).groups()[0]
        arg = re.search(r'\((.*?)\)', option).groups()[0]
        if opt == 'format':
            pattern = arg
        elif opt == 'floor':
            pass
    return dte.strftime(pattern)


def parse_string(options=[]):
    rtn = fake.word()
    for option in options:
        opt = re.search(r'(\w+)(\s?\(.*?\))?', option).groups()[0]
        if opt == 'number':
            return parse_number()
        elif opt == 'name':
            rtn = fake.name()
        elif opt == 'first_name':
            rtn = fake.first_name()
        elif opt == 'last_name':
            rtn = fake.last_name()
        elif opt == 'uuid':
            rtn = fake.uuid4()
        elif opt == 'md5':
            rtn = fake.md5()
        elif opt == 'paragraph':
            rtn = fake.paragraph()
        elif opt == 'sentence':
            rtn = fake.sentence()
        elif opt == 'word':
            rtn = fake.word()

    return rtn


def parse_number(options=[]):
    rtn = fake.pyint()
    for option in options:
        opt = re.search(r'(\w+)(\s?\(.*?\))?', option).groups()[0]
        if opt in ['digits', 'range']:
            template = re.search(r'\((.*?)\)', option).groups()[0]
            low, high = get_min_max(template)
            if opt == 'digits':
                r = fake.pyint(low, high)
                rtn = fake.pystr_format(string_format=f'{"#"*r}')
            elif opt == 'range':
                rtn = fake.pyint(min_value=low, max_value=high)
    return rtn


def get_min_max(template, abs_min=0, abs_high=10):
    if ':' not in template:
        template += ':'
    parts = template.split(':')
    low = parts[0]
    high = parts[1]
    if not low and low != 0:
        low = abs_min
    if not high and high != 0:
        high = abs_max
    return int(low), int(high)


if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
