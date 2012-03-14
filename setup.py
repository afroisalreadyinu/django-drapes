import os
from setuptools import setup

with open('readme.rst') as file:
    long_description = file.read()

setup(
    name = "django-drapes",
    version = "0.1",
    author = "Ulas Tuerkmen",
    author_email = "afroisalreadyinu@gmail.com",
    description = ("Some decorators and classes to make working with django projects easier."),
    long_description=long_description,
    install_requires = ['formencode',
                        'decorator',
                        'django',
                        'coverage',
                        'nose',
                        'mock'],
    py_modules=['django_drapes'],
)
