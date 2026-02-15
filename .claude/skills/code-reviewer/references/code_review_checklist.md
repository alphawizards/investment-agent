# Code Review Checklist

## Purpose
This checklist provides a comprehensive framework for reviewing code in the quantitative trading platform. Use this as a systematic guide to ensure no critical issues are missed.

---

## 🐍 Python-Specific Checks

### Type Safety
- [ ] All function signatures have type hints for parameters and return values
- [ ] Complex types use proper typing imports (`List`, `Dict`, `Optional`, `Union`, etc.)
- [ ] No use of `Any` type unless absolutely necessary (document why)
- [ ] Type hints are compatible with mypy strict mode

### Code Style (PEP 8)
- [ ] Function and variable names use `snake_case`
- [ ] Class names use `PascalCase`
- [ ] Constants use `UPPER_SNAKE_CASE`
- [ ] Line length ≤ 88 characters (Black formatter standard)
- [ ] Proper spacing around operators and after commas
- [ ] No trailing whitespace

### Documentation
- [ ] All public functions have docstrings (Google or NumPy style)
- [ ] Docstrings include: description, Args, Returns, Raises
- [ ] Complex algorithms have inline comments explaining logic
- [ ] Module-level docstring describes purpose and usage

### Error Handling
- [ ] No bare `except:` clauses (always specify exception type)
- [ ] Exceptions are caught at appropriate level (not too broad)
- [ ] Error messages are descriptive and actionable
- [ ] Resources are properly cleaned up (use context managers)
- [ ] Critical errors are logged with appropriate severity

### Common Python Antipatterns
- [ ] No mutable default arguments (`def func(arg=[]):`)
- [ ] No global variables (use class attributes or dependency injection)
- [ ] No string concatenation in loops (use `''.join()` or f-strings)
- [ ] No `import *` (explicit imports only)
- [ ] No circular imports (refactor if detected)

### Financial Python Specifics
- [ ] Use `Decimal` for money calculations, not `float`
- [ ] All datetime objects are timezone-aware (`pd.Timestamp(..., tz='UTC')`)
- [ ] No direct iteration over pandas DataFrames (use vectorized operations)
- [ ] Large datasets use chunking or incremental processing
- [ ] Numerical operations check for NaN/Inf values

---

## 📘 TypeScript-Specific Checks

### Type Safety
- [ ] `strict` mode enabled in `tsconfig.json`
- [ ] No use of `any` type (use `unknown` if type is truly unknown)
- [ ] No non-null assertions (`!`) without justification
- [ ] Interfaces used for object shapes, types for unions/intersections
- [ ] Proper use of generics for reusable components

### Code Style
- [ ] Variables and functions use `camelCase`
- [ ] Classes and interfaces use `PascalCase`
- [ ] Constants use `UPPER_SNAKE_CASE`
- [ ] Consistent use of semicolons (or consistent omission)
- [ ] Proper indentation (2 or 4 spaces, consistent)

### Documentation
- [ ] Complex functions have JSDoc comments
- [ ] Public APIs are documented with parameter and return types
- [ ] Exported types have descriptive comments

### Common TypeScript Antipatterns
- [ ] No implicit `any` types
- [ ] No type assertions without validation (`as Type`)
- [ ] No ignoring TypeScript errors with `@ts-ignore` (use `@ts-expect-error` with explanation)
- [ ] No empty interfaces (use `type` or add properties)

---

## ⚛️ React-Specific Checks

### Component Design
- [ ] Components are small and focused (single responsibility)
- [ ] Props are properly typed with TypeScript interfaces
- [ ] Default props are defined where appropriate
- [ ] Components use functional style with hooks (not class components)

### Performance
- [ ] Expensive computations use `useMemo`
- [ ] Callback functions use `useCallback` to prevent re-creation
- [ ] Large lists use virtualization (react-window or similar)
- [ ] Components that don't need re-renders are wrapped in `React.memo`
- [ ] No inline function definitions in JSX (`onClick={() => ...}`)

