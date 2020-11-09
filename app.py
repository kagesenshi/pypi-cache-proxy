from flask import Flask, request
from flask import Response
import requests
import os
import mimetypes
import hashlib
from time import time
import multiprocessing
import gunicorn.app.base
import argparse
import zc.lockfile as lockfile

pypi_upstream = 'https://pypi.python.org/simple/'
files_upstream = 'https://files.pythonhosted.org/'

cache_dir = os.environ.get('PYPI_CACHE_DIR', 
        os.path.join(os.path.dirname(__file__), 'cache'))

cache_days = int(os.environ.get('PYPI_CACHE_DAYS', 7))

app = Flask('PyPI Caching Proxy')

def rewrite_response(text):
    root = request.url_root
    return text.replace(files_upstream, root + 'files/')

@app.route('/simple', defaults={'path': ''}, methods=['GET'])
@app.route('/simple/<path:path>', methods=['GET'])
def get_pypi(path):
    cache_file = os.path.join(cache_dir, '.pypicache', hashlib.md5(path.encode('utf8')).hexdigest())
    item_dir = os.path.dirname(cache_file)
    if not os.path.exists(item_dir):
        os.makedirs(item_dir)

    if os.path.exists(cache_file):
        st = os.stat(cache_file)
        if (time() - st.st_mtime) < (cache_days*24*60*60):
            mimetype = 'text/html'
            print('Fetching from cache %s' % cache_file)
            with open(cache_file, 'r') as f:
                return Response(rewrite_response(f.read()), mimetype=mimetype)
    upstream = pypi_upstream + path + '?' + request.query_string.decode('utf8')
    print('Fetching upstream %s' % upstream)
    r = requests.get(upstream)

    try:
        lock = lockfile.LockFile(cache_file + '.lock')
        with open(cache_file + '.tmp', 'wb') as f:
            f.write(r.content)
        os.rename(cache_file + '.tmp', cache_file)
        lock.close()
    except lockfile.LockError:
        pass

    return Response(rewrite_response(r.text), mimetype=r.headers.get('Content-Type'))


@app.route('/files', defaults={'path': ''}, methods=['GET'])
@app.route('/files/<path:path>', methods=['GET'])
def get_files(path):
    cache_file = os.path.join(cache_dir, path)
    item_dir = os.path.dirname(cache_file)
    if not os.path.exists(item_dir):
        os.makedirs(item_dir)
    if os.path.exists(cache_file):
        mimetype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        print('Fetching from cache %s' % cache_file)
        with open(cache_file, 'rb') as f:
            return Response(f.read(), mimetype=mimetype)
    upstream = files_upstream + path + '?' + request.query_string.decode('utf8')
    print('Fetching upstream %s' % upstream)
    r = requests.get(upstream)
    try:
        lock = lockfile.LockFile(cache_file + '.lock')
        with open(cache_file + '.tmp', 'wb') as f:
            f.write(r.content)
        os.rename(cache_file + '.tmp', cache_file)
        lock.close()
    except lockfile.LockError:
        pass
    return Response(r.content, mimetype=r.headers.get('Content-Type'))


def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1

class Application(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start PyPI Cache Proxy')
    parser.add_argument('-l', '--host', help='Listening host',
            default='0.0.0.0')
    parser.add_argument('-p', '--port', help='Listening port', default=5000,
            type=int)
    parser.add_argument('-w', '--workers', help='Gunicorn workers',
            default=number_of_workers(), type=int)

    args = parser.parse_args()

    options = {
        'bind': '%s:%s' % (args.host, args.port),
        'workers': args.workers,
    }
    Application(app, options).run()
