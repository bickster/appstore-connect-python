#!/bin/bash

# Manual build and upload script for appstore-connect-client

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building and uploading appstore-connect-client to PyPI${NC}"

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}Warning: There are uncommitted changes${NC}"
    git status --short
    echo ""
    read -p "Do you want to continue? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted${NC}"
        exit 1
    fi
fi

# Check if .pypirc exists
if [ ! -f ~/.pypirc ]; then
    echo -e "${RED}Error: ~/.pypirc not found${NC}"
    echo "Please create ~/.pypirc with your PyPI credentials"
    echo "You can use .pypirc.template as a reference"
    exit 1
fi

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
python3 -m pytest || {
    echo -e "${RED}Tests failed! Fix the tests before uploading.${NC}"
    exit 1
}

# Run linting
echo -e "${YELLOW}Running code quality checks...${NC}"
python3 -m black --check src/appstore_connect tests || {
    echo -e "${RED}Black formatting check failed!${NC}"
    echo "Run 'python3 -m black src/appstore_connect tests' to fix formatting"
    exit 1
}

python3 -m flake8 src/appstore_connect tests --max-line-length=100 --extend-ignore=E203,W503 || {
    echo -e "${RED}Flake8 linting failed!${NC}"
    exit 1
}

python3 -m mypy src/appstore_connect || {
    echo -e "${RED}Mypy type checking failed!${NC}"
    exit 1
}

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf dist/ build/ *.egg-info

# Build the package
echo -e "${YELLOW}Building package...${NC}"
python3 -m build

# Display what will be uploaded
echo -e "${YELLOW}The following files will be uploaded:${NC}"
ls -la dist/

# Confirm upload
echo ""
read -p "Do you want to upload to PyPI? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Upload cancelled${NC}"
    exit 0
fi

# Upload to PyPI
echo -e "${YELLOW}Uploading to PyPI...${NC}"
python3 -m twine upload dist/*

echo -e "${GREEN}✅ Successfully uploaded to PyPI!${NC}"
echo ""
echo "You can now install the package with:"
echo "  pip install appstore-connect-client"