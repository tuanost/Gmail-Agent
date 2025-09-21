from setuptools import setup, find_packages

setup(
    name="gmail-agent",
    version="0.2.0",  # Bumped version for new features
    author="TuanNS2",
    author_email="tuanost@gmail.com",
    description="Gmail Agent with AI analysis capabilities",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/tuanost/Gmail-Agent",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "google-auth-oauthlib>=1.0.0",
        "google-api-python-client>=2.86.0",
        "google-auth-httplib2>=0.1.0",
        "nltk>=3.8.1",
        "scikit-learn>=1.3.0",
        "numpy>=1.25.2",
        "scipy>=1.11.2",
        "openai>=1.0.0",
        "google-generativeai>=0.3.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.13.0",
    ],
    entry_points={
        "console_scripts": [
            "gmail-agent=gmail_agent.main:main",
        ],
    },
)
