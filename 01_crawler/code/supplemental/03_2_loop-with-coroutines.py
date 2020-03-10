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
    def __init__(self, url, hostname):
        print('Begin fetching url: %s' % url)
        self.response = b''
        self.url = url
        self.hostname = hostname
        self.__class__.count += 1

    def fetch(self):
        global stopped
        sock = socket.socket()
        sock.setblocking(False)
        try:
            sock.connect((self.hostname, 80))
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

        get = 'GET {} HTTP/1.0\r\nHost: {}\r\n\r\n'.format(self.url, self.hostname)
        print(get)
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
        if self.__class__.count < 6:
            Task(Fetcher(new_url, self.hostname).fetch())
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


# Begin fetching
for url, hostname in [('/353/', 'xkcd.com'), ('/get/', 'httpbin.org')]:
    fetcher = Fetcher(url, hostname)
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
Begin fetching url: /get/
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
GET /353/ HTTP/1.0
Host: xkcd.com


****** read future ******
future name: read, result: None
new future: future name: read, result: None
step end
********* start select *********
on readable callback
set future result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/353/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19923-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.506630,VS0,VE0\r\n\r\n'
step start
old future: future name: read, result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/353/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19923-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.506630,VS0,VE0\r\n\r\n'
b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/353/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19923-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.506630,VS0,VE0\r\n\r\n'
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
GET / HTTP/1.0
Host: xkcd.com


****** read future ******
future name: read, result: None
new future: future name: read, result: None
step end
********* start select *********
on readable callback
set future result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19927-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.648356,VS0,VE0\r\n\r\n'
step start
old future: future name: read, result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19927-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.648356,VS0,VE0\r\n\r\n'
b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19927-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.648356,VS0,VE0\r\n\r\n'
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
GET / HTTP/1.0
Host: xkcd.com


****** read future ******
future name: read, result: None
new future: future name: read, result: None
step end
********* start select *********
on connected callback
set future result: connected
step start
old future: future name: connect, result: connected
connected
连接建立完成，开始读取数据
GET /get/ HTTP/1.0
Host: httpbin.org


****** read future ******
future name: read, result: None
new future: future name: read, result: None
step end
********* start select *********
on readable callback
set future result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-hnd18736-HND\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.785154,VS0,VE0\r\n\r\n'
step start
old future: future name: read, result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-hnd18736-HND\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.785154,VS0,VE0\r\n\r\n'
b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-hnd18736-HND\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.785154,VS0,VE0\r\n\r\n'
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
GET / HTTP/1.0
Host: xkcd.com


****** read future ******
future name: read, result: None
new future: future name: read, result: None
step end
********* start select *********
on readable callback
set future result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-hnd18742-HND\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.918135,VS0,VE0\r\n\r\n'
step start
old future: future name: read, result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-hnd18742-HND\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.918135,VS0,VE0\r\n\r\n'
b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-hnd18742-HND\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583651204.918135,VS0,VE0\r\n\r\n'
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
GET / HTTP/1.0
Host: xkcd.com


****** read future ******
future name: read, result: None
new future: future name: read, result: None
step end
********* start select *********
on readable callback
set future result: b'HTTP/1.1 404 NOT FOUND\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nContent-Type: text/html\r\nContent-Length: 233\r\nConnection: close\r\nServer: gunicorn/19.9.0\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Credentials: true\r\n\r\n<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n<title>404 Not Found</title>\n<h1>Not Found</h1>\n<p>The requested URL was not found on the server.  If you entered the URL manually please check your spelling and try again.</p>\n'
step start
old future: future name: read, result: b'HTTP/1.1 404 NOT FOUND\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nContent-Type: text/html\r\nContent-Length: 233\r\nConnection: close\r\nServer: gunicorn/19.9.0\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Credentials: true\r\n\r\n<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n<title>404 Not Found</title>\n<h1>Not Found</h1>\n<p>The requested URL was not found on the server.  If you entered the URL manually please check your spelling and try again.</p>\n'
b'HTTP/1.1 404 NOT FOUND\r\nDate: Sun, 08 Mar 2020 07:06:43 GMT\r\nContent-Type: text/html\r\nContent-Length: 233\r\nConnection: close\r\nServer: gunicorn/19.9.0\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Credentials: true\r\n\r\n<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n<title>404 Not Found</title>\n<h1>Not Found</h1>\n<p>The requested URL was not found on the server.  If you entered the URL manually please check your spelling and try again.</p>\n'
数据读取完成，开始解析数据

"""