"""
Setup script for the Korean Stock Analysis System.
"""

from setuptools import setup, find_packages

setup(
    name="mypackage",
    version="4.2",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pandas",
        "numpy",
        "yfinance",
        "scikit-learn",
        "matplotlib",
        "seaborn",
        "plotly",
        "requests",
    ],
    python_requires=">=3.7",
    description="Korean Stock Analysis System",
    author="Korean Stock Analysis Team",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
)