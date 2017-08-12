from setuptools import setup, find_packages

requirements = [
    'pytest>=3.0.0',
]

test_requires = [
    'requests',
]

setup_requires = [
    'setuptools',
    'pip'
]


setup(
    name='pytest-nginx',
    version='1.1',
    description='nginx fixture for pytest',
    long_description=(open('README.rst').read()),
    keywords='tests py.test pytest fixture nginx',
    author='Jakub Klinkovský',
    author_email='lahwaacz@users.noreply.github.com',
    url='https://github.com/lahwaacz/pytest-nginx',
    license='GPLv3',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: '
        'GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages(exclude=["tests"]),
    install_requires=requirements,
    tests_require=test_requires,
    setup_requires=setup_requires,
    test_suite='tests',
    entry_points={
        'pytest11': [
            'pytest_nginx = pytest_nginx.plugin'
        ]},
    include_package_data=True,
    zip_safe=False,
)
