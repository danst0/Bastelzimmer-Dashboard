#!/usr/bin/env python3

"""Dashboard

Usage:
  dashboard.py
  dashboard.py (-v | --verbose)
  dashboard.py (-d | --debug)
  dashboard.py (-h | --help)
  dashboard.py --version

Options:
  -v --verbose  Verbose log level
  -d --debug    Debug log level
  -h --help     Show this screen.
  --version     Show version.

"""

from bottle import route, run, template, static_file, redirect
import json, requests
import re
import logging
import serial, sys
import threading
import time
import serial, glob
import os
import random
from docopt import docopt


logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARN)
sensor_lock = threading.Lock()
sensor_output = []


url = 'http://cnc4:8080/state'
my_address = '1'

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
    result = re.match('((?P<minutes>[0-9]*)m)?(?P<seconds>[0-9]*)s', time_string)
    try:
        mins = int(result.group('minutes'))
    except:
        mins = 0
    seconds = mins * 60 + int(result.group('seconds'))
    return seconds

def get_time_string(seconds):
    result = str(int(seconds/60)) + 'm' + str(seconds % 60) + 's'
    return result


def poll_data():
    global sensor_output
    data = {}
    try:
        resp = requests.get(url=url)
        data = json.loads(resp.text)
    except:
        data = {'wz': 0.0, 'msg': 'Current: 0 [0]  Completed: 100% [0m0s Tot: 0m0s ]',
                'color': 'LightYellow', 'wx': 0.0, 'wy': 0.0,
                'G': ['G0', 'G54', 'G17', 'G21', 'G90', 'G94', 'M0', 'M5', 'M9', 'T0', 'F0.', 'S0.'],
                'state': 'No connection to bCNC'}
        logger.warn('No connection to cnc4')
        pass
        #'msg': 'Current: 61 [699]  Completed: 7% [35s Tot: 6m44s Rem: 6m09s]'



    if data != {}:
        logger.debug(data)
        data['locked'] = False
        if data['msg'] != '':
            split_result = re.match('Current:\s(?P<current_line>[0-9]*)\s\[(?P<total_lines>[0-9]*)\].*\s(?P<percentage>[0-9]*)%\s\[(?P<current_minutes>[0-9ms]*)\sTot:\s(?P<total_minutes>[0-9ms]*)\s(Rem:\s(?P<rem_minutes>[0-9ms]*))?\]',
                 data['msg'])
            if split_result:
                data['current_line'] = split_result.group('current_line')
                data['total_lines'] = split_result.group('total_lines')
                data['percentage'] = split_result.group('percentage')
                data['current_minutes'] = split_result.group('current_minutes')
                data['total_minutes'] = split_result.group('total_minutes')
                data['ETA'] = get_time_string(get_seconds(data['total_minutes']) - get_seconds(data['current_minutes']))
            else:
                logger.debug('Could not match msg: {0}'.format(data['msg']))

        locked_strings = ['Reset to continue', "'$H'|'$X' to unlock"]

        if ' '.join(data['G']) in locked_strings:

            data['locked'] = True
    with sensor_lock:
        data['sensors'] = sensor_output
        logger.info('Sensor data for Dashboard {0}'.format(sensor_output))
    return data

@route('/dashboard')
def index():
    data = poll_data()
    if data != {}:
        logger.info(data)
        return template('results', **data)
    else:
        #logger.info('No connection to cnc4')
        return template('error')



