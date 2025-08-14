# E2E Testing Setup

## Quick Setup

```bash
# 1. Copy the example file
cp .env.test.example .env.test

# 2. Set your admin password in .env.test  
nano .env.test

# 3. Run tests
npm run test:e2e:watching
```

## What You Need

Your admin credentials from the Docker environment:

- **Username**: `admin` 
- **Password**: The admin password you set up

## If Tests Fail

**Authentication Error**: Check that your credentials are set:

```bash
# Check .env.test file exists and has the password set
cat .env.test

# Or run with environment variables directly
E2E_TEST_USERNAME=admin E2E_TEST_PASSWORD=your_password npm run test:e2e:watching
```

**Environment Variable Missing**: The tests will show a clear error:
```
❌ E2E_TEST_USERNAME environment variable is required
```

## Available Commands

```bash
npm run test:e2e:watching    # Watching system tests
npm run test:e2e             # All E2E tests  
npm run test:e2e:ui          # Interactive test runner
npm run test:e2e:debug       # Debug mode
```

## Notes

- `.env.test` is ignored by git (won't be committed)
- Use the same admin credentials from your Docker setup
- Tests require the backend to be running on localhost:8000