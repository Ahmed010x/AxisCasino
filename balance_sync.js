// Universal Balance Synchronization System
// Include this script in all game pages to ensure balance consistency

(function() {
    'use strict';

    // Balance Management Functions
    window.BalanceSync = {
        // Get current balance from multiple sources
        getCurrentBalance: function() {
            // Priority: URL param > localStorage > default
            const urlParams = new URLSearchParams(window.location.search);
            const urlBalance = urlParams.get('balance');
            
            if (urlBalance && !isNaN(urlBalance)) {
                localStorage.setItem('userBalance', urlBalance);
                return parseFloat(urlBalance);
            }
            
            const storedBalance = localStorage.getItem('userBalance');
            return storedBalance ? parseFloat(storedBalance) : 1000;
        },

        // Update balance in localStorage and trigger sync
        updateBalance: function(newBalance) {
            if (isNaN(newBalance) || newBalance < 0) {
                console.warn('Invalid balance value:', newBalance);
                return false;
            }
            
            const formattedBalance = parseFloat(newBalance).toFixed(2);
            localStorage.setItem('userBalance', formattedBalance);
            
            // Trigger storage event for other tabs/windows
            window.dispatchEvent(new StorageEvent('storage', {
                key: 'userBalance',
                newValue: formattedBalance,
                storageArea: localStorage
            }));
            
            // Update display if function exists
            if (typeof updateBalanceDisplay === 'function') {
                updateBalanceDisplay();
            }
            
            return true;
        },

        // Update balance display elements
        updateDisplay: function() {
            const balance = this.getCurrentBalance();
            const elements = [
                '.balance-amount',
                '#balance',
                '#currentBalance',
                '.current-balance'
            ];
            
            elements.forEach(selector => {
                const element = document.querySelector(selector);
                if (element) {
                    element.textContent = balance.toFixed(2) + ' chips';
                }
            });
        },

        // Initialize balance sync for any page
        init: function() {
            // Update display on load
            this.updateDisplay();
            
            // Listen for storage changes from other tabs
            window.addEventListener('storage', (e) => {
                if (e.key === 'userBalance') {
                    this.updateDisplay();
                }
            });
            
            // Periodic sync every 2 seconds
            setInterval(() => {
                this.updateDisplay();
            }, 2000);
        },

        // Generate navigation URL with current balance
        getNavigationUrl: function(baseUrl, additionalParams = {}) {
            const balance = this.getCurrentBalance();
            const userId = localStorage.getItem('userId') || 'guest_' + Date.now();
            const userName = localStorage.getItem('userName') || 'Player';
            const demo = localStorage.getItem('demoMode') === 'true' ? '1' : '0';
            
            const params = new URLSearchParams({
                user_id: userId,
                user_name: userName,
                balance: balance.toFixed(2),
                demo: demo,
                ...additionalParams
            });
            
            return `${baseUrl}?${params.toString()}`;
        }
    };

    // Universal balance sync for all casino games and main webapp
    // Requires: user_id must be available in localStorage or as a global JS variable

    const API_BASE = window.location.origin;

    function getUserId() {
        // Try to get user_id from localStorage, query string, or global variable
        let userId = localStorage.getItem('user_id');
        if (!userId) {
            const params = new URLSearchParams(window.location.search);
            userId = params.get('user_id');
        }
        if (!userId && window.USER_ID) userId = window.USER_ID;
        return userId;
    }

    async function fetchBalance() {
        const userId = getUserId();
        if (!userId) return null;
        try {
            const res = await fetch(`${API_BASE}/api/balance?user_id=${userId}`);
            const data = await res.json();
            if (data.balance !== undefined) {
                localStorage.setItem('balance', data.balance);
                return data.balance;
            }
        } catch (e) {
            // Optionally show error
        }
        return null;
    }

    async function updateBalance(amount) {
        const userId = getUserId();
        if (!userId) return null;
        try {
            const res = await fetch(`${API_BASE}/api/update_balance`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, amount })
            });
            const data = await res.json();
            if (data.balance !== undefined) {
                localStorage.setItem('balance', data.balance);
                return data.balance;
            }
        } catch (e) {
            // Optionally show error
        }
        return null;
    }

    function syncBalanceUI(selector = '.balance-amount') {
        const balance = localStorage.getItem('balance');
        document.querySelectorAll(selector).forEach(el => {
            if (balance !== null) el.textContent = `${balance} chips`;
        });
    }

    // Listen for balance changes in other tabs
    window.addEventListener('storage', (e) => {
        if (e.key === 'balance') {
            syncBalanceUI();
        }
    });

    // On page load, fetch and sync balance
    (async () => {
        const balance = await fetchBalance();
        if (balance !== null) syncBalanceUI();
    })();

    // Export for use in games
    window.fetchBalance = fetchBalance;
    window.updateBalance = updateBalance;
    window.syncBalanceUI = syncBalanceUI;

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.BalanceSync.init();
        });
    } else {
        window.BalanceSync.init();
    }

})();
