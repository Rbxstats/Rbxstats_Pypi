import io
import os
from setuptools import setup, find_packages

# Read the contents of your README file
here = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    # Basic package info
    name="rbxstats",
    version="3.0.6",
    description="A comprehensive Python client for the RbxStats API",
    long_description=long_description,
    long_description_content_type="text/markdown",

    # Authorship
    author="RbxStats Team",
    author_email="rbxstatsxyz@gmail.com",
    url="https://github.com/Rbxstats/Rbxstats_Pypi",

    # What’s actually in the package
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,            # include files from MANIFEST.in

    # Dependencies
    install_requires=[
        "requests>=2.25.0",
        "aiohttp>=3.7.0",
    ],
    python_requires=">=3.7",

    # Optional entry points (e.g. console scripts)
    entry_points={
        # "console_scripts": [
        #     "rbxstats=rbxstats.cli:main",
        # ],
    },

    # Additional metadata for PyPI
    license="MIT",
    keywords="roblox api client rbxstats",
    project_urls={
        "Documentation": "https://github.com/Rbxstats/Rbxstats_Pypi#readme",
        "Source": "https://github.com/Rbxstats/Rbxstats_Pypi",
        "Tracker": "https://github.com/Rbxstats/Rbxstats_Pypi/issues",
    },
    classifiers=[
        # maturity
        "Development Status :: 4 - Beta",
        # audience
        "Intended Audience :: Developers",
        # license
        "License :: OSI Approved :: MIT License",
        # language
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        # environments
        "Operating System :: OS Independent",
    ],
)
