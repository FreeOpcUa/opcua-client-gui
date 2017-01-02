from setuptools import setup, find_packages


setup(name="opcua-client",
      version="0.5.0",
      description="Minimal OPC-UA Client GUI",
      author="Olivier R-D",
      url='https://github.com/FreeOpcUa/opcua-client-gui',
      packages=["uaclient"],
      license="GNU General Public License",
      install_requires=["freeopcua", "opcua-widgets"],
      entry_points={'console_scripts':
                    ['opcua-client = uaclient.mainwindow:main']
                    }
      )
