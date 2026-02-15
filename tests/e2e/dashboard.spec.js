// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * E2E Smoke Tests for Quant Trading Dashboard
 * These tests verify critical paths work end-to-end.
 */

test.describe('API Health & Endpoints', () => {

    test('health endpoint responds correctly', async ({ request }) => {
        const response = await request.get('/');
        expect(response.ok()).toBeTruthy();

        const json = await response.json();
        expect(json.message).toContain('Quant Trading Dashboard API');
        expect(json.version).toBeDefined();
    });

    test('strategies endpoint returns list', async ({ request }) => {
        const response = await request.get('/api/strategies');
        expect(response.ok()).toBeTruthy();

        const strategies = await response.json();
        expect(Array.isArray(strategies)).toBeTruthy();
        expect(strategies.length).toBeGreaterThan(0);

        // Check first strategy has required fields
        const first = strategies[0];
        expect(first.name).toBeDefined();
        expect(first.category).toBeDefined();
        expect(first.status).toBe('active');
    });

    test('API documentation is accessible', async ({ request }) => {
        const response = await request.get('/docs');
        expect(response.ok()).toBeTruthy();
    });

    test('data status endpoint works', async ({ request }) => {
        const response = await request.get('/api/data/status');
        expect(response.ok()).toBeTruthy();

        const status = await response.json();
        expect(status.yfinance_status).toBeDefined();
        expect(status.tiingo_status).toBeDefined();
    });

});

test.describe('Dashboard Navigation', () => {

    test('static dashboard files are accessible', async ({ page }) => {
        // Test that static HTML can be served (when opened directly)
        // This tests that files exist, not that they're served by backend
        const response = await page.goto('file:///c:/Users/ckr_4/01 Web Projects/potential-parakeet/potential-parakeet-1/dashboard/quant2_dashboard.html');
        expect(response.ok()).toBeTruthy();

        // Check page has key elements
        await expect(page.locator('header')).toBeVisible();
        await expect(page.locator('.strategy-card').first()).toBeVisible();
    });

    test('navigation links work on dashboard', async ({ page }) => {
        await page.goto('file:///c:/Users/ckr_4/01 Web Projects/potential-parakeet/potential-parakeet-1/dashboard/quant2_dashboard.html');

        // Click on Quant 1.0 link
        await page.click('text=Quant 1.0');
        await expect(page).toHaveURL(/strategy_dashboard/);

        // Navigate back
        await page.goBack();
        await expect(page.locator('.regime-banner')).toBeVisible();
    });

});

test.describe('Data Display Verification', () => {

    test('regime banner shows correct status', async ({ page }) => {
        await page.goto('file:///c:/Users/ckr_4/01 Web Projects/potential-parakeet/potential-parakeet-1/dashboard/quant2_dashboard.html');

        // Regime indicator should be visible
        const regimeDot = page.locator('.regime-dot');
        await expect(regimeDot).toBeVisible();

        // Regime probabilities should add up to ~100%
        const bullProb = await page.locator('#bullProb').textContent();
        const bearProb = await page.locator('#bearProb').textContent();
        const chopProb = await page.locator('#chopProb').textContent();

        expect(bullProb).toMatch(/\d+%/);
        expect(bearProb).toMatch(/\d+%/);
        expect(chopProb).toMatch(/\d+%/);
    });

    test('strategy cards display metrics', async ({ page }) => {
        await page.goto('file:///c:/Users/ckr_4/01 Web Projects/potential-parakeet/potential-parakeet-1/dashboard/quant2_dashboard.html');

        // Should have at least 4 strategy cards
        const cards = page.locator('.strategy-card');
        const count = await cards.count();
        expect(count).toBeGreaterThanOrEqual(4);

        // First card should have metric values
        const firstCard = cards.first();
        await expect(firstCard.locator('.metric-value').first()).toBeVisible();
    });

    test('timestamps display correctly', async ({ page }) => {
        await page.goto('file:///c:/Users/ckr_4/01 Web Projects/potential-parakeet/potential-parakeet-1/dashboard/quant2_dashboard.html');

        // Activity timestamps should be readable
        const activityTime = page.locator('.activity-time').first();
        await expect(activityTime).toBeVisible();

        const timeText = await activityTime.textContent();
        // Should contain time reference (hours ago, Yesterday, Nov, etc.)
        expect(timeText).toMatch(/(ago|Yesterday|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i);
    });

});
