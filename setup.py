from setuptools import setup

setup(
    name='seed_isort_config',
    description='Statically populate the `known_third_party` `isort` setting.',
    url='https://github.com/asottile/seed-isort-config',
    version='1.5.0',
    author='Anthony Sottile',
    author_email='asottile@umich.edu',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    install_requires=['aspy.refactor_imports'],
    py_modules=['seed_isort_config'],
    entry_points={
        'console_scripts': ['seed-isort-config=seed_isort_config:main'],
    },
)
