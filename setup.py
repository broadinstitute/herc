from setuptools import setup, find_packages
import os
import os.path
import urllib.parse

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='herc',
      version='0.1',
      description='Herc is a webservice that dispatches jobs to Apache Aurora.',
      long_description=readme(),
      url='http://github.com/broadinstitute/herc',
      author='The Broad Institute',
      packages=find_packages(exclude='tests'),
      data_files=[('data/aurora', ['data/aurora/api.thrift']),
                  ('data/schemas', ['data/schemas/jobsubmit.json']),
                  ('', ['thrift-1.0.0-py3.tar.gz'])],
      install_requires=[
          'tornado>=4.0',
          'jsonschema',
          'futures',
          'Jinja2>=2.2',
          'jsonref',
          'pyhocon',
          'mock',
          'arrow',
          'nose',
          'requests',
          'thrift==1.0.0-py3',
          'munch',
          'shortuuid'
      ],
      entry_points={'console_scripts': ['herc = herc.webservice:main']},
      dependency_links = [urllib.parse.urljoin('file:', os.path.join(os.getcwd(), 'thrift-1.0.0-py3.tar.gz'))],
      zip_safe=False,
      test_suite='nose.collector',
      tests_require=['nose']
      )
