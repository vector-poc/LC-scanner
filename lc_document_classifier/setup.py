from setuptools import setup, find_packages

setup(
    name="lc-document-classifier",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain>=0.3.11",
        "langchain-openai>=0.2.12", 
        "langgraph>=0.6.1",
        "pydantic>=2.10.3",
        "python-dotenv>=1.0.1",
    ],
    python_requires=">=3.11",
)