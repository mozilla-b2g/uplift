from setuptools import setup, find_packages
setup(
    name = "gaia_uplift",
    version = "1",
    packages = ['gaia_uplift'],
    package_dir = {'gaia_uplift': 'gaia_uplift'},
    package_data = {'gaia_uplift': ['config.json']},
    entry_points = {
        'console_scripts': [
            'uplift = gaia_uplift.driver:main'
        ]
    },
    install_requires = ["isodate",
                        "requests",
                        "PrettyTable"],
    tests_require = ["nose",
                     "rednose"],
    test_suite = "nose.collector",
    # metadata for upload to PyPI
    author = "John Ford",
    author_email = "john@johnford.info",
    description = "This is a program used to uplift bugs from Gaia's master branch to release branches",
    license = "",
    keywords = "b2g uplift git mozilla firefoxos",
    url = "https://github.com/mozilla-b2g/uplift",   # project home page, if any
    # could also include long_description, download_url, classifiers, etc.
)
