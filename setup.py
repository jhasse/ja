from setuptools import setup

setup(
    name='ja',
    version='1.0.0',
    author="Jan Niklas Hasse",
    author_email="jhasse@bixense.com",
    url="https://bixense.com/ja",
    download_url='https://github.com/jhasse/ja/archive/v1.0.0.tar.gz',
    description="Frontend for Ninja focusing on a faster edit, compile, debug cycle",
    packages=['ja'],
    package_data={'': ['*.pb']},
    entry_points={
        'console_scripts': ['ja = ja:main'],
    },
)
