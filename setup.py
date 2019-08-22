
from distutils.core import setup

setup(

    name='PyFlickr',
    version='0.1a',
    
    description='Python Flickr API bindings.',
    url='http://github.com/mikeboers/PyFlickr',
    author='Mike Boers',
    author_email='pyflickr@mikeboers.com',
    license='New BSD License',
    
    packages=['flickr'],
    install_requires=['oauth2', 'six'],
    
)
