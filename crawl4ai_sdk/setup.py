from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="crawl4ai",
    version="0.1.0",
    author="Crawl4AI Team",
    author_email="info@crawl4ai.com",
    description="Python SDK for the Crawl4AI product extraction service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/crawl4ai/crawl4ai-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        "aiohttp>=3.8.0",
        "pydantic>=1.9.0",
        "typing-extensions>=4.0.0"
    ],
) 