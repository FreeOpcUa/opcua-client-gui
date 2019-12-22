from setuptools import setup, find_packages


setup(name="opcua-client",
      version="0.8.0",
      description="OPC-UA Client GUI",
      author="Olivier R-D",
      url='https://github.com/FreeOpcUa/opcua-client-gui',
      packages=["uaclient"],
      license="GNU General Public License",
      install_requires=["opcua>=0.98.1", "opcua-widgets>=0.5.4"],
      entry_points={'console_scripts':
                    ['opcua-client = uaclient.mainwindow:main']
                    }
      )
