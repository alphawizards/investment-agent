# React Frontend Fix Guide

**Date:** January 3, 2026  
**Objective:** Fix 7 TypeScript compilation errors and Vite host checking issue  
**Estimated Time:** 15-20 minutes

---

## 🎯 Overview

There are **7 TypeScript errors** (unused variables/imports) and **1 Vite configuration issue** blocking production build.

### Error Summary:
1. `Dashboard.tsx` - `summaryLoading` declared but never used
2. `TradeTable.tsx` - `useState` imported but never used
3. `TradeTable.tsx` - `TradeFilters` type imported but never used
4. `AlphaMatrix.tsx` - `Filter` icon imported but never used
5. `DrawdownChart.tsx` - `label` parameter unused in CustomTooltip
6. `RegimeChart.tsx` - `label` parameter unused in CustomTooltip
7. `useMetrics.ts` - `PortfolioMetrics` type imported but never used

---

## 📋 Prerequisites

```bash
cd /home/ubuntu/potential-parakeet/dashboard
```

---

## 🔧 Fix #1: Dashboard.tsx - Remove unused summaryLoading

**File:** `src/components/layout/Dashboard.tsx`  
**Line:** 38  
**Error:** `'summaryLoading' is declared but its value is never read`

### Option A: Remove the variable (if not needed)

```bash
# Edit line 38
# FROM:
const { summary, loading: summaryLoading } = useDashboard(100000);

# TO:
const { summary } = useDashboard(100000);
```

### Option B: Use the variable (if loading state is needed)

```bash
# Keep the variable and use it in the JSX
# Add this near the metrics section:
{summaryLoading && <div>Loading summary...</div>}
```

### Command:
```bash
sed -i 's/const { summary, loading: summaryLoading } = useDashboard(100000);/const { summary } = useDashboard(100000);/' src/components/layout/Dashboard.tsx
```

---

## 🔧 Fix #2: TradeTable.tsx - Remove unused useState

**File:** `src/components/trades/TradeTable.tsx`  
**Line:** 7  
**Error:** `'useState' is declared but its value is never read`

### Solution: Remove unused import

```bash
# Edit line 7
# FROM:
import React, { useState } from 'react';

# TO:
import React from 'react';
```

### Command:
```bash
sed -i "s/import React, { useState } from 'react';/import React from 'react';/" src/components/trades/TradeTable.tsx
```

---

## 🔧 Fix #3: TradeTable.tsx - Remove unused TradeFilters type

**File:** `src/components/trades/TradeTable.tsx`  
**Line:** 9  
**Error:** `'TradeFilters' is declared but never used`

### Solution: Remove from import

```bash
# Edit line 9
# FROM:
import type { Trade, TradeFilters } from '../../types/trade';

# TO:
import type { Trade } from '../../types/trade';
```

### Command:
```bash
sed -i "s/import type { Trade, TradeFilters } from '..\/..\/types\/trade';/import type { Trade } from '..\/..\/types\/trade';/" src/components/trades/TradeTable.tsx
```

---

## 🔧 Fix #4: AlphaMatrix.tsx - Remove unused Filter icon

**File:** `src/components/truth-engine/AlphaMatrix.tsx`  
**Line:** 20  
**Error:** `'Filter' is declared but its value is never read`

### Solution: Remove from import

```bash
# Edit line 20
# FROM:
import { ArrowUpDown, ChevronUp, ChevronDown, Filter, Search } from 'lucide-react';

# TO:
import { ArrowUpDown, ChevronUp, ChevronDown, Search } from 'lucide-react';
```

### Command:
```bash
sed -i "s/import { ArrowUpDown, ChevronUp, ChevronDown, Filter, Search } from 'lucide-react';/import { ArrowUpDown, ChevronUp, ChevronDown, Search } from 'lucide-react';/" src/components/truth-engine/AlphaMatrix.tsx
```

---

## 🔧 Fix #5: DrawdownChart.tsx - Remove unused label parameter

**File:** `src/components/truth-engine/DrawdownChart.tsx`  
**Line:** 27  
**Error:** `'label' is declared but its value is never read`

### Solution: Remove unused parameter or prefix with underscore

