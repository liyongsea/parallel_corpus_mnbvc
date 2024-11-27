import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'requirements.txt')) as f:
    required = f.read().splitlines()

setup(
    name='parallel_corpus_mnbvc',
    version='1.0.8',
    author='',
    author_email='',
    description='parallel corpus dataset from the pypi repository of the mnbvc project',
    url='https://github.com/liyongsea/parallel_corpus_mnbvc',
    packages=find_packages(),
    py_modules=['parallel_corpus_mnbvc'],
    include_package_data=True,
    install_requires=required,
    license="Apache License Version 2.0"
)