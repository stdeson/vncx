from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vncx",
    version="1.1.0",
    author="stdeson",
    author_email="stdeson@gmail.com",
    description="A lightweight VNC client library for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/stdeson/vncx",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        "numpy>=1.18.0",
        "opencv-python>=4.2.0",
        "pycryptodome",
    ],
)