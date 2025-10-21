# GroupGo Testing Guide

## Quick Start

### Prerequisites
Make sure you have Django installed:
```bash
pip3 install -r requirements.txt
```

### Running Tests

#### Option 1: Using the Test Runner Script (Recommended)
```bash
cd groupgo
./run_tests.sh
```

Available options:
- `./run_tests.sh all` - Run all tests (default)
- `./run_tests.sh accounts` - Run only accounts tests
- `./run_tests.sh travel` - Run only travel_groups tests
- `./run_tests.sh home` - Run only home tests
- `./run_tests.sh verbose` - Run with detailed output
- `./run_tests.sh coverage` - Run with coverage report
- `./run_tests.sh fast` - Run with minimal output
- `./run_tests.sh help` - Show help message

#### Option 2: Using Django's manage.py Directly
```bash
cd groupgo
python3 manage.py test                    # Run all tests
python3 manage.py test accounts           # Run accounts tests only
python3 manage.py test travel_groups      # Run travel_groups tests only
python3 manage.py test home               # Run home tests only
```

---

## Test Structure

```
groupgo/
├── accounts/
│   └── tests.py                 # 27 tests for accounts app
├── travel_groups/
│   └── tests.py                 # 27 tests for travel_groups app
├── home/
│   └── tests.py                 # 4 tests for home app
├── TEST_SUMMARY.md              # Detailed test documentation
├── TESTING_GUIDE.md             # This file
└── run_tests.sh                 # Convenient test runner script
```

---

## What's Being Tested?

### Accounts App (27 tests)
✓ User registration and profile creation  
✓ Login/logout functionality  
✓ Dashboard access and display  
✓ Itinerary creation and management  
✓ Phone number validation  
✓ Email validation  
✓ Password validation  
✓ Authentication requirements  

### Travel Groups App (27 tests)
✓ Group creation and management  
✓ Joining and leaving groups  
✓ Group capacity and full group handling  
✓ Admin permissions and restrictions  
✓ Travel preferences management  
✓ Trip preferences management  
✓ Group itinerary management  
✓ Member roles (admin vs member)  
✓ Group settings updates  

### Home App (4 tests)
✓ Homepage accessibility  
✓ Template rendering  
✓ Public access (no login required)  

---

## Test Results

When you run the tests, you should see output like this:

```
Creating test database for alias 'default'...
Found 58 test(s).
System check identified no issues (0 silenced).
..........................................................
----------------------------------------------------------------------
Ran 58 tests in 11.702s

OK
Destroying test database for alias 'default'...
```

### Success Indicators
- All dots (`.`) indicate passing tests
- `OK` at the end confirms all tests passed
- Test database is automatically created and destroyed

### Failure Indicators
- `F` indicates a failed test
- `E` indicates an error in a test
- `FAILED` at the end with details about what failed

---

## Common Test Commands

### Run Specific Test Class
```bash
python3 manage.py test accounts.tests.UserProfileModelTest
python3 manage.py test travel_groups.tests.TravelGroupModelTest
```

### Run Specific Test Method
```bash
python3 manage.py test accounts.tests.UserProfileModelTest.test_create_user_profile
```

### Run with Different Verbosity Levels
```bash
python3 manage.py test --verbosity=0    # Minimal output
python3 manage.py test --verbosity=1    # Default
python3 manage.py test --verbosity=2    # Detailed output
python3 manage.py test --verbosity=3    # Very detailed output
```

### Keep Test Database (for debugging)
```bash
python3 manage.py test --keepdb
```

### Run Tests in Parallel (faster for large test suites)
```bash
python3 manage.py test --parallel
```

---

## Coverage Report (Optional)

To see how much of your code is covered by tests:

### Install coverage
```bash
pip3 install coverage
```

### Run tests with coverage
```bash
./run_tests.sh coverage
```

Or manually:
```bash
coverage run --source='.' manage.py test
coverage report
coverage html
```

Then open `htmlcov/index.html` in a browser to see a detailed HTML report.

---

## Troubleshooting

### Django Not Installed
**Error**: `ModuleNotFoundError: No module named 'django'`

**Solution**:
```bash
pip3 install -r requirements.txt
```

### Permission Denied (Script Not Executable)
**Error**: `Permission denied: ./run_tests.sh`

**Solution**:
```bash
chmod +x run_tests.sh
```

### Database Locked
**Error**: `database is locked`

**Solution**:
```bash
# Remove any leftover test database
rm db.sqlite3
python3 manage.py test
```

### Import Errors
**Error**: `ImportError: cannot import name 'X' from 'Y'`

**Solution**: Make sure you're in the correct directory:
```bash
cd groupgo
python3 manage.py test
```

---

## Test Development Tips

### Writing New Tests

1. **Add tests to the appropriate file**:
   - `accounts/tests.py` for accounts app
   - `travel_groups/tests.py` for travel_groups app
   - `home/tests.py` for home app

2. **Follow the existing pattern**:
   ```python
   class MyNewTest(TestCase):
       """Test cases for my feature"""
       
       def setUp(self):
           """Create test data"""
           self.user = User.objects.create_user(...)
       
       def test_something(self):
           """Test that something works"""
           # Arrange
           # Act
           # Assert
           self.assertEqual(actual, expected)
   ```

3. **Run your new tests**:
   ```bash
   python3 manage.py test myapp.tests.MyNewTest
   ```

### Test Data Best Practices

- Create fresh test data in `setUp()` method
- Don't rely on order of test execution
- Use descriptive variable names
- Clean up after tests (Django does this automatically for database)

### Assertion Methods

Common Django test assertions:
- `assertEqual(a, b)` - Check if a equals b
- `assertTrue(x)` / `assertFalse(x)` - Check boolean value
- `assertIn(a, b)` - Check if a is in b
- `assertRaises(Exception)` - Check if exception is raised
- `assertContains(response, text)` - Check if response contains text
- `assertRedirects(response, url)` - Check if response redirects to url
- `assertTemplateUsed(response, template)` - Check template usage

---

## CI/CD Integration

These tests can be easily integrated into CI/CD pipelines:

### GitHub Actions Example
```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: |
          cd groupgo
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd groupgo
          python manage.py test
```

### GitLab CI Example
```yaml
test:
  image: python:3.12
  script:
    - cd groupgo
    - pip install -r requirements.txt
    - python manage.py test
```

---

## Performance Monitoring

Track test performance over time:
```bash
# Time the test execution
time python3 manage.py test

# Expected result: ~11-12 seconds for all 58 tests
```

If tests are taking significantly longer:
- Check for slow database queries
- Look for tests that might be waiting/sleeping
- Consider using `--parallel` flag

---

## Need Help?

For more detailed information, see:
- `TEST_SUMMARY.md` - Comprehensive test documentation
- Django Testing Documentation: https://docs.djangoproject.com/en/4.2/topics/testing/

---

## Summary

✅ **58 comprehensive tests** covering all major functionality  
✅ **100% passing rate** - all tests green  
✅ **~12 seconds** execution time  
✅ **Easy to run** with convenient script  
✅ **Well documented** with clear descriptions  
✅ **CI/CD ready** for automated testing  

Run `./run_tests.sh` to verify everything works!

