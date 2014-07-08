#!/usr/bin/env python3

from setuptools import setup, find_packages


def get_readme():
    with open("README.md") as f:
        return f.read()


setup(name="OlympianAdmin",
      version="0.1",
      description="Administration System for Counter-Strike: Source Servers",
      long_description=get_readme(),
      author="Adam Cunnington",
      author_email="ac@adamcunnington.info",
      license="GPLv3",
      classifiers=[
          "Development Status :: 2 - Pre-Alpha",
          "Environment :: Other Environment",
          "Intended Audience :: Other Audience",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "Natural Language :: English",
          "Operating System :: OS Independent",
          "Programming Language :: Python :: 2.5",
          "Topic :: Games/Entertainment :: First Person Shooters"],
      keywords=("css counter-strike 'counter-strike: source', server "
                "administration"),
      packages=find_packages(exclude=(".git", )))
