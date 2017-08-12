import os
import requests
import pytest

from pytest_nginx import factories

@pytest.fixture(scope="session")
def nginx_server_root(tmpdir_factory):
    return tmpdir_factory.mktemp("nginx-server-root")

nginx_proc = factories.nginx_proc("nginx_server_root")

@pytest.fixture(scope="module")
def nginx_hello_world(nginx_proc):
    f = open(os.path.join(nginx_proc.server_root, "index.html"), "w")
    f.write("Hello world! This is pytest-nginx.")
    f.close()
    return nginx_proc

def test_hello_world(nginx_hello_world):
    url = "http://{}:{}".format(nginx_hello_world.host, nginx_hello_world.port)
    response = requests.get(url)
    assert response.status_code == 200
    assert response.text == "Hello world! This is pytest-nginx."


nginx_php_proc = factories.nginx_php_proc("nginx_server_root")

@pytest.fixture(scope="module")
def nginx_php_hello_world(nginx_php_proc):
    f = open(os.path.join(nginx_php_proc.server_root, "index.php"), "w")
    f.write("<?php\nprint('Hello world! This is pytest-nginx, serving PHP!')\n?>")
    f.close()
    return nginx_php_proc

def test_php_hello_world(nginx_php_hello_world):
    url = "http://{}:{}".format(nginx_php_hello_world.host, nginx_php_hello_world.port)
    response = requests.get(url)
    assert response.status_code == 200
    assert response.text == "Hello world! This is pytest-nginx, serving PHP!"
