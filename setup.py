from setuptools import setup, find_packages

setup(
    name='gym_yotrading',
    version='0.0.16',
    packages=find_packages(),

    author='VL',
    author_email='vladimir.lavrentiev@gmail.com',

    install_requires=[
        'gym>=0.12.5',
        'numpy>=1.16.4',
        'pandas>=0.24.2',
        'matplotlib>=3.1.1'
    ],

    package_data={
        'gym_yotrading': ['datasets/data/*']
    }
)
