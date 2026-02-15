/**
 * Universe Selector Component
 * ===========================
 * Reusable component for selecting stock universes in the Quant 2.0 dashboard.
 * 
 * Usage:
 *   const selector = new UniverseSelector('container-id', {
 *       onSelect: (universe) => console.log('Selected:', universe)
 *   });
 *   await selector.init();
 */

class UniverseSelector {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = null;
        this.selectElement = null;
        this.universes = [];
        this.currentUniverse = options.defaultUniverse || localStorage.getItem('selectedUniverse') || 'SPX500';
        this.onSelect = options.onSelect || (() => { });
        this.apiBase = options.apiBase || '/api';
        this.isLoading = false;
    }

    /**
     * Initialize the selector - loads universes and renders the component
     */
    async init() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            console.error(`UniverseSelector: Container '${this.containerId}' not found`);
            return;
        }

        await this.loadUniverses();
        this.render();
        this.bindEvents();
    }

    /**
     * Load available universes from the API
     */
    async loadUniverses() {
        this.isLoading = true;

        try {
            const response = await fetch(`${this.apiBase}/universes/`);
            if (response.ok) {
                const data = await response.json();
                this.universes = data.universes || [];
                console.log('Loaded universes from API:', this.universes.length);
            } else {
                throw new Error('API unavailable');
            }
        } catch (error) {
            console.log('Using fallback universe list:', error.message);
            // Fallback universes if API unavailable
            this.universes = [
                { key: 'SPX500', name: 'S&P 500', region: 'US', ticker_count: 500 },
                { key: 'NASDAQ100', name: 'NASDAQ 100', region: 'US', ticker_count: 100 },
                { key: 'RUSSELL2000', name: 'Russell 2000', region: 'US', ticker_count: 100 },
                { key: 'US_ETFS', name: 'US ETFs', region: 'US', ticker_count: 40 },
                { key: 'ASX200', name: 'ASX 200', region: 'AU', ticker_count: 50 },
                { key: 'ASX_TOTAL', name: 'ASX Total Market', region: 'AU', ticker_count: 100 },
                { key: 'ASX_ETFS', name: 'ASX ETFs', region: 'AU', ticker_count: 25 },
                { key: 'CORE_ETFS', name: 'Core ETFs', region: 'GLOBAL', ticker_count: 15 }
            ];
        }

        this.isLoading = false;
    }

    /**
     * Render the selector component
     */
    render() {
        // Group universes by region
        const grouped = {};
        this.universes.forEach(u => {
            const region = u.region || 'Other';
            if (!grouped[region]) grouped[region] = [];
            grouped[region].push(u);
        });

        // Build select HTML
        let optionsHtml = '';
        for (const [region, universes] of Object.entries(grouped)) {
            optionsHtml += `<optgroup label="${this.getRegionLabel(region)}">`;
            universes.forEach(u => {
                const selected = u.key === this.currentUniverse ? 'selected' : '';
                optionsHtml += `<option value="${u.key}" ${selected}>${u.name} (${u.ticker_count})</option>`;
            });
            optionsHtml += '</optgroup>';
        }

        this.container.innerHTML = `
            <div class="universe-selector">
                <label for="universe-select" class="universe-label">
                    <span class="universe-icon">🌐</span>
                    Universe
                </label>
                <select id="universe-select" class="universe-select">
                    ${optionsHtml}
                </select>
                <span class="universe-info" id="universe-info"></span>
            </div>
        `;

        this.selectElement = this.container.querySelector('#universe-select');
        this.updateInfo();

        // Add styles if not already present
        this.injectStyles();
    }

    /**
     * Get human-readable region label
     */
    getRegionLabel(region) {
        const labels = {
            'US': '🇺🇸 United States',
            'AU': '🇦🇺 Australia',
            'GLOBAL': '🌍 Global'
        };
        return labels[region] || region;
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        if (!this.selectElement) return;

        this.selectElement.addEventListener('change', (e) => {
            this.setUniverse(e.target.value);
        });
    }

    /**
     * Update the info display
     */
    updateInfo() {
        const infoEl = this.container.querySelector('#universe-info');
        if (!infoEl) return;

        const universe = this.universes.find(u => u.key === this.currentUniverse);
        if (universe) {
            infoEl.textContent = `${universe.ticker_count} stocks`;
        }
    }

    /**
     * Set the current universe
     */
    setUniverse(key) {
        if (this.currentUniverse === key) return;

        this.currentUniverse = key;
        localStorage.setItem('selectedUniverse', key);

        // Update select if programmatically set
        if (this.selectElement && this.selectElement.value !== key) {
            this.selectElement.value = key;
        }

        this.updateInfo();

        // Trigger callback
        const universe = this.universes.find(u => u.key === key);
        this.onSelect(key, universe);
    }

    /**
     * Get the current universe key
     */
    getCurrentUniverse() {
        return this.currentUniverse;
    }

    /**
     * Get current universe info
     */
    getCurrentUniverseInfo() {
        return this.universes.find(u => u.key === this.currentUniverse);
    }

    /**
     * Inject CSS styles
     */
    injectStyles() {
        if (document.getElementById('universe-selector-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'universe-selector-styles';
        styles.textContent = `
            .universe-selector {
                display: flex;
                align-items: center;
                gap: 12px;
                background: var(--bg-card, #1a1a3a);
                padding: 10px 16px;
                border-radius: 10px;
                border: 1px solid var(--border, #2a2a4a);
            }

            .universe-label {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 13px;
                font-weight: 600;
                color: var(--text-secondary, #a0a0c0);
                white-space: nowrap;
            }

            .universe-icon {
                font-size: 16px;
            }

            .universe-select {
                flex: 1;
                background: var(--bg-secondary, #12122a);
                border: 1px solid var(--border, #2a2a4a);
                color: var(--text-primary, #ffffff);
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                min-width: 180px;
                transition: border-color 0.2s, box-shadow 0.2s;
            }

            .universe-select:hover {
                border-color: var(--accent, #00d4ff);
            }

            .universe-select:focus {
                outline: none;
                border-color: var(--accent, #00d4ff);
                box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.2);
            }

            .universe-select option {
                background: var(--bg-secondary, #12122a);
                color: var(--text-primary, #ffffff);
                padding: 8px;
            }

            .universe-select optgroup {
                font-weight: 600;
                color: var(--accent, #00d4ff);
            }

            .universe-info {
                font-size: 12px;
                color: var(--text-secondary, #a0a0c0);
                white-space: nowrap;
            }

            /* Responsive */
            @media (max-width: 768px) {
                .universe-selector {
                    flex-wrap: wrap;
                }
                
                .universe-select {
                    min-width: 140px;
                }
            }
        `;
        document.head.appendChild(styles);
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UniverseSelector;
}
