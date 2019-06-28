import os.path

from setuptools import setup, find_packages


def get_data_files():
    """
    Dictionary of data files
    """
    current_dir = os.getcwd()
    data_files = {}
    for package in packages:
        data_files[package] = []
        os.chdir(os.path.join(package))
        for data_dir in ('templates', 'static', 'migrations', 'fixtures', 'features', 'templatetags', 'management'):
            data_files[package].extend(
                [os.path.join(subdir, f) for (subdir, dirs, files) in os.walk(data_dir) for f in files])
        os.chdir(current_dir)
    return data_files


packages = [p.replace(".", "/") for p in sorted(find_packages())]
package_scripts = ["manage.py"]
package_data = get_data_files()

setup(name='bpaotu',
      version='1.24.4',
      description="BPA OTU",
      author='Centre for Comparative Genomics',
      author_email='web@ccg.murdoch.edu.au',
      packages=packages,
      package_data=package_data,
      include_package_data=True,
      zip_safe=False,
      scripts=package_scripts, )
