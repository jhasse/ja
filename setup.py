from setuptools import setup

VERSION='1.1.0' # also see __init__.py

setup(
    name='ja',
    version=VERSION,
    author="Jan Niklas Hasse",
    author_email="jhasse@bixense.com",
    url="https://bixense.com/ja",
    download_url='https://github.com/jhasse/ja/archive/v{}.tar.gz'.format(VERSION),
    description="Frontend for Ninja focusing on a faster edit, compile, debug cycle",
    packages=['ja'],
    package_data={'': ['*.pb']},
    entry_points={
        'console_scripts': ['ja = ja:main'],
    },
    install_requires=[
        'humanize',
        'click',
        'protobuf',
    ],
)
