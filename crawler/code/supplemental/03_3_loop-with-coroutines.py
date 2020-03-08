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

urls_todo = set(['/'])
urls_seen = set(['/'])
selector = DefaultSelector()
stopped = False
concurrency_achieved = 0

class Future:
    def __init__(self, name):
        self.name = name
        self.result = None
        self._callbacks = []

    def add_done_callback(self, fn):
        self._callbacks.append(fn)

    def set_result(self, result):
        print('set future result: %s' % result)
        self.result = result
        for fn in self._callbacks:
            fn(self)

    def __iter__(self):
        print('__iter__')
        yield self  # This tells Task to wait for completion.
        return self.result

    def __str__(self):
        return 'future name: %s, result: %s, id: %s' % (self.name, self.result, id(self))




class Task:
    def __init__(self, coro):
        print('init task')
        self.coro = coro
        print('****** init future ******')
        f = Future('init')
        f.set_result(None)
        print(f)
        self.step(f)

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


def connect(sock, address):
    sock.setblocking(False)
    try:
        sock.connect(address)
    except BlockingIOError:
        pass
    f = Future('connect')
    def on_connected():
        print('on connected callback')
        f.set_result(None)

    selector.register(sock.fileno(), EVENT_WRITE, on_connected)
    yield from f
    selector.unregister(sock.fileno())


def read(sock):
    f = Future('read')
    def on_readable():
        print('on read callback')
        f.set_result(sock.recv(1024))  # Read 4k at a time.

    selector.register(sock.fileno(), EVENT_READ, on_readable)
    chunk = yield from f
    selector.unregister(sock.fileno())
    return chunk


def read_all(sock):
    response = []
    chunk = yield from read(sock)
    while chunk:
        response.append(chunk)
        chunk = yield from read(sock)

    return b''.join(response)


class Fetcher:
    def __init__(self, url):
        self.response = b''
        self.url = url

    def fetch(self):
        global concurrency_achieved, stopped
        concurrency_achieved = max(concurrency_achieved, len(urls_todo))

        sock = socket.socket()
        yield from connect(sock, ('xkcd.com', 80))

        get = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(self.url)
        print(get)
        sock.send(get.encode('ascii'))
        self.response = yield from read_all(sock)
        self._process_response()
        urls_todo.remove(self.url)
        if not urls_todo:
            stopped = True
        print(self.url)

    def _process_response(self):
        if not self.response:
            print('error: {}'.format(self.url))
            return
        # if not self._is_html():
        #     return
        urls = set(re.findall(r'''(?i)href=["']?([^\s"'<>]+)''', self.body()))
        urls = ['/353/']
        print(urls)
        for url in urls:
            normalized = urllib.parse.urljoin(self.url, url)
            parts = urllib.parse.urlparse(normalized)
            if parts.scheme not in ('', 'http', 'https'):
                continue
            host, port = urllib.parse.splitport(parts.netloc)
            if host and host.lower() not in ('xkcd.com', 'www.xkcd.com'):
                continue
            defragmented, frag = urllib.parse.urldefrag(parts.path)
            if defragmented not in urls_seen:
                urls_todo.add(defragmented)
                urls_seen.add(defragmented)
                Task(Fetcher(defragmented).fetch())

    def body(self):
        body = self.response.split(b'\r\n\r\n', 1)[1]
        return body.decode('utf-8')

    def _is_html(self):
        head, body = self.response.split(b'\r\n\r\n', 1)
        headers = dict(h.split(': ') for h in head.decode().split('\r\n')[1:])
        return headers.get('Content-Type', '').startswith('text/html')


start = time.time()
fetcher = Fetcher('/')
Task(fetcher.fetch())

while not stopped:
    print('********* start select *********')
    events = selector.select()
    for event_key, event_mask in events:
        callback = event_key.data
        callback()

print('{} URLs fetched in {:.1f} seconds, achieved concurrency = {}'.format(
    len(urls_seen), time.time() - start, concurrency_achieved))


"""
init task
****** init future ******
set future result: None
future name: init, result: None, id: 4349341936
step start
old future: future name: init, result: None, id: 4349341936
__iter__
new future: future name: connect, result: None, id: 4349341992
step end
********* start select *********
on connected callback
set future result: None
step start
old future: future name: connect, result: None, id: 4349341992
GET / HTTP/1.0
Host: xkcd.com


__iter__
new future: future name: read, result: None, id: 4349342888
step end
********* start select *********
on read callback
set future result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 09:05:21 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19929-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583658322.759161,VS0,VE0\r\n\r\n'
step start
old future: future name: read, result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 09:05:21 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19929-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583658322.759161,VS0,VE0\r\n\r\n', id: 4349342888
__iter__
new future: future name: read, result: None, id: 4349341992
step end
********* start select *********
on read callback
set future result: b''
step start
old future: future name: read, result: b'', id: 4349341992
['/353/']
init task
****** init future ******
set future result: None
future name: init, result: None, id: 4349344400
step start
old future: future name: init, result: None, id: 4349344400
__iter__
new future: future name: connect, result: None, id: 4349344232
step end
/
********* start select *********
on connected callback
set future result: None
step start
old future: future name: connect, result: None, id: 4349344232
GET /353/ HTTP/1.0
Host: xkcd.com


__iter__
new future: future name: read, result: None, id: 4349341992
step end
********* start select *********
on read callback
set future result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/353/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 09:05:21 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19945-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583658322.885927,VS0,VE0\r\n\r\n'
step start
old future: future name: read, result: b'HTTP/1.1 301 Moved Permanently\r\nServer: Varnish\r\nRetry-After: 0\r\nLocation: https://xkcd.com/353/\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nDate: Sun, 08 Mar 2020 09:05:21 GMT\r\nVia: 1.1 varnish\r\nConnection: close\r\nX-Served-By: cache-tyo19945-TYO\r\nX-Cache: HIT\r\nX-Cache-Hits: 0\r\nX-Timer: S1583658322.885927,VS0,VE0\r\n\r\n', id: 4349341992
__iter__
new future: future name: read, result: None, id: 4349344232
step end
********* start select *********
on read callback
set future result: b''
step start
old future: future name: read, result: b'', id: 4349344232
['/353/']
/353/
2 URLs fetched in 0.3 seconds, achieved concurrency = 2

"""