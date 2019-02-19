import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="hockey_scraper",
    version="1.0",
    author="Jesse Moore",
    author_email="jessemoore07@gmail.com",
    description="Package for scraping hockey games from NHL and ESPN",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jes-moore/hockey_scraper",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    )
