from setuptools import setup, find_packages

setup(
    name="melek_fetch",
    version="2.0.0",
    author="Melek Project",
    author_email="support@melekai.project",
    description="Anahtarsız ve Ücretsiz API'ler üzerinden Hava Durumu, Döviz/Altın ve Wikipedia veri toplama motoru.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
    ],
)