def read_serial():
    global sensor_output
    lines = []
    #ser.write(b'h\n')
    if ser.isOpen():
        try:
            lines = ser.readlines(5)
        except serial.serialutil.SerialException as e:
            raise
        except BlockingIOError as eb:
            logger.warn('Serial blocked')
            raise
    #logger.info('Read line')

    for no, line in enumerate(lines):

        sanitized_line = ''
        try:
            sanitized_line = line.decode('ascii')
        except:
            logger.error('Error with line')
        logger.info('Line number: {0}, Text: {1}'.format(no+1, sanitized_line))

        if sanitized_line.startswith('OK 5'):
            logger.info('Received from Bastelzimmer Display: {0}'.format(sanitized_line))
            #with sensor_lock:
            #    sensor_output = sanitized_line.strip('\r\n').split(' ')
            #if len(sensor_output) >= 5:
            #    address = sensor_output[1]
            #    logger.info('Result {0}, moved {1}, light {2}, humidity {3}, temperature {4}'.format(*sensor_output))
            #else:
            #    logger.info('Output less than 5 ' + str(sensor_output))


        elif sanitized_line.startswith('OK'):
            with sensor_lock:
                sensor_output = sanitized_line.strip('\r\n').split(' ')
                logger.debug('Unsanitized sensor output: {0}'.format(sensor_output))
            if len(sensor_output) == 5:
                address = sensor_output[1]
                logger.info('Result {0}, moved {1}, light {2}, humidity {3}, temperature {4}'.format(*sensor_output))
            else:
                logger.info('Output other than 5 ' + str(sensor_output))

        if sanitized_line.startswith('TEMP'):
            sanitized_line = sanitized_line[5:].strip()
            logger.info('Current water temperature ' + str(sanitized_line))
            ext_temperature = int(float(sanitized_line)*10 + 5)
            byte_1 = int(ext_temperature / 256)
            byte_2 = ext_temperature % 256

            send_out_bytes = ''.join(['99,', str(byte_1), ',', str(byte_2), ',0a']).encode()


            logger.info('Sending out Bytes with temperature {0}'.format(send_out_bytes))

            logger.debug('Serial port {0}'.format(ser.port))
            ser.write(send_out_bytes)

            # After temperature send out Status
            data = poll_data()
            if data['state'] == 'Idle':
                status = 0
            elif data['state'] == 'No connection to bCNC':
                status = 1
            elif data['state'] == 'Run':
                status = 2    
            elif data['state'] == 'Connected':
                status = 3
            elif data['state'] == 'Hold':
                status = 4

            elif data['state'].startswith('error'):
                status = 5
            elif data['state'] == 'Alarm':
                status = 6
            else:
                logger.info('Current status not found: {0}'.format(data['state']))
                status = 255
            #status = random.randrange(0,3)
            percentage = 0
            if 'percentage' in data.keys():
                percentage = int(data['percentage'])
            send_out_bytes = ''.join(['100,', str(status),',', str(percentage), ',0a']).encode()
            logger.info('Sending out Bytes with Percentage {0}'.format(send_out_bytes))
            ser.write(send_out_bytes)


    if not cancel_timer.is_set():
        t = threading.Timer(10.0, read_serial)
        t.start()
    else:
        logger.info('Timer successfully canceled')

def scan_serial_ports():
    # scan for available ports. return a list of device names.
    return glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')


if __name__ == '__main__':

    jeeUSB_port = ''
    ser = None
    #print(os.environ)
    if 'BOTTLE_CHILD' in os.environ and os.environ['BOTTLE_CHILD'] == 'true':
        arguments = docopt(__doc__, version='Dashboard 1.2')
        #print(arguments)
        if arguments['--verbose']:
            logger.setLevel(logging.INFO)
            logger.info('Log level INFO')
        if arguments['--debug']:
            logger.setLevel(logging.DEBUG)
            logger.debug('Log level DEBUG')
        logger.info('Available ports')

        ports = scan_serial_ports()
        logger.info(ports)

        for port in ports:
            if not port.endswith('1') and port.find('USB') != -1:
                jeeUSB_port = port
                logger.info('Selecting port {0}'.format(jeeUSB_port))

                #ser = serial.Serial(jeeUSB_port, 57600, timeout=1)
                try:
                    ser = serial.Serial(jeeUSB_port, 57600, timeout=1)
                except Exception as e:
                    ser = None
                    logger.error('Serial connection not possible')
                    raise e
                try:
                    logger.info(ser.readlines(100))
                except:
                    pass


        if ser:
            logger.info('Successful connection to serial port')
            try:
                ser.read(10000)
                logger.info('Flushed cache')
            except:
                raise
            read_serial()
            #read_temperature()


    # do not use reloader else serial port is executed twice (all code above!!)
    run(host='0.0.0.0', port=8081, reloader=True)
    cancel_timer.set()
    #print('Timer canceled')
    time.sleep(2)
    #print('Exiting')
    if ser and ser.isOpen():
        ser.close()


    #http://cnc4:8080/state
    # {"G": ["G0", "G54", "G17", "G21", "G90", "G94", "M0", "M5", "M9", "T0", "F0.", "S0."], "color": "LightYellow", "state": "Idle", "msg": "Current: 862 [862]  Completed: 100% [1m58s Tot: 1m58s ]", "wz": 0.0, "wy": 0.0, "wx": 0.0}
    # <iframe src="http://cnc4:8080/" width="98%" height="100%" style="border:none"></iframe>
