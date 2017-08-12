import os.path
import contextlib
import subprocess
import socket
import time

import pytest


__all__ = ('NginxProcess', 'nginx_proc')

NGINX_DEFAULT_CONFIG_TEMPLATE = """\
# nginx has to start in foreground, otherwise pytest-nginx won't be able to kill it
daemon off;
pid %TMPDIR%/nginx.pid;
error_log %TMPDIR%/error.log;
worker_processes auto;
worker_cpu_affinity auto;

events {
    worker_connections  1024;
}

http {
    default_type  application/octet-stream;
    access_log off;
    sendfile on;
    aio threads;
    charset utf-8;

    server {
        listen       %PORT%;
        server_name  %HOST%;
        index  index.html index.htm;
        location / {
            root "%SERVER_ROOT%";
        }
    }
}
"""

def get_config(request):
    """Return a dictionary with config options."""
    config = {}
    options = [
        'exec', 'start_params', 'host', 'port', 'config_template',
    ]
    for option in options:
        option_name = 'nginx_' + option
        conf = request.config.getoption(option_name) or \
            request.config.getini(option_name)
        config[option] = conf
    return config

def init_nginx_directory(tmpdir, template_path, host, port, server_root):
    """
    Initialize temporary directory for nginx.

    :param str tmpdir: temporary directory to initialize
    :param str host: nginx host
    :param str port: TCP port
    :returns: path of the temporary nginx config
    """
    def format_config(config, **kwargs):
        for key, value in kwargs.items():
            config = config.replace("%" + key.upper() + "%", str(value))
        return config
    if template_path:
        config_template = open(template_path).read()
    else:
        config_template = NGINX_DEFAULT_CONFIG_TEMPLATE
    config = format_config(config_template,
                           tmpdir=tmpdir,
                           host=host,
                           port=port,
                           server_root=server_root)
    config_path = os.path.join(tmpdir, "nginx.conf")
    f = open(config_path, "w")
    f.write(config)
    return config_path

@contextlib.contextmanager
def daemon(cmd, **popen_args):
    with subprocess.Popen(cmd, **popen_args) as proc:
        # make sure that the process did not fail right away
        code = proc.poll()
        if code is not None and code != 0:
            raise Exception("Command '{}' exited with non-zero return code: {}".format(cmd, code))

        # yield the process to the caller
        yield proc

        # stop the daemon
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except TimeoutError:
            proc.kill()

        # check errors
        code = proc.poll()
        if code != 0:
            raise Exception("Command '{}' exited with non-zero return code: {}".format(cmd, code))

class NginxProcess:
    def __init__(self, proc, host, port, server_root):
        self._proc = proc
        self.host = host
        self.port = port
        self.server_root = server_root

def get_random_port(host=""):
    s = socket.socket()
    with contextlib.closing(s):
        s.bind((host, 0))
        return s.getsockname()[1]

def wait_for_socket(host, port, timeout=10, timeout_inner=0.1):
    def check():
        s = socket.socket()
        with contextlib.closing(s):
            try:
                s.connect((host, port))
                return True
            except (socket.error, socket.timeout):
                return False
    slept = 0
    while slept < timeout and not check():
        time.sleep(timeout_inner)
    if slept == timeout:
        raise TimeoutError("Could not bind to socket ({}, {}).".format(host, port))

def nginx_proc(server_root_fixture_name, executable=None, start_params=None,
               host=None, port=None, config_template=None):
    """
    Nginx process factory.

    :param str executable: path to nginx
    :param str start_params: additional parameters passed to nginx
    :param str host: host name to listen on
    :param int port: port number to listen on
    :param str server_root: path to the directory to be served by nginx
    :param str config_template: path to the template nginx configuration file
    :rtype: func
    :returns: function which makes a nginx process
    """
    @pytest.fixture(scope='session')
    def nginx_proc_fixture(request, tmpdir_factory):
        """
        Process fixture for nginx.

        :param FixtureRequest request: fixture request object
        :rtype: mirakuru.HTTPExecutor
        :returns: HTTP executor
        """
        nonlocal executable, start_params, host, port, config_template

        server_root = request.getfixturevalue(server_root_fixture_name)
        config = get_config(request)

        executable = executable or config['exec']
        start_params = start_params or config['start_params']
        host = host or config['host']
        port = port or config['port']
        if not port:
            port = get_random_port(port)
        config_template = config_template or config['config_template']

        if not os.path.isdir(server_root):
            raise ValueError("Specified server root ('{}') is not an existing directory.".format(server_root))
        if config_template and not os.path.isfile(config_template):
            raise ValueError("Specified config template ('{}') is not an existing file.".format(config_template))

        tmpdir = tmpdir_factory.mktemp("nginx-data")
        config_path = init_nginx_directory(tmpdir, config_template, host, port, server_root)

        cmd = "{} -c {} {}".format(executable, config_path, start_params)
        with daemon(cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                ) as proc:
            wait_for_socket(host, port)
            yield NginxProcess(proc, host, port, server_root)

    return nginx_proc_fixture
