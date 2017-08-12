from pytest_nginx import factories


_help_executable = 'Path to nginx executable'
_help_start_params = "Additional parameters passed to nginx"
_help_host = 'Host at which nginx will accept connections'
_help_port = 'Port at which nginx will accept connections'
_help_config_template = 'Path to the template nginx configuration file'


def pytest_addoption(parser):
    """Configure options for pytest-nginx."""
    parser.addini(
        name='nginx_exec',
        help=_help_executable,
        default='nginx'
    )

    parser.addini(
        name='nginx_start_params',
        help=_help_start_params,
        default=''
    )

    parser.addini(
        name='nginx_host',
        help=_help_host,
        default='127.0.0.1'
    )

    parser.addini(
        name='nginx_port',
        help=_help_port,
        default=None,
    )

    parser.addini(
        name='nginx_config_template',
        help=_help_config_template,
        default=None
    )

    parser.addoption(
        '--nginx-exec',
        action='store',
        metavar='path',
        dest='nginx_exec',
        help=_help_executable
    )

    parser.addoption(
        '--nginx-start-params',
        action='store',
        dest='nginx_start_params',
        help=_help_start_params
    )

    parser.addoption(
        '--nginx-host',
        action='store',
        dest='nginx_host',
        help=_help_host,
    )

    parser.addoption(
        '--nginx-port',
        action='store',
        dest='nginx_port',
        help=_help_port
    )

    parser.addoption(
        '--nginx-config-template',
        action='store',
        dest='nginx_config_template',
        help=_help_config_template
    )


# TODO: we'd have to pass server_root fixture here
#nginx_proc = factories.nginx_proc()
