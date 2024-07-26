from setuptools import setup, find_packages

setup(
    name='ifclca',
    version='0.1.0a1',  # Pre-release alpha version
    description='IfcLCA-Py is a Python package for Life Cycle Assessment using Ifc data.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/IfcLCA/IfcLCA-Py',
    author='Louis Trümpler',
    author_email='admifclca@gmail.com',
    license='AGPL-3.0',
    classifiers=[
        'Development Status :: 3 - Alpha',  # Indicates an alpha version
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Operating System :: OS Independent',
    ],
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=[
        'ifcopenshell',
        'pytest' 
    ],
    include_package_data=True,
)