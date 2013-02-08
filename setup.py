from setuptools import setup, find_packages
import os

f = open(os.path.join(os.path.dirname(__file__), 'README'))
readme = f.read()
f.close()

setup(
    name='regs_models',
    version="0.1",
    description='Model layer for the various regs tools.',
    long_description=readme,
    author='Andrew Pendleton',
    author_email='apendleton@sunlightfoundation.com',
    url='http://github.com/sunlightlabs/regs_models/',
    packages=find_packages(),
    license='BSD License',
    platforms=["any"],
    py_modules=["regs_models"],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Environment :: Web Environment',
    ],
    install_requires=["pymongo", "mongoengine", "html2text", "PyYaml"]
)
