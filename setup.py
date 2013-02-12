from distutils.core import setup

name = 'troia-charts-generator'
version = '0.1'

setup(
    name=name,
    version=version,
    description='Troia Charts Generator',
    #install_requires=('troia_client',),
    dependency_links=('https://github.com/kkonrad/troia-python-client.git#egg=troia_client',),
    scripts=('eval_script.py',)
)
