#!/usr/bin/env python3

from bottle import route, run, template, static_file, redirect
import json, requests
import re
import logging
import serial, sys
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARN)


url = 'http://cnc4:8080/state'



@route('/')
def root():
    redirect('/dashboard')

@route('/hello/<name>')
def index(name):
    return template('<b>Hello {{name}}</b>!', name=name)


@route('/static/:filename#.*#')
def send_static(filename):
    return static_file(filename, root='./static/')

def get_seconds(time_string):
    result = re.match('(?P<minutes>[0-9]*)m(?P<seconds>[0-9]*)s', time_string)
    seconds = int(result.group('minutes')) * 60 + int(result.group('seconds'))
    return seconds

def get_time_string(seconds):
    result = str(int(seconds/60)) + 'm' + str(seconds % 60) + 's'
    return result

@route('/dashboard')
def index():
    data = None
    try:
        resp = requests.get(url=url)
        data = json.loads(resp.text)
    except:
        data = {'wz': 0.0, 'msg': 'Current: 862 [862]  Completed: 100% [1m58s Tot: 1m58s ]',
                'color': 'LightYellow', 'wx': 0.0, 'wy': 0.0,
                'G': ['G0', 'G54', 'G17', 'G21', 'G90', 'G94', 'M0', 'M5', 'M9', 'T0', 'F0.', 'S0.'],
                'state': 'Idle'}
        logger.error('No connection to cnc4')
        pass


    lines = ser.readlines(1)
    print(lines)


    if data != None:
        print(data)
        #{'wz': 0.0, 'msg': 'Current: 862 [862]  Completed: 100% [1m58s Tot: 1m58s ]',
        # 'color': 'LightYellow', 'wx': 0.0, 'wy': 0.0,
        # 'G': ['G0', 'G54', 'G17', 'G21', 'G90', 'G94', 'M0', 'M5', 'M9', 'T0', 'F0.', 'S0.'],
        # 'state': 'Idle'}
        #print(data['msg'])
        data['locked'] = False
        if data['msg'] != '':
            split_result = re.match('Current:\s(?P<current_line>[0-9]*)\s\[(?P<total_lines>[0-9]*)\].*\s(?P<percentage>[0-9]*)%\s\[(?P<current_minutes>[0-9ms]*)\sTot:\s(?P<total_minutes>[0-9ms]*)\s\]',
                 data['msg'])
            data['current_line'] = split_result.group('current_line')
            data['total_lines'] = split_result.group('total_lines')
            data['percentage'] = split_result.group('percentage')
            data['current_minutes'] = split_result.group('current_minutes')
            data['total_minutes'] = split_result.group('total_minutes')
            data['ETA'] = get_time_string(get_seconds(data['total_minutes']) - get_seconds(data['current_minutes']))
        locked_strings = ['Reset to continue', "'$H'|'$X' to unlock"]

        if ' '.join(data['G']) in locked_strings:

            data['locked'] = True
        return template('results', **data)
    else:
        #logger.info('No connection to cnc4')
        return template('error')


ser = serial.Serial('/dev/ttyUSB1', 57600)
run(host='0.0.0.0', port=8081, reloader=True)

#http://cnc4:8080/state
# {"G": ["G0", "G54", "G17", "G21", "G90", "G94", "M0", "M5", "M9", "T0", "F0.", "S0."], "color": "LightYellow", "state": "Idle", "msg": "Current: 862 [862]  Completed: 100% [1m58s Tot: 1m58s ]", "wz": 0.0, "wy": 0.0, "wx": 0.0}
# <iframe src="http://cnc4:8080/" width="98%" height="100%" style="border:none"></iframe>