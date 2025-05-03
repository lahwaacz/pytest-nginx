import os.path
import contextlib
import subprocess
import socket
import time
import pwd

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

NGINX_DEFAULT_PHP_CONFIG_TEMPLATE = """\
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
        index  index.php;
        root "%SERVER_ROOT%";

        location ~ \.php$ {
            try_files $uri $document_root$fastcgi_script_name =404;
            fastcgi_pass unix:%PHP_FPM_SOCKET%;
            fastcgi_index index.php;

            fastcgi_param  SCRIPT_FILENAME    $document_root$fastcgi_script_name;
            fastcgi_param  QUERY_STRING       $query_string;
            fastcgi_param  REQUEST_METHOD     $request_method;
            fastcgi_param  CONTENT_TYPE       $content_type;
            fastcgi_param  CONTENT_LENGTH     $content_length;

            fastcgi_param  SCRIPT_NAME        $fastcgi_script_name;
            fastcgi_param  REQUEST_URI        $request_uri;
            fastcgi_param  DOCUMENT_URI       $document_uri;
            fastcgi_param  DOCUMENT_ROOT      $document_root;
            fastcgi_param  SERVER_PROTOCOL    $server_protocol;
            fastcgi_param  REQUEST_SCHEME     $scheme;
            fastcgi_param  HTTPS              $https if_not_empty;

            fastcgi_param  GATEWAY_INTERFACE  CGI/1.1;
            fastcgi_param  SERVER_SOFTWARE    nginx/$nginx_version;

            fastcgi_param  REMOTE_ADDR        $remote_addr;
            fastcgi_param  REMOTE_PORT        $remote_port;
            fastcgi_param  SERVER_ADDR        $server_addr;
            fastcgi_param  SERVER_PORT        $server_port;
            fastcgi_param  SERVER_NAME        $server_name;

            # PHP only, required if PHP was built with --enable-force-cgi-redirect
            fastcgi_param  REDIRECT_STATUS    200;
        }
    }
}
"""

PHP_FPM_DEFAULT_CONFIG_TEMPLATE = """\
[global]
error_log = %PHP_FPM_ERROR_LOG%

[www]
user = %PHP_FPM_USER%

listen = %PHP_FPM_SOCKET%

pm = dynamic
pm.max_children = 5
pm.min_spare_servers = 1
pm.max_spare_servers = 3
"""

def format_config(config, **kwargs):
    for key, value in kwargs.items():
        config = config.replace("%" + key.upper() + "%", str(value))
    return config

def init_nginx(tmpdir, template_path, host, port, server_root, php_fpm_socket=None):
    """
    Initialize data for nginx.

    :returns: path of the temporary nginx config
    """
    if template_path:
        config_template = open(template_path).read()
    elif php_fpm_socket:
        config_template = NGINX_DEFAULT_PHP_CONFIG_TEMPLATE
    else:
        config_template = NGINX_DEFAULT_CONFIG_TEMPLATE
    config = format_config(config_template,
                           tmpdir=tmpdir,
                           host=host,
                           port=port,
                           server_root=server_root)
    if php_fpm_socket:
        config = format_config(config, php_fpm_socket=php_fpm_socket)
    config_path = os.path.join(tmpdir, "nginx.conf")
    f = open(config_path, "w")
    f.write(config)
    return config_path

def init_php_fpm(tmpdir, template_path):
    """
    Initialize data for php-fpm.

    :returns: path of the php-fpm config, and path to the php-fpm socket
    """
    if template_path:
        config_template = open(template_path).read()
    else:
        config_template = PHP_FPM_DEFAULT_CONFIG_TEMPLATE
    user = get_username()
    socket = os.path.join(tmpdir, "php-fpm.socket")
    config = format_config(config_template,
                           php_fpm_error_log=os.path.join(tmpdir, "php-fpm-error.log"),
                           php_fpm_user=user,
                           php_fpm_socket=socket)
    config_path = os.path.join(tmpdir, "php-fpm.conf")
    f = open(config_path, "w")
    f.write(config)
    return config_path, socket

@contextlib.contextmanager
def daemon(cmd, **popen_args):
    with subprocess.Popen(cmd, **popen_args) as proc:
        # make sure that the process did not fail right away
        code = proc.poll()
        if code is not None and code != 0:
            raise subprocess.CalledProcessError(returncode=code, cmd=cmd, output=proc.stdout, stderr=proc.stderr)

        try:
            # yield the process to the caller
            yield proc

        finally:
            # stop the daemon
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except TimeoutError:
                proc.kill()

            # check errors
            code = proc.poll()
            if code != 0:
                raise subprocess.CalledProcessError(returncode=code, cmd=cmd, output=proc.stdout, stderr=proc.stderr)

