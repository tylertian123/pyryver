import setuptools
import pyryver

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    install_requires = fh.read().splitlines()

setuptools.setup(
    name="pyryver",
    version=pyryver.__version__,
    author="Tyler Tian",
    author_email="tylertian123@gmail.com",
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
