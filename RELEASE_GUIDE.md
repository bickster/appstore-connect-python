# Release Guide

This guide explains how to create a new release of the `appstore-connect-client` package.

## Prerequisites

Before creating a release, ensure you have:

1. **PyPI Account**: You need an account on [PyPI](https://pypi.org/) with maintainer access to the package
2. **PyPI API Token**: Generate an API token from your PyPI account settings
3. **GitHub Repository Access**: Push access to the main branch and ability to create tags
4. **Development Environment**: All development dependencies installed (`pip install -e .[dev]`)
5. **Clean Working Directory**: No uncommitted changes in your local repository
6. **Updated CHANGELOG.md**: Document all changes for the new version before releasing

## Automated Release Process

The recommended way to create a release is using the automated release script:

```bash
./release.sh <version>
```

For example:
```bash
./release.sh 0.2.0
```

This script will:
1. Verify you're on the main branch with no uncommitted changes
2. Check that CHANGELOG.md contains an entry for the new version
3. Pull the latest changes from origin/main
4. Update version numbers in `setup.py`, `pyproject.toml`, and `__init__.py`
5. Run all tests and linting checks
6. Build the package
7. Commit the version changes
8. Create and push a git tag
9. Trigger the GitHub Actions workflow which will:
   - Run tests on multiple Python versions
   - Build and publish to PyPI
   - Create a GitHub release with changelog notes

## Manual Release Process

If you need to create a release manually:

### 1. Update Version Numbers

Update the version in three files:
- `setup.py`: Change the `version` parameter
- `pyproject.toml`: Update the `version` field
- `src/appstore_connect/__init__.py`: Update `__version__`

### 2. Run Quality Checks

```bash
# Run tests
python -m pytest

# Check code formatting
python -m black --check src/appstore_connect tests

# Run linter
python -m flake8 src/appstore_connect tests --max-line-length=100 --extend-ignore=E203,W503

# Type checking
python -m mypy src/appstore_connect
```

### 3. Build the Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build source distribution and wheel
python -m build
```

### 4. Create Git Tag

```bash
# Commit version changes
git add setup.py pyproject.toml src/appstore_connect/__init__.py
git commit -m "Bump version to X.Y.Z"

# Create annotated tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"

# Push changes and tag
git push origin main
git push origin vX.Y.Z
```

### 5. Upload to PyPI (if GitHub Actions fails)

If the automated upload fails, you can manually upload:

```bash
# Using the build_and_upload.sh script (builds and uploads)
./build_and_upload.sh

# Or build without uploading
./build_and_upload.sh --no-upload

# Then manually upload with twine
python -m twine upload dist/*
```

## Post-Release Tasks

After creating a release:

1. **Verify PyPI Upload**: Check that the new version appears on [PyPI](https://pypi.org/project/apple-appstore-connect-client/)
2. **Verify GitHub Release**: Check that the release was automatically created with changelog notes
3. **Test Installation**: In a clean environment, test `pip install apple-appstore-connect-client==X.Y.Z`
4. **Update Documentation**: If there are new features, update the documentation accordingly

Note: CHANGELOG.md should be updated BEFORE running the release script, and GitHub releases are now created automatically.

## Setting Up GitHub Actions for PyPI

To enable automated PyPI uploads via GitHub Actions:

1. Generate a PyPI API token:
   - Log in to PyPI
   - Go to Account Settings → API tokens
   - Create a new token scoped to this project

2. Add the token to GitHub:
   - Go to repository Settings → Secrets and variables → Actions
   - Create a new secret named `PYPI_API_TOKEN`
   - Paste your PyPI token as the value

3. The GitHub Actions workflow will automatically:
   - Run when you push a tag starting with 'v'
   - Execute all tests on Python 3.8-3.12
   - Build the package
   - Upload to PyPI using the token
   - Extract release notes from CHANGELOG.md
   - Create a GitHub release with the changelog notes
   - Attach the built wheel and source distribution to the release

## Troubleshooting

### Tests Failing
- Ensure all tests pass locally before creating a release
- Check that test dependencies are up to date
- Review recent changes that might have broken tests

### Version Conflicts
- PyPI doesn't allow re-uploading the same version
- If you need to fix something, increment the version number
- Consider using post-releases (X.Y.Z.post1) for critical fixes

### GitHub Actions Failures
- Check the Actions tab for detailed error logs
- Verify the PYPI_API_TOKEN secret is correctly set
- Ensure the tag format matches the expected pattern (vX.Y.Z)

### Manual Upload Issues
- Verify your PyPI credentials in ~/.pypirc
- Ensure you have upload permissions for the package
- Check that the built files in dist/ are valid

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version (X.0.0): Incompatible API changes
- **MINOR** version (0.Y.0): New functionality, backwards compatible
- **PATCH** version (0.0.Z): Backwards compatible bug fixes

Examples:
- Breaking change: 1.0.0 → 2.0.0
- New feature: 1.0.0 → 1.1.0
- Bug fix: 1.0.0 → 1.0.1