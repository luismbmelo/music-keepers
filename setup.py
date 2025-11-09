"""Setup file for Music Keepers."""

from setuptools import setup, find_packages

setup(
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
