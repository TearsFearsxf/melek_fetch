from setuptools import setup, find_packages

setup(
    name="melek_sys",
    version="1.0.0",
    author="Melek Project",
    author_email="support@melekai.project",
    description="Industrial-grade hardware monitoring and unresponsive process controller for Melek AI",
    long_description="Industrial-grade hardware monitoring and unresponsive process controller for Melek AI",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.8",
    install_requires=[
        "psutil>=5.9.0",
        "WMI>=1.5.0",
        "pywin32>=300",
    ],
)
