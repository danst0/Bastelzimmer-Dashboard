#!/usr/bin/env python3

from bottle import route, run, template, static_file, redirect
import json, requests
import re
import logging
import serial, sys
import threading
import time
import serial, glob




logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARN)
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
                'state': 'No connection to bCNC'}
        logger.warn('No connection to cnc4')
        pass



    error = True
    if data != {}:
        logger.debug(data)
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
        logger.info('Sensor data for Dashboard {0}'.format(sensor_output))
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
        #logger.info(lines)
        sanitized_line = ''
        try:
            sanitized_line = lines[0].decode('ascii')
        except:
            logger.error(lines)


        if sanitized_line.startswith('OK'):
            with sensor_lock:
                sensor_output = sanitized_line.strip('\r\n').split(' ')
            logger.debug('Result {0}, moved {1}, light {2}, humidity {3}, temperature {4}'.format(*sensor_output))

    if not cancel_timer.is_set():
        t = threading.Timer(1.0, read_serial)
        t.start()
    else:
        logger.info('Timer successfully canceled')

def scan_serial_ports():
    # scan for available ports. return a list of device names.
    return glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')



logger.info('Available ports')
ports = scan_serial_ports()
logger.info(ports)
jeeUSB_port = ''
for port in ports:
    if not port.endswith('0'):
        jeeUSB_port = port
logger.info('Selecting port {0}'.format(jeeUSB_port))

#ser = serial.Serial(jeeUSB_port, 57600, timeout=1)
try:
    ser = serial.Serial(jeeUSB_port, 57600, timeout=1)
except Exception as e:
    ser = None
    logger.error('Serial connection not possible')
    raise e
else:
    ser.read(10000)
    read_serial()



run(host='0.0.0.0', port=8081, reloader=True)
cancel_timer.set()
#print('Timer canceled')
time.sleep(2)
#print('Exiting')


#http://cnc4:8080/state
# {"G": ["G0", "G54", "G17", "G21", "G90", "G94", "M0", "M5", "M9", "T0", "F0.", "S0."], "color": "LightYellow", "state": "Idle", "msg": "Current: 862 [862]  Completed: 100% [1m58s Tot: 1m58s ]", "wz": 0.0, "wy": 0.0, "wx": 0.0}
# <iframe src="http://cnc4:8080/" width="98%" height="100%" style="border:none"></iframe>