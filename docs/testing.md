# NexusAI Testing Guide

This document describes the testing infrastructure for NexusAI, covering unit tests, integration tests, and end-to-end (E2E) tests.

## Overview

NexusAI uses a comprehensive testing strategy:

| Test Type | Backend | Frontend | Location |
|-----------|---------|----------|----------|
| Unit Tests | pytest | Vitest | `backend/tests/unit/`, `frontend/tests/` |
| Integration Tests | pytest + testcontainers | - | `backend/tests/integration/` |
| E2E Tests | - | Playwright | `e2e/tests/` |

## Backend Testing

### Setup

```bash
cd backend
pip install -e ".[dev,test]"
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py -v

# Run specific test
pytest tests/unit/test_auth.py::TestAuthEndpoints::test_login_success -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

### Test Structure

```
backend/tests/
├── conftest.py          # Shared fixtures
├── fixtures/
│   └── seed_data.py     # Synthetic test data
├── unit/
│   ├── test_auth.py     # Authentication tests
│   ├── test_chat.py     # Chat completion tests
│   └── test_health.py   # Health endpoint tests
└── integration/
    └── test_database.py # Database operations
```

### Fixtures

Key fixtures defined in `conftest.py`:

- `db_session` - Async database session
- `test_user` - Regular test user
- `admin_user` - Admin user with elevated privileges
- `auth_token` - JWT token for authenticated requests
- `test_client` - FastAPI test client

### Seed Data

Load synthetic data for testing:

```python
from tests.fixtures.seed_data import load_seed_data

async def test_with_seed_data(db_session):
    await load_seed_data(db_session)
    # Your test code...
```

## Frontend Testing

### Setup

```bash
cd frontend
npm install
```

### Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm test -- --watch

# Run specific test file
npm test -- tests/components/Button.test.tsx
```

### Test Structure

```
frontend/tests/
├── setup.ts            # Test setup and mocks
├── components/
│   └── Button.test.tsx # Component tests
└── hooks/
    └── useChat.test.ts # Hook tests
```

### Configuration

Vitest configuration is in `vitest.config.ts`:

```typescript
export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
  },
});
```

## E2E Testing

### Setup

```bash
cd e2e
npm install
npx playwright install
```

### Running Tests

```bash
# Run all tests
npm test

# Run with browser visible
npm run test:headed

# Run with Playwright UI
npm run test:ui

# Run specific browser
npm run test:chromium
npm run test:firefox
npm run test:webkit

# Run mobile tests
npm run test:mobile

# Generate tests interactively
npm run codegen
```

### Test Structure

```
e2e/
├── playwright.config.ts    # Playwright configuration
├── package.json
├── fixtures/
│   └── test-data.ts        # Test data helpers
├── playwright/.auth/       # Auth state storage
└── tests/
    ├── auth.setup.ts       # Authentication setup
    ├── auth.spec.ts        # Authentication tests
    ├── chat.spec.ts        # Chat interface tests
    ├── documents.spec.ts   # Document management tests
    ├── home.spec.ts        # Home page tests
    └── navigation.spec.ts  # Navigation tests
```

### Writing E2E Tests

```typescript
import { test, expect } from '@playwright/test';

test('should complete user flow', async ({ page }) => {
  // Navigate
  await page.goto('/chat');

  // Interact
  await page.getByPlaceholder('message').fill('Hello');
  await page.getByRole('button', { name: 'send' }).click();

  // Assert
  await expect(page.getByText('Hello')).toBeVisible();
});
```

### Authentication

E2E tests use stored authentication state. The setup runs once before tests:

```typescript
// auth.setup.ts
setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.context().storageState({ path: authFile });
});
```

## CI Integration

Tests run automatically on every push and PR:

1. **Backend Lint** - Ruff + MyPy
2. **Backend Tests** - pytest with PostgreSQL + Redis
3. **Frontend Lint** - ESLint + TypeScript
4. **Frontend Tests** - Vitest
5. **Frontend Build** - Next.js production build
6. **E2E Tests** - Playwright (after unit tests pass)

### Running Tests Locally (Full Stack)

```bash
# Terminal 1: Start services
docker compose up -d postgres redis

# Terminal 2: Run backend tests
cd backend && pytest tests/ -v

# Terminal 3: Run frontend tests
cd frontend && npm test

# Terminal 4: Run E2E tests (after starting servers)
cd e2e && npm test
```

## Best Practices

1. **Test isolation** - Each test should be independent
2. **Mock external services** - Use mocks for APIs, email, etc.
3. **Use fixtures** - Reuse setup code via fixtures
4. **Descriptive names** - Test names should describe the scenario
5. **Fast feedback** - Unit tests should run quickly
6. **Visual regression** - Use Playwright screenshots for UI testing

## Troubleshooting

### Backend Tests

- **Database connection errors**: Ensure PostgreSQL is running
- **Redis errors**: Ensure Redis is running
- **Import errors**: Run `pip install -e ".[dev,test]"`

### Frontend Tests

- **React errors**: Check that jsdom is configured
- **Module not found**: Run `npm install`

### E2E Tests

- **Browser not found**: Run `npx playwright install`
- **Timeout errors**: Increase timeout in config
- **Auth errors**: Delete `playwright/.auth/` and re-run setup
