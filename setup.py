#!/usr/bin/env python
from distutils.core import setup

setup(name='Liszt',
      version='1.0',
      description='A web-backed todo list and note-taking application',
      author='Karim Hamidou',
      author_email='khamidou@gmail.com',
      url='http://todoliszt.com/',
      packages=['libliszt'],
      scripts=['liszt', 'liszt-daemon', 'liszt-setup']
      data_file=[('', 'README'), ('', 'EXAMPLES')]
     )
