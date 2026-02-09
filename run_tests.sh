#!/bin/bash
# Test runner script for Discord Overseerr Bot

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[TEST]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest is not installed"
    print_status "Installing test dependencies..."
    pip install -r requirements.txt
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"

case $TEST_TYPE in
    "all")
        print_status "Running all tests with coverage..."
        pytest --cov=bot --cov-report=term-missing --cov-report=html
        ;;
    
    "unit")
        print_status "Running unit tests only..."
        pytest -m unit -v
        ;;
    
    "integration")
        print_status "Running integration tests only..."
        pytest -m integration -v
        ;;
    
    "fast")
        print_status "Running fast tests (no coverage)..."
        pytest -v
        ;;
    
    "coverage")
        print_status "Running tests with coverage report..."
        pytest --cov=bot --cov-report=term-missing --cov-report=html --cov-report=xml
        print_status "Coverage report generated in htmlcov/index.html"
        ;;
    
    "watch")
        print_status "Running tests in watch mode..."
        if command -v ptw &> /dev/null; then
            ptw
        else
            print_warning "pytest-watch not installed. Installing..."
            pip install pytest-watch
            ptw
        fi
        ;;
    
    "debug")
        print_status "Running tests in debug mode (with pdb)..."
        pytest -v --pdb --showlocals
        ;;
    
    "failed")
        print_status "Re-running last failed tests..."
        pytest --lf -v
        ;;
    
    "parallel")
        print_status "Running tests in parallel..."
        if command -v pytest-xdist &> /dev/null; then
            pytest -n auto -v
        else
            print_warning "pytest-xdist not installed. Installing..."
            pip install pytest-xdist
            pytest -n auto -v
        fi
        ;;
    
    "specific")
        if [ -z "$2" ]; then
            print_error "Please specify a test file or path"
            echo "Usage: $0 specific <test_path>"
            exit 1
        fi
        print_status "Running specific test: $2"
        pytest "$2" -v
        ;;
    
    "help"|"-h"|"--help")
        echo "Discord Overseerr Bot Test Runner"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  all          - Run all tests with coverage (default)"
        echo "  unit         - Run unit tests only"
        echo "  integration  - Run integration tests only"
        echo "  fast         - Run tests without coverage (faster)"
        echo "  coverage     - Run tests and generate detailed coverage report"
        echo "  watch        - Run tests in watch mode (re-run on file changes)"
        echo "  debug        - Run tests in debug mode (with pdb)"
        echo "  failed       - Re-run only failed tests from last run"
        echo "  parallel     - Run tests in parallel (faster)"
        echo "  specific     - Run specific test file/path"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                               # Run all tests"
        echo "  $0 unit                          # Run unit tests"
        echo "  $0 specific tests/test_overseerr.py"
        echo "  $0 coverage                      # Generate coverage report"
        exit 0
        ;;
    
    *)
        print_error "Unknown command: $TEST_TYPE"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac

# Check exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    print_status "✅ Tests completed successfully!"
else
    print_error "❌ Tests failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
