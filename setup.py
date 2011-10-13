import os
from setuptools import setup

setup(
    name = "django-drapes",
    version = "0.1",
    author = "Afrois Alreadyinu",
    author_email = "afroisalreadyinu@gmail.com",
    description = ("SOme decorators and classes to make working with django projects easier."),
    install_requires = ['formencode',
                        'decorator',
                        'django',
                        'coverage',
                        'nose',
                        'mock'],
    py_modules=['django_drapes'],
)
