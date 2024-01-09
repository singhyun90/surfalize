from pathlib import Path
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize
import numpy

with open('README.md', 'r', encoding='utf-8') as file:
    long_description = file.read()

def find_cython_files(directory='.'):
    cython_files = []
    directory = Path(directory)
    for path in directory.rglob('*.pyx'):
        cython_files.append(str(path))
    return cython_files

cython_files = find_cython_files()
ext_modules = cythonize(cython_files)

setup(
    name='surfalize',
    version='0.5.1',
    description='A python module to analyze surface roughness',
    author='Frederic Schell',
    author_email='frederic.schell@iws.fraunhofer.de',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires='>=3.6',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    install_requires=[
        'numpy>=1.18.1',
        'matplotlib>=3.1.1',
        'pandas>=1.0.1',
        'scipy>=1.4.1',
        'tqdm'
    ],
    include_dirs=[numpy.get_include()],
    ext_modules=ext_modules
)
