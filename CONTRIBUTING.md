# Contributing to RAG-Powered Domain Expert System

Thank you for considering contributing to this project! We welcome contributions from the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guidelines](#style-guidelines)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please be respectful and constructive in all interactions.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/RAG-Powered-Domain-Expert-System.git`
3. Add upstream remote: `git remote add upstream https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System.git`

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- OpenAI API key

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Set up environment
cp .env.example .env
# Edit .env with your API key
```

### Development Tools

We use several tools to maintain code quality:

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking
- **Pytest**: Testing
- **Pre-commit**: Git hooks

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-new-embedding-model`
- `bugfix/fix-upload-error`
- `docs/update-api-documentation`
- `refactor/improve-vector-search`

### Commit Messages

Follow conventional commit format:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```
feat(api): add support for DOCX files

fix(vectorstore): resolve embedding dimension mismatch

docs(readme): update installation instructions
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### Writing Tests

- Place tests in the `tests/` directory
- Use pytest fixtures for setup/teardown
- Mock external API calls (OpenAI)
- Aim for >80% code coverage
- Test both success and failure cases

Example:

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_feature(sample_data):
    assert sample_data["key"] == "value"
```

## Submitting Changes

### Pull Request Process

1. **Update your fork**

   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

4. **Run quality checks**

   ```bash
   # Format code
   black .

   # Check linting
   flake8 .

   # Run tests
   pytest
   ```

5. **Commit changes**

   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

6. **Push to your fork**

   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create Pull Request**
   - Go to GitHub and create a PR
   - Fill out the PR template
   - Link related issues
   - Request review

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts
- [ ] CI/CD pipeline passes

## Style Guidelines

### Python Style

We follow PEP 8 with these specifics:

- **Line length**: 88 characters (Black default)
- **Imports**: Organized using isort
- **Type hints**: Use type hints where possible
- **Docstrings**: Google style

Example:

```python
from typing import List, Optional

def process_documents(
    documents: List[str],
    chunk_size: int = 1000,
    overlap: Optional[int] = None
) -> List[dict]:
    """
    Process documents into chunks.

    Args:
        documents: List of document texts
        chunk_size: Maximum chunk size in characters
        overlap: Number of overlapping characters

    Returns:
        List of processed document chunks

    Raises:
        ValueError: If chunk_size is invalid
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    # Implementation here
    return []
```

### File Organization

```python
# Standard library imports
import os
import sys

# Third-party imports
import numpy as np
from fastapi import FastAPI

# Local imports
from core.vector_store import VectorStore
from config.settings import settings
```

### Documentation

- Update README.md for user-facing changes
- Update API.md for API changes
- Add docstrings to all functions/classes
- Include examples in documentation

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Check existing issues/discussions first

## Contact

- **Author**: Mohamed Noorul Naseem
- **Email**: noorulnaseem11@gmail.com
- **GitHub**: [mohamednoorulnaseem](https://github.com/mohamednoorulnaseem)
- **LinkedIn**: [mohamednoorulnaseem](https://www.linkedin.com/in/mohamednoorulnaseem)

## Recognition

Contributors will be recognized in:

- README.md Contributors section
- Release notes
- Project documentation

Thank you for contributing!
