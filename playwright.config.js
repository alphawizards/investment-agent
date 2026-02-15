// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
    testDir: './tests/e2e',
    fullyParallel: false,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: 1,
    reporter: [
        ['html', { open: 'never' }],
        ['list']
    ],
    use: {
        baseURL: 'http://localhost:8000',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
    webServer: {
        command: 'set PYTHONIOENCODING=utf-8 && python -m backend.main',
        url: 'http://localhost:8000/',
        reuseExistingServer: true,
        timeout: 120000,
        stdout: 'ignore',
        stderr: 'ignore',
    },
});
