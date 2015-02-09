from setuptools import setup, find_packages

def readme():
	with open('README.md') as f:
		return f.read()

setup(name='herc',
	version='0.1',
	description='herc is a webservice that dispatches jobs to Apache Aurora.',
	long_description=readme(),
	url='http://github.com/broadinstitute/herc',
	author='Broad Institute',
	packages=find_packages(),
	package_data = {
		# Include all JSON schemas.
		'': ['data/schemas/*.json']
		},
	install_requires=[
	 'tornado>=4.0',
	 'jsonschema',
	 'futures'
	],
	entry_points = { 'console_scripts': [ 'herc = webservice.webservice:main' ] },
	zip_safe=False)