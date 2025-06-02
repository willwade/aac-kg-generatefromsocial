"""
Setup script for AAC Knowledge Graph Generator.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="aac-kg-generator",
    version="0.1.0",
    author="Will Wade",
    author_email="wwade@acecentre.org.uk",
    description="Generate personal knowledge graphs from social data for AAC applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/willwade/aac-kg-generatefromsocial",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "aac-kg=main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt"],
    },
)
