#!/bin/bash

# Automated release script for appstore-connect-client

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if version argument is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Version number required${NC}"
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 0.2.0"
    exit 1
fi

VERSION=$1
VERSION_TAG="v${VERSION}"

echo -e "${GREEN}Preparing release for version ${VERSION}${NC}"

# Check if we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}Error: Releases must be made from the main branch${NC}"
    echo "Current branch: $CURRENT_BRANCH"
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Error: There are uncommitted changes${NC}"
    git status --short
    exit 1
fi

# Check if CHANGELOG.md contains entry for this version
echo -e "${YELLOW}Checking CHANGELOG.md for version ${VERSION}...${NC}"
if ! grep -q "## \[${VERSION}\]" CHANGELOG.md; then
    echo -e "${RED}Error: CHANGELOG.md does not contain an entry for version ${VERSION}${NC}"
    echo "Please add a changelog entry for this version before releasing."
    exit 1
fi
echo -e "${GREEN}✓ CHANGELOG.md contains entry for version ${VERSION}${NC}"

# Pull latest changes
echo -e "${YELLOW}Pulling latest changes from origin/main...${NC}"
git pull origin main

# Update version in setup.py
echo -e "${YELLOW}Updating version in setup.py...${NC}"
sed -i.bak "s/version=\".*\"/version=\"${VERSION}\"/" setup.py
rm setup.py.bak

# Update version in __init__.py
echo -e "${YELLOW}Updating version in __init__.py...${NC}"
sed -i.bak "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" src/appstore_connect/__init__.py
rm src/appstore_connect/__init__.py.bak

# Update version in pyproject.toml (only in [project] section)
echo -e "${YELLOW}Updating version in pyproject.toml...${NC}"
# Use awk to update only the version line in the [project] section
awk -v ver="${VERSION}" '
    /^\[project\]/ { in_project = 1 }
    /^\[/ && !/^\[project\]/ { in_project = 0 }
    in_project && /^version = / { print "version = \"" ver "\""; next }
    { print }
' pyproject.toml > pyproject.toml.tmp && mv pyproject.toml.tmp pyproject.toml

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
python3 -m pytest

# Run linting
echo -e "${YELLOW}Running black formatter check...${NC}"
python3 -m black --check src/appstore_connect tests

echo -e "${YELLOW}Running flake8...${NC}"
python3 -m flake8 src/appstore_connect tests --max-line-length=100 --extend-ignore=E203,W503

echo -e "${YELLOW}Running mypy...${NC}"
python3 -m mypy src/appstore_connect

# Build the package
echo -e "${YELLOW}Building package...${NC}"
rm -rf dist/ build/ *.egg-info
python3 -m build

# Commit version changes
echo -e "${YELLOW}Committing version changes...${NC}"
git add setup.py pyproject.toml src/appstore_connect/__init__.py
git commit -m "Bump version to ${VERSION}"

# Create and push tag
echo -e "${YELLOW}Creating tag ${VERSION_TAG}...${NC}"
git tag -a ${VERSION_TAG} -m "Release version ${VERSION}"

# Push changes and tag
echo -e "${YELLOW}Pushing to origin...${NC}"
git push origin main
git push origin ${VERSION_TAG}

echo -e "${GREEN}✅ Release ${VERSION} prepared successfully!${NC}"
echo ""
echo "The GitHub Actions workflow will now:"
echo "1. Run tests on multiple Python versions"
echo "2. Build the package"
echo "3. Publish to PyPI automatically"
echo "4. Create a GitHub release with changelog notes"
echo ""
echo "Monitor the release at: https://github.com/YOUR_USERNAME/appstore-connect-python/actions"
echo ""
echo -e "${YELLOW}Note: Make sure you've updated CHANGELOG.md before running this script${NC}"