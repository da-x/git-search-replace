#!/usr/bin/env python

from setuptools import setup

setup(
    name='git-search-replace',
    version='1.0.3',
    author='Dan Aloni',
    author_email='alonid@gmail.com',
    packages=['gitsearchreplace',],
    scripts=['bin/gsr-branch.py'],
    url='https://github.com/da-x/git-search-replace',
    license='LICENSE.txt',
    description='a utility on top of git for project-wide '
                'search-and-replace that includes filenames too',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.0',
        'License :: OSI Approved :: BSD License',
    ],
    entry_points = {
        'console_scripts': [
            'git-search-replace.py = gitsearchreplace:main',
        ]
    },
    install_requires=['plumbum>=1.5']
)
