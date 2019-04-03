from setuptools import setup
import os

# Get the long description from the README file
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
        name='ruccola',
        version='0.0.1',
        description='A rocket.chat client',
        long_description=long_description,
        long_description_content_type='text/markdown',
        url='https://github.com/krig/ruccola',
        author='Kristoffer Grönlund',
        author_email='kgronlund@suse.com',
        keywords='rocket.chat client',
        packages=['libruccola'],
        python_requires='>=3.5',
        install_requires=['requests>=2.18', 'prompt_toolkit>=2', 'websockets>=3.4'],
        entry_points={
            'console_scripts': [
                'ruccola=libruccola:main',
            ],
        },
    )
