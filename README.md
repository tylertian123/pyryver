# pyryver
![Python 3](https://img.shields.io/pypi/pyversions/pyryver)
[![MIT License](https://img.shields.io/pypi/l/pyryver)](https://github.com/tylertian123/pyryver/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/pyryver)](https://pypi.org/project/pyryver/)
[![Read the Docs (latest)](https://img.shields.io/readthedocs/pyryver)](https://pyryver.readthedocs.io/en/latest/)
[![Read the Docs (stable)](https://img.shields.io/readthedocs/pyryver/stable?label=docs%20%28stable%29)](https://pyryver.readthedocs.io/en/stable/)

`pyryver` is an unofficial async Python library for Ryver.
It provides a simple and sane way of automating tasks on Ryver and building bots, without the need to set up Hubot or Botkit.

Note that since it is still in major version 0, the API may change any time. 
However, we will attempt to make it as backwards-compatible as possible (excluding version 0.1.0).

Version 0.3.0 is currently in alpha.

Special thanks to [@mincrmatt12](https://github.com/mincrmatt12)!

## Installation
`pyryver` is now on PyPI! You can install it with `python3 -m pip install --user pyryver`.
You can also find pre-releases on [TestPyPI](https://test.pypi.org/project/pyryver/).
More instructions can be found at [Read the Docs](https://pyryver.readthedocs.io/en/latest/index.html).

`pyryver` requires Python >= 3.6 and the `aiohttp` library. 

## Supported Actions
`pyryver` has near complete support for every common Ryver action. 
This includes things like sending messages, uploading files, managing topics & tasks, creating forums/teams, etc.

`pyryver` currently does not support editing user and organization settings. 
Forum/team settings, however, are supported.

For a complete list of everything the API contains, head over to [the docs](https://pyryver.readthedocs.io/en/latest/index.html).
If there's something missing from the API that you'd like to see, create an issue and we'll get to it ASAP.

## Documentation and Examples
Documentation and examples can be found on [Read the Docs](https://pyryver.readthedocs.io).

If you want to see an example of `pyryver` being used in a real project, check out [LaTeX Bot](https://github.com/tylertian123/ryver-latexbot).
