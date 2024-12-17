# ja [![PyPI version](https://badge.fury.io/py/ja.svg)](https://badge.fury.io/py/ja)

Frontend for [Ninja](https://ninja-build.org) focusing on a faster edit, compile, debug cycle.
[Learn more...](docs/index.md)

## Install From Git

```
pip install --user --force .
```

# How to Upload a New Release

```
pip install setuptools twine
python setup.py sdist
python -m twine upload dist/ja-*.tar.gz
```
