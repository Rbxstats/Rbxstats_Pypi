from setuptools import setup, find_packages

setup(
    name="rbxstats",
    version="3.0.5",
    description="A comprehensive client for the RbxStats API",
    author="Rbxstats",
    author_email="rbxstatsxyz@gmail.com",
    url="https://github.com/Rbxstats/Rbxstats_Pypi",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "requests>=2.25.0",
        "aiohttp>=3.7.0",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
