#!/bin/bash

# GroupGo Test Runner Script
# This script runs the Django test suite with various options

echo "======================================="
echo "GroupGo Test Suite"
echo "======================================="
echo ""

# Check if Django is installed
if ! python3 -c "import django" &> /dev/null; then
    echo "Error: Django is not installed!"
    echo "Please run: pip3 install -r requirements.txt"
    exit 1
fi

# Function to display usage
usage() {
    echo "Usage: $0 [option]"
    echo ""
    echo "Options:"
    echo "  all          Run all tests (default)"
    echo "  accounts     Run only accounts app tests"
    echo "  travel       Run only travel_groups app tests"
    echo "  home         Run only home app tests"
    echo "  verbose      Run all tests with verbose output"
    echo "  coverage     Run tests with coverage report (requires coverage package)"
    echo "  fast         Run tests with minimal output"
    echo "  help         Show this help message"
    echo ""
}

# Parse command line arguments
OPTION=${1:-all}

case $OPTION in
    all)
        echo "Running all tests..."
        echo ""
        python3 manage.py test
        ;;
    
    accounts)
        echo "Running accounts app tests..."
        echo ""
        python3 manage.py test accounts
        ;;
    
    travel)
        echo "Running travel_groups app tests..."
        echo ""
        python3 manage.py test travel_groups
        ;;
    
    home)
        echo "Running home app tests..."
        echo ""
        python3 manage.py test home
        ;;
    
    verbose)
        echo "Running all tests with verbose output..."
        echo ""
        python3 manage.py test --verbosity=2
        ;;
    
    coverage)
        echo "Running tests with coverage report..."
        echo ""
        if ! python3 -c "import coverage" &> /dev/null; then
            echo "Error: coverage package is not installed!"
            echo "Please run: pip3 install coverage"
            exit 1
        fi
        coverage run --source='.' manage.py test
        echo ""
        echo "======================================="
        echo "Coverage Report"
        echo "======================================="
        coverage report
        echo ""
        echo "Generating HTML coverage report..."
        coverage html
        echo "HTML report generated in htmlcov/index.html"
        ;;
    
    fast)
        echo "Running tests with minimal output..."
        echo ""
        python3 manage.py test --verbosity=0
        ;;
    
    help)
        usage
        exit 0
        ;;
    
    *)
        echo "Error: Unknown option '$OPTION'"
        echo ""
        usage
        exit 1
        ;;
esac

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================="
    echo "✓ All tests passed successfully!"
    echo "======================================="
    exit 0
else
    echo ""
    echo "======================================="
    echo "✗ Some tests failed!"
    echo "======================================="
    exit 1
fi