class NginxProcess:
    def __init__(self, host, port, server_root):
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

def get_username():
    """Return the user name of the current process."""
    return pwd.getpwuid(os.getuid()).pw_name


def nginx_proc(server_root_fixture_name, host=None, port=None,
               nginx_exec=None, nginx_params=None, config_template=None):
    """
    Nginx process factory.

    :param str nginx_exec: path to the nginx executable
    :param str nginx_params: additional parameters passed to nginx
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
        nonlocal host, port, nginx_exec, nginx_params, config_template

        server_root = request.getfixturevalue(server_root_fixture_name)

        def get_option(option_name):
            return request.config.getoption(option_name) or request.config.getini(option_name)

        host = host or get_option('nginx_host')
        port = port or get_option('nginx_port')
        if not port:
            port = get_random_port(host)
        nginx_exec = nginx_exec or get_option('nginx_exec')
        nginx_params = nginx_params or get_option('nginx_params')
        config_template = config_template or get_option('nginx_config_template')

        if not os.path.isdir(server_root):
            raise ValueError("Specified server root ('{}') is not an existing directory.".format(server_root))
        if config_template and not os.path.isfile(config_template):
            raise ValueError("Specified config template ('{}') is not an existing file.".format(config_template))

        tmpdir = tmpdir_factory.mktemp("nginx-data")
        config_path = init_nginx(tmpdir, config_template, host, port, server_root)

        cmd = "{} -c {} {}".format(nginx_exec, config_path, nginx_params)
        with daemon(cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                ) as proc:
            wait_for_socket(host, port)
            yield NginxProcess(host, port, server_root)

    return nginx_proc_fixture

def nginx_php_proc(server_root_fixture_name, host=None, port=None,
                   nginx_exec=None, nginx_params=None, nginx_config_template=None,
                   php_fpm_exec=None, php_fpm_params=None, php_fpm_config_template=None):
    """
    Factory for the nginx and php-fpm processes.

    :param str nginx_exec: path to the nginx executable
    :param str nginx_params: additional parameters passed to nginx
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
        nonlocal host, port, nginx_exec, nginx_params, nginx_config_template, php_fpm_exec, php_fpm_params, php_fpm_config_template

        server_root = request.getfixturevalue(server_root_fixture_name)

        def get_option(option_name):
            return request.config.getoption(option_name) or request.config.getini(option_name)

        host = host or get_option('nginx_host')
        port = port or get_option('nginx_port')
        if not port:
            port = get_random_port(host)
        nginx_exec = nginx_exec or get_option('nginx_exec')
        php_fpm_exec = php_fpm_exec or get_option('php_fpm_exec')
        nginx_params = nginx_params or get_option('nginx_params')
        php_fpm_params = php_fpm_params or get_option('php_fpm_params')
        nginx_config_template = nginx_config_template or get_option('nginx_config_template')
        php_fpm_config_template = php_fpm_config_template or get_option('php_fpm_config_template')

        if not os.path.isdir(server_root):
            raise ValueError("Specified server root ('{}') is not an existing directory.".format(server_root))
        if nginx_config_template and not os.path.isfile(nginx_config_template):
            raise ValueError("Specified config template ('{}') is not an existing file.".format(nginx_config_template))
        if php_fpm_config_template and not os.path.isfile(php_fpm_config_template):
            raise ValueError("Specified config template ('{}') is not an existing file.".format(php_fpm_config_template))

        tmpdir = tmpdir_factory.mktemp("nginx-php-fpm-data")
        php_fpm_config_path, php_fpm_socket_path = init_php_fpm(tmpdir, php_fpm_config_template)
        nginx_config_path = init_nginx(tmpdir, nginx_config_template, host, port, server_root, php_fpm_socket_path)

        nginx_cmd = "{} -c {} {}".format(nginx_exec, nginx_config_path, nginx_params)
        php_fpm_cmd = "{} --nodaemonize --fpm-config {} {}".format(php_fpm_exec, php_fpm_config_path, php_fpm_params)
        with daemon(php_fpm_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                ) as php_fpm_proc:
            with daemon(nginx_cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                    ) as nginx_proc:
                wait_for_socket(host, port)
                yield NginxProcess(host, port, server_root)

    return nginx_proc_fixture
