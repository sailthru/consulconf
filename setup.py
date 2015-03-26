try:
    from distutils.core import setup
    from setuptools import find_packages
except ImportError:
    print("Please install Distutils and setuptools"
          " before installing this package")
    raise

setup(
    name='consulconf',
    version='0.0.11.dev0',
    description=('Code to configure consul key:value store for applications'),

    author='Alex Gaudio',
    author_email='agaudio@sailthru.com',
    url='https://github.com/sailthru/consulconf',

    install_requires=['argparse_tools', 'requests', 'future'],
    packages=find_packages(),

    entry_points={
        'console_scripts': [
            'consulconf = consulconf.__main__:go',
        ],
        'setuptools.installation': [
            'eggsecutable = consulconf.__main__:go',
        ],
    }
)
