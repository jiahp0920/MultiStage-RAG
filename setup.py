from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="multistage-rag",
    version="1.0.0",
    author="MultiStage-RAG Team",
    author_email="multistage-rag@example.com",
    description="A configurable multi-stage RAG system with recall, pre-ranking, and re-ranking stages",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/MultiStage-RAG",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "all": [
            "openai>=1.0.0",
            "anthropic>=0.7.0",
            "pinecone-client>=2.2.0",
            "weaviate-client>=3.26.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "multistage-rag-api=multistage_rag.api.app:main",
            "multistage-rag-cli=multistage_rag.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)