### Hooks Usage
- [ ] `useEffect` dependencies are complete and correct
- [ ] No missing dependencies (ESLint exhaustive-deps rule)
- [ ] Cleanup functions return from `useEffect` when needed
- [ ] Custom hooks follow `use` prefix naming convention
- [ ] State updates use functional form when depending on previous state

### Common React Antipatterns
- [ ] No prop drilling (use Context or state management)
- [ ] No direct DOM manipulation (use refs appropriately)
- [ ] No missing keys in lists
- [ ] No index as key (unless list is static)

---

## 🚀 FastAPI-Specific Checks

### API Design
- [ ] Endpoints follow REST conventions (GET, POST, PUT, DELETE)
- [ ] URL paths use kebab-case (`/api/trade-history`, not `/api/tradeHistory`)
- [ ] Proper HTTP status codes (200, 201, 400, 404, 500, etc.)
- [ ] Request/response models use Pydantic for validation
- [ ] Endpoints have proper OpenAPI documentation (docstrings)

### Security
- [ ] Input validation using Pydantic models
- [ ] Authentication/authorization implemented where needed
- [ ] No sensitive data in logs or error messages
- [ ] CORS configured appropriately (not `allow_origins=["*"]` in production)
- [ ] Rate limiting implemented for public endpoints

### Performance
- [ ] Database queries use async operations (`async def`)
- [ ] No blocking I/O in async endpoints
- [ ] Proper use of dependency injection
- [ ] Database connections use connection pooling
- [ ] Large responses use pagination or streaming

---

## 🗄️ Database & SQL Checks

### Query Safety
- [ ] All queries use parameterized statements (no string concatenation)
- [ ] No SQL injection vulnerabilities
- [ ] Proper escaping of user inputs

### Performance
- [ ] Indexes exist on frequently queried columns
- [ ] No N+1 query problems (use joins or eager loading)
- [ ] Large result sets use pagination
- [ ] Queries avoid `SELECT *` (specify needed columns)

### Data Integrity
- [ ] Foreign key constraints defined
- [ ] Proper use of transactions for multi-step operations
- [ ] Unique constraints on appropriate columns
- [ ] Default values defined where appropriate

---

## 💰 Financial Domain Checks

### Backtesting Integrity
- [ ] No look-ahead bias (signals use only past data)
- [ ] No survivorship bias (universe includes delisted stocks)
- [ ] Corporate actions handled correctly (splits, dividends)
- [ ] Rebalancing respects market hours and holidays
- [ ] Trade costs included in performance calculations

### Numerical Correctness
- [ ] Currency conversion occurs before statistical calculations
- [ ] Floating-point precision issues avoided (use Decimal for money)
- [ ] Timezone handling is consistent and correct
- [ ] NaN/Inf values are handled appropriately
- [ ] Rounding is done consistently (e.g., to 2 decimal places for money)

### Risk Management
- [ ] Position sizing respects risk limits
- [ ] Leverage calculations are correct
- [ ] Drawdown calculations include all costs
- [ ] Volatility calculations use appropriate window sizes
- [ ] Correlation matrices are positive semi-definite

### Data Quality
- [ ] Missing data is handled appropriately (forward fill, drop, interpolate)
- [ ] Outliers are detected and handled
- [ ] Data sources are validated and consistent
- [ ] Historical data includes sufficient lookback period
- [ ] Data is properly aligned by timestamp

---

## 🧪 Testing Checks

### Test Coverage
- [ ] Critical business logic has unit tests
- [ ] Edge cases are tested (empty inputs, nulls, extremes)
- [ ] Error paths are tested (exceptions, validation failures)
- [ ] Integration tests for API endpoints
- [ ] Test coverage ≥ 80% for core modules

