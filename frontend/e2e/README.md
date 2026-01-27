# NexusAI E2E Testing Framework

End-to-end testing framework for NexusAI using [Playwright](https://playwright.dev/).

## Overview

This E2E testing framework provides:

- **Page Object Model (POM)** - Reusable page objects for clean test code
- **Authentication Setup** - Shared authentication state across tests
- **Visual Regression** - Screenshot comparison for UI changes
- **Smoke Tests** - Quick health checks
- **Cross-browser Testing** - Chrome, Firefox, Safari, and mobile viewports
- **CI/CD Integration** - GitHub Actions workflows

## Directory Structure

```
e2e/
├── .auth/                  # Authentication state storage
├── fixtures/               # Test data and fixtures
│   └── test-data.ts        # User credentials, messages, API responses
├── pages/                  # Page Object Model classes
│   ├── base.page.ts        # Base page with common methods
│   ├── login.page.ts       # Login page interactions
│   ├── register.page.ts    # Registration page interactions
│   ├── chat.page.ts        # Chat page interactions
│   └── index.ts            # Page exports
├── utils/                  # Helper utilities
│   └── test-helpers.ts     # Common test helpers
├── auth.setup.ts           # Authentication setup (runs first)
├── auth.unauth.spec.ts     # Unauthenticated tests (login, register)
├── chat.spec.ts            # Chat functionality tests
├── smoke.spec.ts           # Quick smoke tests
├── visual.spec.ts          # Visual regression tests
└── README.md               # This file
```

## Quick Start

### Prerequisites

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install
```

### Running Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run with UI (interactive mode)
npm run test:e2e:ui

# Run in headed mode (see browser)
npm run test:e2e:headed

# Run specific test suite
npm run test:e2e:smoke    # Smoke tests only
npm run test:e2e:auth     # Authentication tests
npm run test:e2e:chat     # Chat tests
npm run test:e2e:visual   # Visual regression

# Debug mode
npm run test:e2e:debug

# View test report
npm run test:e2e:report

# Update visual snapshots
npm run test:e2e:update-snapshots
```

## Test Categories

### Smoke Tests (`smoke.spec.ts`)

Quick health checks that verify the application is running:

- Application accessibility
- Page load times
- Static asset loading
- No console errors
- API health endpoints

```bash
npm run test:e2e:smoke
```

### Authentication Tests (`auth.unauth.spec.ts`)

Tests for login, registration, and auth flows:

- Login form validation
- Invalid credentials handling
- Successful login flow
- Registration validation
- Protected route redirects
- Session management

```bash
npm run test:e2e:auth
```

### Chat Tests (`chat.spec.ts`)

Core chat functionality tests:

- Message sending and receiving
- Streaming responses
- Conversation management
- Error handling
- Keyboard navigation
- Accessibility

```bash
npm run test:e2e:chat
```

### Visual Regression (`visual.spec.ts`)

Screenshot comparisons for UI consistency:

- Page layouts
- Component states
- Dark mode
- Responsive breakpoints
- Error states

```bash
npm run test:e2e:visual
```

## Page Objects

### Using Page Objects

```typescript
import { test } from '@playwright/test';
import { LoginPage, ChatPage } from './pages';

test('example test', async ({ page }) => {
  const loginPage = new LoginPage(page);
  const chatPage = new ChatPage(page);

  // Navigate and interact
  await loginPage.goto();
  await loginPage.login('user@example.com', 'password');

  // Verify navigation
  await chatPage.assertPageLoaded();
  await chatPage.sendMessage('Hello!');
});
```

### Available Page Objects

| Page | Methods |
|------|---------|
| `LoginPage` | `login()`, `fillLoginForm()`, `assertErrorDisplayed()` |
| `RegisterPage` | `register()`, `fillRegistrationForm()`, `acceptTerms()` |
| `ChatPage` | `sendMessage()`, `startNewChat()`, `selectConversation()` |

## Test Data

### Using Test Data

```typescript
import { testUsers, testMessages, generateTestUser } from './fixtures/test-data';

// Static test data
await loginPage.login(testUsers.development.email, testUsers.development.password);

// Dynamic test data
const newUser = generateTestUser();
await registerPage.register(newUser);
```

## Mocking APIs

### Route Interception

```typescript
test('handle API error', async ({ page }) => {
  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Invalid credentials' }),
    });
  });

  // Test error handling
});
```

### Delayed Responses

```typescript
await page.route('**/api/**', async (route) => {
  await new Promise((resolve) => setTimeout(resolve, 2000));
  await route.continue();
});
```

## Visual Testing

### Capturing Screenshots

```typescript
// Full page screenshot
await expect(page).toHaveScreenshot('page-name.png', { fullPage: true });

// Element screenshot
await expect(page.locator('button')).toHaveScreenshot('button.png');
```

### Updating Baselines

When intentional UI changes are made:

```bash
npm run test:e2e:update-snapshots
```

## Configuration

### `playwright.config.ts`

Key configuration options:

```typescript
{
  testDir: './e2e',
  timeout: 60000,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
  ],
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLAYWRIGHT_BASE_URL` | Application URL | `http://localhost:3000` |
| `CI` | Running in CI environment | - |

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests

Workflow includes:
- Full E2E test suite
- Smoke tests
- Visual regression (on PRs)

### Artifacts

Test artifacts are uploaded on failure:
- Screenshots
- Videos
- Trace files
- HTML report

## Best Practices

### Writing Tests

1. **Use Page Objects** - Keep tests clean and maintainable
2. **Mock External APIs** - Isolate tests from external dependencies
3. **Unique Test Data** - Generate unique data to avoid conflicts
4. **Meaningful Assertions** - Test behavior, not implementation

### Test Organization

1. **Group Related Tests** - Use `test.describe()` blocks
2. **Setup/Teardown** - Use `beforeEach`/`afterEach` hooks
3. **Independent Tests** - Tests should not depend on each other

### Performance

1. **Parallel Execution** - Tests run in parallel by default
2. **Shared Auth State** - Login once, reuse across tests
3. **Avoid Timeouts** - Use proper waits instead of `waitForTimeout()`

## Troubleshooting

### Common Issues

**Tests failing in CI but passing locally:**
- Check for timing issues
- Verify environment variables
- Review CI logs for network errors

**Visual tests failing:**
- Update snapshots if changes are intentional
- Check for font rendering differences
- Verify viewport sizes

**Authentication issues:**
- Clear `.auth/` directory
- Verify test user exists in database
- Check API endpoints

### Debugging

```bash
# Run with debug mode
npm run test:e2e:debug

# Run single test
npx playwright test -g "test name"

# Show browser
npx playwright test --headed

# Generate trace
npx playwright test --trace on
```

## Resources

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Test Assertions](https://playwright.dev/docs/test-assertions)
- [Page Object Models](https://playwright.dev/docs/pom)
