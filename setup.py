from setuptools import setup, find_packages

setup(
    name="gmail-agent",
    version="0.1.0",
    author="TuanNS2",
    author_email="tuanost@gmail.com",
    description="Gmail Agent with AI analysis capabilities",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/tuanns2/gmail-agent",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "google-auth-oauthlib",
        "google-api-python-client",
        "nltk",
        "scikit-learn",
        "numpy",
        "python-dotenv",
        "google-generativeai",
    ],
    entry_points={
        "console_scripts": [
            "gmail-agent=gmail_agent.main:main",
        ],
    },
)