### Test Quality
- [ ] Tests are independent (no shared state)
- [ ] Tests use descriptive names (`test_calculate_momentum_with_negative_returns`)
- [ ] Tests use fixtures for common setup
- [ ] Tests are fast (< 1 second per test, < 10 seconds total)
- [ ] Mock external dependencies (APIs, databases)

### Financial Testing
- [ ] Backtests are reproducible (fixed random seeds)
- [ ] Known scenarios are tested (2008 crisis, 2020 crash)
- [ ] Edge cases tested (zero returns, missing data, single stock)
- [ ] Performance metrics validated against manual calculations

---

## 🔒 Security Checks

### Secrets Management
- [ ] No hardcoded API keys, passwords, or tokens
- [ ] Secrets loaded from environment variables
- [ ] `.env` file is in `.gitignore`
- [ ] No secrets in Git history (use git-secrets or similar)

### Input Validation
- [ ] All user inputs validated (type, range, format)
- [ ] File uploads restricted by type and size
- [ ] SQL queries use parameterized statements
- [ ] No eval() or exec() with user input

### Authentication & Authorization
- [ ] Passwords are hashed (bcrypt, argon2)
- [ ] Session tokens are secure and expire
- [ ] Authorization checks on all protected endpoints
- [ ] No sensitive data in JWT payload

---

## 📊 Performance Checks

### Algorithmic Complexity
- [ ] No O(n²) or worse algorithms on large datasets
- [ ] Sorting uses efficient algorithms (not bubble sort)
- [ ] Search operations use appropriate data structures (sets, dicts)

### Data Processing
- [ ] Large datasets use streaming or chunking
- [ ] Vectorized operations used instead of loops (pandas, numpy)
- [ ] Caching used for expensive computations
- [ ] Incremental loading for historical data

### Frontend Performance
- [ ] Large lists use virtualization
- [ ] Images are optimized and lazy-loaded
- [ ] Bundle size is reasonable (< 500KB gzipped)
- [ ] No unnecessary re-renders (use React DevTools Profiler)

---

## 📝 Documentation Checks

### Code Documentation
- [ ] README is up-to-date with setup instructions
- [ ] API endpoints are documented (OpenAPI/Swagger)
- [ ] Complex algorithms have explanatory comments
- [ ] Configuration options are documented

### User Documentation
- [ ] User-facing features have usage guides
- [ ] Error messages are clear and actionable
- [ ] Changelog is updated with user-facing changes

---

## 🚢 Deployment Checks

### Pre-Deployment
- [ ] All tests passing
- [ ] Linting passing (ruff, eslint)
- [ ] Type checking passing (mypy, tsc)
- [ ] Security scan passing (bandit, npm audit)
- [ ] Dependencies are up-to-date (no critical vulnerabilities)

### Configuration
- [ ] Environment variables documented
- [ ] Database migrations tested
- [ ] Rollback plan documented
- [ ] Monitoring and logging configured

---

## 📋 Review Severity Levels

### CRITICAL (Must Fix Before Merge)
- Security vulnerabilities
- Data corruption risks
- Look-ahead bias in backtesting
- Hardcoded secrets
- SQL injection vulnerabilities

### WARN (Should Fix Soon)
- Performance issues (O(n²) algorithms)
- Missing error handling
- Incomplete type hints
- Missing tests for critical paths
- Code duplication

### INFO (Consider Improving)
- Code style violations
- Missing documentation
- Potential refactoring opportunities
- Test coverage gaps for non-critical code

---

## 🎯 Review Checklist Summary

Before approving a pull request, ensure:

1. ✅ All automated checks pass (tests, linting, type checking)
2. ✅ No CRITICAL issues remain
3. ✅ WARN issues are documented and tracked
4. ✅ Code is readable and maintainable
5. ✅ Financial domain requirements are met (if applicable)
6. ✅ Security best practices followed
7. ✅ Performance is acceptable
8. ✅ Documentation is updated

---

**Last Updated**: 2024-12-28  
**Version**: 1.0  
**Maintainer**: Code Review Team
