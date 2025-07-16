#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="apple-appstore-connect-client",
    version="0.3.0",
    author="Chris Bick",
    author_email="chris@bickster.com",
    description="A comprehensive Python client for the Apple App Store Connect API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chrisbick/appstore-connect-client",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    keywords="apple, app store connect, api, sales, metadata, ios, apps",
    project_urls={
        "Bug Reports": "https://github.com/chrisbick/appstore-connect-client/issues",
        "Source": "https://github.com/chrisbick/appstore-connect-client",
        "Documentation": "https://appstore-connect-client.readthedocs.io/",
    },
)