```bash
# Edit line 27
# FROM:
const CustomTooltip = ({ active, payload, label }: any) => {

# TO:
const CustomTooltip = ({ active, payload }: any) => {
```

### Command:
```bash
sed -i 's/const CustomTooltip = ({ active, payload, label }: any) => {/const CustomTooltip = ({ active, payload }: any) => {/' src/components/truth-engine/DrawdownChart.tsx
```

---

## 🔧 Fix #6: RegimeChart.tsx - Remove unused label parameter

**File:** `src/components/truth-engine/RegimeChart.tsx`  
**Line:** 71  
**Error:** `'label' is declared but its value is never read`

### Solution: Remove unused parameter

```bash
# Edit line 71
# FROM:
const CustomTooltip = ({ active, payload, label }: any) => {

# TO:
const CustomTooltip = ({ active, payload }: any) => {
```

### Command:
```bash
sed -i 's/const CustomTooltip = ({ active, payload, label }: any) => {/const CustomTooltip = ({ active, payload }: any) => {/' src/components/truth-engine/RegimeChart.tsx
```

---

## 🔧 Fix #7: useMetrics.ts - Remove unused PortfolioMetrics type

**File:** `src/hooks/useMetrics.ts`  
**Line:** 8  
**Error:** `'PortfolioMetrics' is declared but never used`

### Solution: Remove from import

```bash
# Edit line 8
# FROM:
import type { Trade, PortfolioMetrics } from '../types/trade';

# TO:
import type { Trade } from '../types/trade';
```

### Command:
```bash
sed -i "s/import type { Trade, PortfolioMetrics } from '..\/types\/trade';/import type { Trade } from '..\/types\/trade';/" src/hooks/useMetrics.ts
```

---

## 🔧 Fix #8: Vite Host Checking Issue

**File:** `vite.config.ts`  
**Issue:** Vite dev server blocks proxied domain requests

### Solution: Update server configuration

The configuration has already been updated with `allowedHosts: 'all'`, but for production deployment, you should build the app instead of using the dev server.

**Current config (already applied):**
```typescript
server: {
  port: 3000,
  host: '0.0.0.0',
  allowedHosts: 'all',  // ✅ Already added
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

**For production, use the build command instead:**
```bash
npm run build
# This creates a production bundle in dist/ that can be served by nginx or the backend
```

---

## 🚀 Complete Fix Script

Run all fixes at once:

```bash
#!/bin/bash
cd /home/ubuntu/potential-parakeet/dashboard

echo "🔧 Fixing TypeScript errors..."

# Fix 1: Dashboard.tsx - Remove summaryLoading
sed -i 's/const { summary, loading: summaryLoading } = useDashboard(100000);/const { summary } = useDashboard(100000);/' src/components/layout/Dashboard.tsx

# Fix 2: TradeTable.tsx - Remove useState
sed -i "s/import React, { useState } from 'react';/import React from 'react';/" src/components/trades/TradeTable.tsx

# Fix 3: TradeTable.tsx - Remove TradeFilters
sed -i "s/import type { Trade, TradeFilters } from '..\/..\/types\/trade';/import type { Trade } from '..\/..\/types\/trade';/" src/components/trades/TradeTable.tsx

# Fix 4: AlphaMatrix.tsx - Remove Filter
sed -i "s/import { ArrowUpDown, ChevronUp, ChevronDown, Filter, Search } from 'lucide-react';/import { ArrowUpDown, ChevronUp, ChevronDown, Search } from 'lucide-react';/" src/components/truth-engine/AlphaMatrix.tsx

# Fix 5: DrawdownChart.tsx - Remove label
sed -i 's/const CustomTooltip = ({ active, payload, label }: any) => {/const CustomTooltip = ({ active, payload }: any) => {/' src/components/truth-engine/DrawdownChart.tsx

# Fix 6: RegimeChart.tsx - Remove label
sed -i 's/const CustomTooltip = ({ active, payload, label }: any) => {/const CustomTooltip = ({ active, payload }: any) => {/' src/components/truth-engine/RegimeChart.tsx

# Fix 7: useMetrics.ts - Remove PortfolioMetrics
sed -i "s/import type { Trade, PortfolioMetrics } from '..\/types\/trade';/import type { Trade } from '..\/types\/trade';/" src/hooks/useMetrics.ts

