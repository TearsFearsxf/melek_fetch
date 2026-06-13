from setuptools import setup, find_packages

setup(
    name="melek_fetch",
    version="2.1.0",
    author="Melek Project",
    author_email="support@melekai.project",
    description="Web scraper, system hardware monitor, and process controller library for Melek AI",
    long_description="Web scraper, system hardware monitor, and process controller library for Melek AI",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "psutil>=5.9.0",
        "WMI>=1.5.0",
        "pywin32>=300",
    ],
)
