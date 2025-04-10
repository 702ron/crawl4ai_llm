#!/usr/bin/env python
"""
Setup script for crawl4ai_llm.
"""

import os

from setuptools import find_packages, setup

# Read the contents of README.md
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

# Read version from package __init__.py
about = {}
with open(os.path.join("crawl4ai_llm", "__init__.py"), encoding="utf-8") as f:
    exec(f.read(), globals(), about)

# Read requirements from requirements.txt
with open("requirements.txt", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="crawl4ai_llm",
    version=about["__version__"],
    description="E-commerce product data extraction using Crawl4AI and LLMs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/crawl4ai_llm",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "crawl4ai-extract=crawl4ai_llm.__main__:main",
            "crawl4ai-api=crawl4ai_llm.api.cli:main",
        ],
    },
)
