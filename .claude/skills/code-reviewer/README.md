# Code Review System for Quantitative Trading Platform

## Overview

This code review system provides a comprehensive framework for conducting production-grade code reviews specifically tailored for the **potential-parakeet** quantitative trading platform. It combines automated quality checks with domain-specific validation for financial systems.

---

## 📁 Files Included

### 1. `code_review_prompt_revised.xml`
The master prompt template for conducting code reviews. This XML-formatted prompt guides reviewers (human or AI) through a systematic evaluation process.

**Key Features**:
- ✅ Fixed typo from original (`APIsz` → `APIs`)
- ✅ Standardized XML formatting for tech stack
- ✅ Added quantitative finance domain context
- ✅ Expanded quality gates for financial correctness
- ✅ Includes automated tooling references
- ✅ Structured output schema with financial validation section

**Usage**: Use this prompt when reviewing code changes in your quantitative trading platform. Replace `{{INSERT_CONTEXT_HERE}}` and `{{INSERT_CODE_HERE}}` with actual context and code to review.

### 2. `code_review_checklist.md`
A comprehensive checklist covering all aspects of code quality for the platform.

**Sections**:
- Python-specific checks (type safety, PEP 8, documentation)
- TypeScript-specific checks (strict mode, type safety)
- React-specific checks (performance, hooks usage)
- FastAPI-specific checks (API design, security)
- Database & SQL checks (query safety, performance)
- Financial domain checks (backtesting integrity, numerical correctness)
- Testing checks (coverage, quality)
- Security checks (secrets management, input validation)
- Performance checks (algorithmic complexity, data processing)

**Usage**: Reference this checklist during code reviews to ensure no critical issues are missed.

### 3. `coding_standards.md`
Defines coding standards, conventions, and best practices for the platform.

**Sections**:
- Project structure standards
- Python standards (naming, style, type hints, documentation)
- TypeScript standards (naming, configuration, type definitions)
- React component standards
- Testing standards (pytest, Jest/Vitest)
- Git workflow standards (branch naming, commit messages, PR templates)
- Performance standards
- Security standards
- Documentation standards
- Deployment standards

**Usage**: All contributors should follow these standards. Reference during onboarding and code reviews.

### 4. `common_antipatterns.md`
Catalogs common antipatterns and problematic practices to avoid.

**Categories**:
- Python antipatterns (mutable defaults, bare except, global variables)
- TypeScript antipatterns (any types, non-null assertions)
- React antipatterns (inline functions, missing dependencies)
- Financial domain antipatterns (floating-point money, look-ahead bias, survivorship bias)
- Performance antipatterns (N+1 queries, synchronous I/O in async)
- Security antipatterns (hardcoded secrets, SQL injection)

**Usage**: Reference during code reviews to identify and prevent recurring issues.

---

## 🚀 Quick Start

### Step 1: Add Files to Your Repository

Copy the reference files to your `.claude/skills/code-reviewer/references/` directory:

```bash
cd /path/to/potential-parakeet

# Create directory structure
mkdir -p .claude/skills/code-reviewer/references

# Copy reference files
cp code_review_checklist.md .claude/skills/code-reviewer/references/
cp coding_standards.md .claude/skills/code-reviewer/references/
cp common_antipatterns.md .claude/skills/code-reviewer/references/
```

### Step 2: Update Your Code Reviewer Agent

Replace or merge the content of `.claude/agents/code-reviewer.md` with the new prompt:

```bash
# Backup existing agent
cp .claude/agents/code-reviewer.md .claude/agents/code-reviewer.md.backup

# Option A: Replace with new prompt (recommended)
cp code_review_prompt_revised.xml .claude/agents/code-reviewer.md

# Option B: Keep both (quick review + deep review)
# Manually merge the files, keeping your existing quick checklist
# and adding the master prompt for deep reviews
```

### Step 3: Test the System

Test the code review system on a sample code change:

```bash
# Create a test branch
git checkout -b test/code-review-system

# Make a small change
echo "# Test change" >> strategy/signals.py

# Run code review using your AI agent
# (Invoke your code-reviewer agent with the changes)
```

---

## 📋 Usage Examples

### Example 1: Reviewing a New Strategy

**Context**:
```
Adding a new residual momentum strategy that removes Fama-French factors
before calculating momentum scores. This will be used in the Quant 2.0 pipeline.
File: strategy/quant2/momentum/residual_momentum.py
```

