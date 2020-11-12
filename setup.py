from setuptools import setup

with open("readme.md") as readme:
    long_description = readme.read()

setup(
    name="Socket_Singleton",
    version="1.0.0",
    description="Allow a single instance of a Python application to run at once",
    py_modules=["Socket_Singleton"],
    package_dir={"":"src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/emboiko/Socket_Singleton",
    author="Emboiko",
    author_email="ed@emboiko.com",
)
