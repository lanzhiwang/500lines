#!/usr/bin/env python3.4

"""Sloppy little crawler, demonstrates a hand-made event loop and coroutines.

First read loop-with-callbacks.py. This example builds on that one, replacing
callbacks with generators.
"""

from selectors import *
import socket
import re
import urllib.parse
import time


selector = DefaultSelector()
stopped = False

class Future:
    def __init__(self, name):
        self.name = name
        self.result = None
        self._callbacks = []

    def __str__(self):
        return 'future name: %s, result: %s' % (self.name, self.result)

    def add_done_callback(self, fn):
        self._callbacks.append(fn)

    def set_result(self, result):
        print('set future result: %s' % result)
        self.result = result
        for fn in self._callbacks:
            fn(self)


class Fetcher:
    count = 0
    def __init__(self, url):
        print('Begin fetching url: %s' % url)
        self.response = b''
        self.url = url
        self.__class__.count += 1

    def fetch(self):
        global stopped
        sock = socket.socket()
        sock.setblocking(False)
        try:
            sock.connect(('xkcd.com', 80))
        except BlockingIOError:
            pass

        print('****** connect future ******')
        connect_future = Future('connect')
        print(connect_future)

        def on_connected():
            print('on connected callback')
            connect_future.set_result('connected')

        selector.register(sock.fileno(), EVENT_WRITE, on_connected)

        connect_future_result = yield connect_future
        print(connect_future_result)
        selector.unregister(sock.fileno())

        print('连接建立完成，开始读取数据')

        get = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(self.url)
        sock.send(get.encode('ascii'))

        print('****** read future ******')
        read_future = Future('read')
        print(read_future)

        def on_readable():
            print('on readable callback')
            read_future.set_result(sock.recv(4096))  # Read 4k at a time.

        selector.register(sock.fileno(), EVENT_READ, on_readable)
        self.response = yield read_future
        print(self.response)
        selector.unregister(sock.fileno())

        print('数据读取完成，开始解析数据')

        new_url = '/'
        if self.__class__.count < 3:
            Task(Fetcher(new_url).fetch())
        else:
            stopped = True


class Task:
    def __init__(self, coro):
        print('init task')
        self.coro = coro

        print('****** init future ******')
        init_future = Future('init')
        init_future.set_result(None)
        print(init_future)

        self.step(init_future)

    def step(self, future):
        print('step start')
        print('old future: %s' % future)
        try:
            next_future = self.coro.send(future.result)
        except StopIteration:
            return

        print('new future: %s' % next_future)
        next_future.add_done_callback(self.step)
        print('step end')


# Begin fetching http://xkcd.com/353/
fetcher = Fetcher('/353/')
Task(fetcher.fetch())

while not stopped:
    print('********* start select *********')
    events = selector.select()
    for event_key, event_mask in events:
        callback = event_key.data
        callback()

"""
Begin fetching url: /353/
init task
****** init future ******
set future result: None
future name: init, result: None
step start
old future: future name: init, result: None
****** connect future ******
future name: connect, result: None
new future: future name: connect, result: None
step end
********* start select *********
on connected callback
set future result: connected
step start
old future: future name: connect, result: connected
connected
连接建立完成，开始读取数据
****** read future ******
future name: read, result: None
new future: future name: read, result: None
step end
********* start select *********
on readable callback
set future result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/353/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 03:23:34 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19925-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583637815.776190,VS0,VE0\r\n\r\n'
step start
old future: future name: read, result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/353/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 03:23:34 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19925-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583637815.776190,VS0,VE0\r\n\r\n'
b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/353/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 03:23:34 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19925-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583637815.776190,VS0,VE0\r\n\r\n'
数据读取完成，开始解析数据
Begin fetching url: /
init task
****** init future ******
set future result: None
future name: init, result: None
step start
old future: future name: init, result: None
****** connect future ******
future name: connect, result: None
new future: future name: connect, result: None
step end
********* start select *********
on connected callback
set future result: connected
step start
old future: future name: connect, result: connected
connected
连接建立完成，开始读取数据
****** read future ******
future name: read, result: None
new future: future name: read, result: None
step end
********* start select *********
on readable callback
set future result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 03:23:34 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19926-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583637815.895729,VS0,VE0\r\n\r\n'
step start
old future: future name: read, result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 03:23:34 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19926-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583637815.895729,VS0,VE0\r\n\r\n'
b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 03:23:34 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19926-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583637815.895729,VS0,VE0\r\n\r\n'
数据读取完成，开始解析数据
Begin fetching url: /
init task
****** init future ******
set future result: None
future name: init, result: None
step start
old future: future name: init, result: None
****** connect future ******
future name: connect, result: None
new future: future name: connect, result: None
step end
********* start select *********
on connected callback
set future result: connected
step start
old future: future name: connect, result: connected
connected
连接建立完成，开始读取数据
****** read future ******
future name: read, result: None
new future: future name: read, result: None
step end
********* start select *********
on readable callback
set future result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 03:23:35 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19949-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583637815.036291,VS0,VE0\r\n\r\n'
step start
old future: future name: read, result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 03:23:35 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19949-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583637815.036291,VS0,VE0\r\n\r\n'
b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 03:23:35 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19949-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583637815.036291,VS0,VE0\r\n\r\n'
数据读取完成，开始解析数据

"""