echo "✅ All fixes applied!"
echo ""
echo "🧪 Testing build..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "📦 Production bundle created in dist/"
else
    echo "❌ Build failed. Check errors above."
    exit 1
fi
```

---

## 📝 Manual Fix Steps (Alternative)

If you prefer to fix manually:

### Step 1: Navigate to dashboard directory
```bash
cd /home/ubuntu/potential-parakeet/dashboard
```

### Step 2: Open each file and make the changes

1. **Dashboard.tsx** (line 38): Remove `, loading: summaryLoading`
2. **TradeTable.tsx** (line 7): Remove `, { useState }`
3. **TradeTable.tsx** (line 9): Remove `, TradeFilters`
4. **AlphaMatrix.tsx** (line 20): Remove `, Filter`
5. **DrawdownChart.tsx** (line 27): Remove `, label`
6. **RegimeChart.tsx** (line 71): Remove `, label`
7. **useMetrics.ts** (line 8): Remove `, PortfolioMetrics`

### Step 3: Test the build
```bash
npm run build
```

---

## ✅ Verification

After applying all fixes, verify the build:

```bash
cd /home/ubuntu/potential-parakeet/dashboard

# Run TypeScript compiler check
npx tsc --noEmit

# If no errors, build the production bundle
npm run build

# Check build output
ls -lh dist/

# Expected output:
# dist/
#   ├── index.html
#   ├── assets/
#   │   ├── index-[hash].js
#   │   ├── index-[hash].css
#   │   └── vendor-[hash].js
```

---

## 🚀 Deployment After Fixes

Once all fixes are applied and build succeeds:

### Option 1: Serve via Backend (FastAPI)

```python
# Add to backend/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/app", StaticFiles(directory="dashboard/dist", html=True), name="app")
```

### Option 2: Serve via Nginx

```nginx
server {
    listen 80;
    root /home/ubuntu/potential-parakeet/dashboard/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

### Option 3: Deploy to CDN

```bash
# Upload dist/ folder to S3, Vercel, Netlify, etc.
```

---

## 🎯 Expected Results

After applying all fixes:

- ✅ **0 TypeScript compilation errors**
- ✅ **Production build succeeds**
- ✅ **dist/ folder created with optimized bundle**
- ✅ **Bundle size: ~500KB (gzipped: ~150KB)**
- ✅ **Ready for production deployment**

---

## 🐛 Troubleshooting

### If build still fails:

1. **Clear cache and reinstall dependencies:**
```bash
rm -rf node_modules package-lock.json
npm install
```

2. **Check for additional errors:**
```bash
npm run build 2>&1 | tee build-errors.log
```

3. **Verify Node.js version:**
```bash
node --version  # Should be v18+ or v20+
```

4. **Check TypeScript version:**
```bash
npx tsc --version  # Should be 5.2.2
```

---

## 📊 Summary

| Issue | File | Line | Fix | Status |
|-------|------|------|-----|--------|
| Unused variable | Dashboard.tsx | 38 | Remove `summaryLoading` | ⏳ Pending |
| Unused import | TradeTable.tsx | 7 | Remove `useState` | ⏳ Pending |
| Unused type | TradeTable.tsx | 9 | Remove `TradeFilters` | ⏳ Pending |
| Unused icon | AlphaMatrix.tsx | 20 | Remove `Filter` | ⏳ Pending |
| Unused param | DrawdownChart.tsx | 27 | Remove `label` | ⏳ Pending |
| Unused param | RegimeChart.tsx | 71 | Remove `label` | ⏳ Pending |
| Unused type | useMetrics.ts | 8 | Remove `PortfolioMetrics` | ⏳ Pending |
| Vite config | vite.config.ts | 15 | Already fixed | ✅ Done |

---

## 🎓 Best Practices

To prevent these issues in the future:

1. **Enable ESLint auto-fix:**
```json
// .vscode/settings.json
{
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

2. **Use TypeScript strict mode:**
```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

3. **Run linting before commit:**
```bash
npm run lint
```

---

**Ready to apply fixes?** Run the complete fix script or follow the manual steps above.
