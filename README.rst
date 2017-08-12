pytest-nginx
============

pytest-nginx is a pytest plugin, that allows you to test code, which requires
communicating with a web server. Custom fixtures can be made which manage the
content of the server root directory.

How to use
==========

The plugin contains one fixture:

* **nginx_proc** - session scoped fixture, which manages the nginx daemon with
  the most basic configuration for serving static files.

All fixtures take the name of a fixture managing the server root directory. In
the simplest case it is an empty temporary directory managed with the
``tmpdir_factory`` built-in fixture:

.. code-block:: python

    from pytest_nginx import factories
    
    @pytest.fixture(scope="session")
    def nginx_server_root(tmpdir_factory):
        return tmpdir_factory.mktemp("nginx-server-root")
    
    nginx_proc = factories.nginx_proc("nginx_server_root")

To manage the served content, you can create additional module or
function-scoped fixtures on top of ``nginx_proc``:

.. code-block:: python

    @pytest.fixture(scope="module")
    def nginx_hello_world(nginx_proc):
        f = open(os.path.join(nginx_proc.server_root, "index.html"), "w")
        f.write("Hello world! This is pytest-nginx serving on host {}, port {}."
                .format(nginx_proc.host, nginx_proc.port))
        f.close()
        return nginx_proc

Configuration
=============

You can define your settings in three ways: with fixture factory arguments,
with command line options and with ``pytest.ini`` configuration options. These
settings are handled in the following order:

1. Fixture factory arguments
2. Command line options
3. ``pytest.ini`` configuration options

+---------------------------+---------------------------+---------------------------+---------------------------+
| Fixture factory argument  | Command line option       | pytest.ini option         | Default                   |
+===========================+===========================+===========================+===========================+
| executable                | --nginx-exec              | nginx_exec                | nginx                     |
+---------------------------+---------------------------+---------------------------+---------------------------+
| start_params              | --nginx-start-params      | nginx_start_params        | ""                        |
+---------------------------+---------------------------+---------------------------+---------------------------+
| host                      | --nginx-host              | nginx_host                | 127.0.0.1                 |
+---------------------------+---------------------------+---------------------------+---------------------------+
| port                      | --nginx-port              | nginx_port                | random                    |
+---------------------------+---------------------------+---------------------------+---------------------------+
| config_template           | --nginx-config-template   | nginx_config_template     | auto-generated            |
+---------------------------+---------------------------+---------------------------+---------------------------+

Examples showing how to specify the port number:

* Pass it as an argument to the factory function:

    .. code-block:: python

        nginx_proc = factories.nginx_proc(port=8888)

* Use the ``--nginx-port`` command line option when running pytest:

    .. code-block::

        pytest ./tests --nginx-port=8888


* Add the ``nginx_port`` option to the ``pytest.ini`` file:

    .. code-block:: ini

        [pytest]
        nginx_port = 8888
