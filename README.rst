Pypi Caching Proxy
===================

Setup a proxy that caches PyPI download files. Set this as your PyPI Index URL,
and it will serve PyPI's ``/simple`` and serve+cache files from ``files.pythonhosted.org``.

Usage
------

Installation steps::

  virtualenv venv
  ./venv/bin/pip install -r requirements.txt

You can start up the proxy by executing ``app.py``, or you can serve using WSGI
server as it is a simple Flask app::

  ./venv/bin/python app.py

To install package from this cache, you can use ``-i`` option::

  pip install -i http://localhost:5000/simple

Or you can `override your default pypi URL
<https://pip.pypa.io/en/stable/user_guide/#config-file>`_.

Known Issue 
------------

Help appreciated

* Large packages might timeout because download is not streamed directly but
  rather downloaded into cache first. 
* No checksum validation of cache download. Downloaded cache might be
  corrupted. 
