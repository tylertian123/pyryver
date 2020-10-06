import importlib
import os
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    install_requires = fh.read().splitlines()


def get_lib_ver():
    """
    Magical function that loads the version from pyryver/version.py.

    Credits to @mincrmatt12.
    """
    spec = importlib.util.spec_from_file_location("pyryver.version", os.path.join(os.path.dirname(__file__), "pyryver/version.py"))
    version = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version)
    return version.__version__


setuptools.setup(
    name="pyryver",
    version=get_lib_ver(),
    author="Tyler Tian, Matthew Mirvish",
    author_email="tylertian123@gmail.com, matthew@mm12.xyz",
    description="An unofficial async Python library for Ryver.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tylertian123/pyryver",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
    ],
    install_requires=install_requires,
    python_requires=">=3.6",
    keywords="ryver"
)
