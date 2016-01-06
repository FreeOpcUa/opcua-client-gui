from setuptools import setup, find_packages


setup(name="freeopcua-client",
      version="0.4.4",
      description="Minimal OPC-UA Client GUI",
      author="Olivier R-D",
      url='https://github.com/FreeOpcUa/opcua-client-gui',
      packages=["freeopcuaclient"],
      license="GNU General Public License",
      install_requires=["freeopcua"],
      entry_points={'console_scripts':
                    ['freeopcua-client = freeopcuaclient.mainwindow:main']
                    }
      )
