#!/usr/bin/env python3

from bottle import route, run, template, static_file, redirect
import json, requests
import re
import logging
import serial, sys
import threading
import time




logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
sensor_lock = threading.Lock()
sensor_output = []


url = 'http://cnc4:8080/state'

cancel_timer = threading.Event()

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
    global sensor_output
    data = {}
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



    error = True
    if data != {}:
        logger.info(data)
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
        error = False
    with sensor_lock:
        data['sensors'] = sensor_output
        print(sensor_output)
        error = False
    if not error:
        return template('results', **data)
    else:
        #logger.info('No connection to cnc4')
        return template('error')

def read_serial():
    global sensor_output
    lines = []
    try:
        lines = ser.readlines(1)
    except serial.serialutil.SerialException as e:
        pass
    except BlockingIOError as eb:
        logger.warn('Serial blocked')

    if len(lines) > 0:
        try:
            sanitized_line = lines[0].decode('ascii')
        except:
            logger.error(lines)
        else:
            sanitized_line = ''
        if sanitized_line.startswith('OK'):
            with sensor_lock:
                sensor_output = sanitized_line.split(' ')
            logger.info('-'*40)
            logger.info('Result', sensor_output[0])
            logger.info('Moved', sensor_output[1])
            logger.info('Light', sensor_output[2])
            logger.info('Humidity', sensor_output[3])
            logger.info('Temp', int(sensor_output[4])/10.0)

    if not cancel_timer.is_set():
        t = threading.Timer(1.0, read_serial)
        t.start()
    else:
        logger.info('Timer successfully canceled')


try:
    ser = serial.Serial('/dev/ttyUSB1', 57600, timeout=1)
except:
    ser = None
    logger.error('Serial connection not possible')
else:
    read_serial()


run(host='0.0.0.0', port=8081, reloader=True)
cancel_timer.set()
#print('Timer canceled')
time.sleep(2)
#print('Exiting')


#http://cnc4:8080/state
# {"G": ["G0", "G54", "G17", "G21", "G90", "G94", "M0", "M5", "M9", "T0", "F0.", "S0."], "color": "LightYellow", "state": "Idle", "msg": "Current: 862 [862]  Completed: 100% [1m58s Tot: 1m58s ]", "wz": 0.0, "wy": 0.0, "wx": 0.0}
# <iframe src="http://cnc4:8080/" width="98%" height="100%" style="border:none"></iframe>