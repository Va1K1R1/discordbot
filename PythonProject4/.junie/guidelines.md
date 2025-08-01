# Development Guidelines

This document provides guidelines for developing and maintaining the MyPackage project. It is intended for advanced developers and focuses on project-specific information.

## Build/Configuration Instructions

### Setting Up the Development Environment

1. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # On Windows
   ```

2. **Install Development Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install the Package in Development Mode**:
   ```bash
   pip install -e .
   ```
   This installs the package in "editable" mode, allowing you to make changes to the code without reinstalling.

### Project Structure

The project follows a standard Python package structure:

```
mypackage/
├── .junie/                  # Project guidelines
├── src/                     # Source code
│   └── mypackage/           # Main package
│       ├── __init__.py      # Package initialization
│       └── calculator.py    # Example module
├── tests/                   # Test directory
│   └── test_calculator.py   # Tests for calculator module
├── setup.py                 # Package setup configuration
├── requirements.txt         # Development dependencies
└── README.md                # Project overview
```

## Testing Information

### Running Tests

The project uses pytest as the testing framework. To run the tests:

```bash
python -m pytest
```

### Test Coverage

To run tests with coverage reporting:

```bash
python -m pytest --cov=src
```

This will show the percentage of code covered by tests. Aim for at least 90% coverage for production code.

### Adding New Tests

1. **Test File Naming**: Test files should be named `test_*.py` to be automatically discovered by pytest.

2. **Test Function Naming**: Test functions should be named `test_*` to be recognized as tests.

3. **Test Organization**: 
   - Place tests in the `tests/` directory
   - Mirror the package structure in the tests directory
   - Group related tests in the same file

4. **Example Test**:
   ```python
   # tests/test_new_module.py
   import pytest
   from src.mypackage.new_module import new_function

   def test_new_function():
       # Arrange
       input_value = 5
       expected_output = 10
       
       # Act
       result = new_function(input_value)
       
       # Assert
       assert result == expected_output
   ```

5. **Testing Exceptions**:
   ```python
   def test_function_raises_exception():
       with pytest.raises(ValueError):
           function_that_should_raise()
   ```

## Code Quality

### Code Style

The project follows the PEP 8 style guide. Use flake8 to check for style issues:

```bash
flake8 src tests
```

Common style requirements:
- Use 4 spaces for indentation
- Maximum line length of 79 characters
- Two blank lines before function and class definitions
- No trailing whitespace
- Add a newline at the end of files

### Code Formatting

Use black to automatically format code:

```bash
black src tests
```

### Type Checking

The project uses mypy for static type checking:

```bash
mypy src
```

For better type checking, add type annotations to functions:

```python
def add(a: float, b: float) -> float:
    return a + b
```

## Development Workflow

1. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make Changes and Run Tests**:
   ```bash
   # Make your changes
   python -m pytest
   flake8 src tests
   mypy src
   ```

3. **Format Code**:
   ```bash
   black src tests
   ```

4. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Add new feature"
   ```

5. **Push Changes**:
   ```bash
   git push origin feature/new-feature
   ```

## Documentation

- Use docstrings for all modules, classes, and functions
- Follow the Google docstring style
- Keep the README.md up to date with installation and usage instructions