**Code to Review**:
```python
def calculate_residual_momentum(returns, factors):
    residuals = returns - (factors @ betas)
    return residuals.rolling(252).mean()
```

**Expected Output**:
- **Score**: 62/100
- **Risk Level**: Medium
- **Issues Detected**:
  - CRITICAL: Undefined variable `betas`
  - WARN: Missing type hints
  - WARN: No error handling
  - INFO: Performance concern with rolling window
- **Refactored Solution**: Corrected code with type hints, error handling, and optimized computation
- **Next Steps**: Fix critical issues before merge

### Example 2: Reviewing an API Endpoint

**Context**:
```
Adding a new FastAPI endpoint to retrieve trade history with pagination.
File: backend/routers/trades.py
```

**Code to Review**:
```python
@router.get("/trades")
def get_trades(ticker: str):
    trades = db.query(Trade).filter(Trade.ticker == ticker).all()
    return trades
```

**Expected Output**:
- **Score**: 58/100
- **Risk Level**: Medium
- **Issues Detected**:
  - WARN: Missing pagination (could return thousands of rows)
  - WARN: No input validation (SQL injection risk)
  - WARN: Should be async function
  - INFO: Missing response model
- **Refactored Solution**: Async endpoint with pagination, Pydantic validation, and response model
- **Next Steps**: Add pagination and input validation before merge

### Example 3: Reviewing a React Component

**Context**:
```
Adding a new trade table component with sorting and filtering.
File: dashboard/src/components/trades/TradeTable.tsx
```

**Code to Review**:
```typescript
function TradeTable({ trades }) {
    return (
        <table>
            {trades.map((trade, index) => (
                <tr key={index} onClick={() => handleClick(trade)}>
                    <td>{trade.ticker}</td>
                </tr>
            ))}
        </table>
    );
}
```

**Expected Output**:
- **Score**: 54/100
- **Risk Level**: Medium
- **Issues Detected**:
  - WARN: Using index as key (causes re-render bugs)
  - WARN: Inline function in onClick (performance issue)
  - WARN: Missing TypeScript types for props
  - INFO: No memoization for expensive operations
- **Refactored Solution**: Typed component with proper keys, memoized callbacks, and performance optimizations
- **Next Steps**: Fix key and inline function issues before merge

---

## 🎯 Integration with Development Workflow

### Pre-Commit Review
Run automated checks before committing:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run all checks
pre-commit run --all-files
```

### Pull Request Review
Use the code review system for all pull requests:

1. **Automated Checks**: CI/CD runs tests, linting, type checking
2. **AI Review**: Use code-reviewer agent for initial assessment
3. **Human Review**: Developer reviews AI findings and approves/requests changes
4. **Merge**: Only merge after all CRITICAL issues are resolved

### Continuous Improvement
Update the reference files as you discover new patterns:

```bash
# Add a new antipattern you discovered
echo "### New Antipattern" >> .claude/skills/code-reviewer/references/common_antipatterns.md

# Commit the update
git add .claude/skills/code-reviewer/references/
git commit -m "docs(code-review): add new antipattern for timezone handling"
```

---

## 🔧 Customization

### Adding Domain-Specific Checks

To add checks specific to your trading strategies, edit `code_review_checklist.md`:

```markdown
## 💰 Financial Domain Checks

### Strategy-Specific Checks
- [ ] OLMAR strategy uses correct kernel function
- [ ] HRP optimization uses proper distance metric
- [ ] Regime detection HMM has sufficient states
- [ ] Meta-labeling uses triple-barrier method correctly
```

### Adjusting Severity Levels

Customize what constitutes CRITICAL vs WARN in your context:

```markdown
### CRITICAL (Must Fix Before Merge)
- Look-ahead bias in backtesting
- Survivorship bias in stock universe
- Missing transaction costs in performance calculations
- Timezone-naive datetime in signal generation

### WARN (Should Fix Soon)
- Missing type hints in strategy code
- Incomplete test coverage for new strategies
- Performance issues in data loading
```

### Adding Automated Tools

Add new tools to the automated checks section in the XML prompt:

```xml
<python_tools>
  <tool>ruff check . --fix</tool>
  <tool>mypy strategy/ backend/ --strict</tool>
  <tool>pytest tests/ --cov --cov-report=term-missing</tool>
  <tool>bandit -r backend/ strategy/ -ll</tool>
  <tool>vulture . --min-confidence 80</tool>  <!-- NEW: Find dead code -->
