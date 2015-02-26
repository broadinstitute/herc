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
      packages=find_packages(exclude='tests'),
      package_data={
          # Include everything in data/, both schemas and examples.
          '': ['data/*']
      },
      install_requires=[
          'tornado>=4.0',
          'jsonschema',
          'futures',
          'Jinja2>=2.2',
          'jsonref'
      ],
      entry_points={'console_scripts': ['herc = herc.webservice:main']},
      zip_safe=False,
      test_suite='nose.collector',
      tests_require=['nose']
      )
