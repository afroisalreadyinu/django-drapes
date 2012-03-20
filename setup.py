import os
from setuptools import setup

DESC = "Some decorators and classes to make working with django projects easier."

try:
    with open('readme.rst') as file:
        long_description = file.read()
except IOError:
    long_description = DESC

setup(
    name = "django-drapes",
    version = "0.1.1",
    author = "Ulas Tuerkmen",
    author_email = "afroisalreadyinu@gmail.com",
    description = DESC,
    long_description=long_description,
    install_requires = ['formencode',
                        'decorator',
                        'django',
                        'coverage',
                        'nose',
                        'mock'],
    py_modules=['django_drapes'],
    classifiers=['Framework :: Django',],
)