</python_tools>
```

---

## 📊 Metrics and Reporting

### Code Review Metrics to Track

1. **Review Score Distribution**: Track average scores over time
2. **Issue Severity Breakdown**: Count CRITICAL/WARN/INFO issues
3. **Time to Resolution**: How long to fix critical issues
4. **Recurring Issues**: Which antipatterns appear most frequently
5. **Test Coverage**: Track coverage percentage over time

### Sample Dashboard

Create a dashboard to visualize code review metrics:

```python
import pandas as pd
import plotly.express as px

# Load review history
reviews = pd.read_csv('code_reviews.csv')

# Plot score distribution
fig = px.histogram(reviews, x='score', nbins=20, 
                   title='Code Review Score Distribution')
fig.show()

# Plot issue severity over time
severity_counts = reviews.groupby(['date', 'severity']).size().reset_index()
fig = px.line(severity_counts, x='date', y=0, color='severity',
              title='Issue Severity Trends')
fig.show()
```

---

## 🎓 Best Practices

### 1. **Use Deep Review for Critical Code**
- Core strategy logic (signal generation, portfolio optimization)
- API endpoints handling financial data
- Database migrations or schema changes
- Security-sensitive code (authentication, API key handling)

### 2. **Use Quick Review for Non-Critical Code**
- Documentation updates
- Configuration changes
- Dashboard styling/UI tweaks
- Minor bug fixes

### 3. **Review Your Own Code**
Before submitting a PR, run the code review system on your own changes:
- Catch issues early
- Learn from feedback
- Improve code quality proactively

### 4. **Keep Reference Files Updated**
As your platform evolves, update the reference files:
- Add new antipatterns as you discover them
- Update coding standards for new technologies
- Refine quality gates based on production incidents

### 5. **Combine Automated and Manual Review**
- Automated tools catch syntax and style issues
- AI review catches logical and architectural issues
- Human review catches domain-specific and business logic issues

---

## 🔗 Additional Resources

### For Python Development
- [PEP 8 Style Guide](https://pep8.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Effective Python](https://effectivepython.com/)

### For TypeScript/React Development
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [React Best Practices](https://react.dev/learn)
- [React Performance Optimization](https://react.dev/learn/render-and-commit)

### For Financial Development
- [Quantopian Lectures](https://www.quantopian.com/lectures)
- [Advances in Financial Machine Learning](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086)
- [Systematic Trading](https://www.systematictrading.org/)

### For Code Review
- [Google Engineering Practices](https://google.github.io/eng-practices/review/)
- [Code Review Best Practices](https://www.swarmia.com/blog/code-review-best-practices/)

---

## 🐛 Troubleshooting

### Issue: "Reference files not found"
**Solution**: Ensure reference files are in the correct location:
```bash
ls -la .claude/skills/code-reviewer/references/
# Should show: code_review_checklist.md, coding_standards.md, common_antipatterns.md
```

### Issue: "Too many false positives"
**Solution**: Adjust severity levels in the checklist or add exceptions for specific cases:
```markdown
### Exceptions
- `any` type allowed in legacy API integration code (to be refactored in Q2)
- Index as key allowed for static lists that never reorder
```

### Issue: "Reviews take too long"
**Solution**: Use quick review mode for non-critical changes, reserve deep review for production code.

---

## 📝 Changelog

### Version 1.0 (2024-12-28)
- Initial release
- Fixed typo in original prompt (`APIsz` → `APIs`)
- Added quantitative finance domain context
- Created three reference files (checklist, standards, antipatterns)
- Added financial correctness quality gate
- Included automated tooling references

---

## 🤝 Contributing

To improve the code review system:

1. **Report Issues**: If you find gaps or errors in the reference files
2. **Suggest Improvements**: Propose new checks or antipatterns
3. **Share Examples**: Provide real-world examples of issues caught
4. **Update Documentation**: Keep this README current as the system evolves

---

## 📄 License

This code review system is part of the potential-parakeet quantitative trading platform.

---

**Last Updated**: 2024-12-28  
**Version**: 1.0  
**Maintainer**: Development Team
