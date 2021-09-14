from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='My MA',
    version='1.0',
    description='Ontology Population Using Web Scraping with Python',
    long_description=readme,
    author='Miguel Ramos',
    author_email='miguel.ramos.95@outlook.es',
    url='https://github.com/mrdlp/MA',
    license=license,
    packages=find_packages(where=('src'))
    
    #idk if this should be kept, given that there is a requirement.txt file
    install_requires=[
        'requests',
        'bs4'
    ],
)
