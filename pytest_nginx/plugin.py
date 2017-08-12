from pytest_nginx import factories


_help = {
    "nginx_host":               "Host at which nginx will accept connections",
    "nginx_port":               "Port at which nginx will accept connections",
    "nginx_exec":               "Path to nginx executable",
    "nginx_params":             "Additional parameters passed to nginx",
    "nginx_config_template":    "Path to the template nginx configuration file",
    "php_fpm_exec":             "Path to php-fpm executable",
    "php_fpm_params":           "Additional parameters passed to php-fpm",
    "php_fpm_config_template":  "Path to the template nginx configuration file used along with php-fpm",
}

_defaults = {
    "nginx_host":               "127.0.0.1",
    "nginx_port":               None,
    "nginx_exec":               "nginx",
    "nginx_params":             "",
    "nginx_config_template":    None,
    "php_fpm_exec":             "php-fpm",
    "php_fpm_params":           "",
    "php_fpm_config_template":  None,
}

def _add_option(parser, option):
    parser.addini(
        name=option,
        help=_help[option],
        default=_defaults[option]
    )
    parser.addoption(
        "--" + option.replace("_", "-"),
        action="store",
        dest=option,
        help=_help[option]
    )

def pytest_addoption(parser):
    """Configure options for pytest-nginx."""
    for option in ["nginx_host", "nginx_port",
                   "nginx_exec", "nginx_params", "nginx_config_template",
                   "php_fpm_exec", "php_fpm_params", "php_fpm_config_template"]:
        _add_option(parser, option)

# TODO: we'd have to pass server_root fixture here
#nginx_proc = factories.nginx_proc()
