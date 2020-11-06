from flask import Flask, request
from flask import Response
import requests
import os
import mimetypes
import hashlib
from time import time

pypi_upstream = 'https://pypi.python.org/simple/'
files_upstream = 'https://files.pythonhosted.org/'
cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
cache_days = 7

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
            with open(cache_file, 'rb') as f:
                return Response(f.read(), mimetype=mimetype)
    upstream = pypi_upstream + path + '?' + request.query_string.decode('utf8')
    print('Fetching upstream %s' % upstream)
    r = requests.get(upstream)
    with open(cache_file, 'wb') as f:
        f.write(r.content)
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
    with open(cache_file, 'wb') as f:
        f.write(r.content)
    return Response(r.content, mimetype=r.headers.get('Content-Type'))


if __name__ == '__main__':
    app.run('0.0.0.0', 5000)
