from setuptools import setup, find_packages


def get_requires(path='requirements.txt'):

    with open(path, 'r') as fd:
        requirements = fd.read().split('\n')
    return requirements


setup(
    name='DynamicGravityProcessor',
    version='0.0.9',
    packages=find_packages(where='dgp'),
    url='https://github.com/DynamicGravitySystems/DGP',
    license='Apache v2.0',
    author='Zachery Brady, Chris Bertinato, Daniel Aliod',
    install_requires=get_requires(),
    python_requires='>=3.5',
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'dgp = dgp.__main__.main()'
        ]
    }
)
