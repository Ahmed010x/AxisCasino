// Universal Balance Sync for Casino WebApp & Games
// This file ensures balance consistency across all games and main webapp
// Enhanced version with real-time sync and comprehensive coverage

(function() {
    'use strict';
    
    const API_BASE = window.location.origin;
    let syncInProgress = false;
    let lastKnownBalance = null;
    
    // Get user ID from URL parameters or localStorage
    function getUserId() {
        const urlParams = new URLSearchParams(window.location.search);
        const userId = urlParams.get('user_id') || localStorage.getItem('user_id');
        if (userId) {
            localStorage.setItem('user_id', userId);
        }
        return userId;
    }
    
    // Fetch balance from backend API with retry logic
    async function fetchBalance(retries = 3) {
        const userId = getUserId();
        if (!userId) {
            console.warn('No user_id available for balance fetch');
            return null;
        }
        
        for (let i = 0; i < retries; i++) {
            try {
                const response = await fetch(`${API_BASE}/api/balance?user_id=${userId}`, {
                    method: 'GET',
                    headers: {
                        'Cache-Control': 'no-cache'
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.balance !== undefined) {
                    lastKnownBalance = data.balance;
                    localStorage.setItem('balance', data.balance.toString());
                    syncBalanceUI();
                    broadcastBalanceChange(data.balance);
                    return data.balance;
                }
            } catch (error) {
                console.warn(`Balance fetch attempt ${i + 1} failed:`, error);
                if (i === retries - 1) {
                    console.error('All balance fetch attempts failed:', error);
                }
            }
        }
        return null;
    }
    
    // Update balance via backend API with atomic transaction
    async function updateBalance(amount, retries = 3) {
        if (syncInProgress) {
            console.warn('Balance sync already in progress, queuing...');
            await new Promise(resolve => setTimeout(resolve, 100));
            return updateBalance(amount, retries);
        }
        
        syncInProgress = true;
        const userId = getUserId();
        
        if (!userId) {
            console.warn('No user_id available for balance update');
            syncInProgress = false;
            return null;
        }
        
        for (let i = 0; i < retries; i++) {
            try {
                const response = await fetch(`${API_BASE}/api/update_balance`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        user_id: parseInt(userId),
                        amount: parseInt(amount)
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.balance !== undefined) {
                    lastKnownBalance = data.balance;
                    localStorage.setItem('balance', data.balance.toString());
                    syncBalanceUI();
                    broadcastBalanceChange(data.balance);
                    syncInProgress = false;
                    return data.balance;
                } else if (data.error) {
                    console.error('Balance update error:', data.error);
                    syncInProgress = false;
                    return null;
                }
            } catch (error) {
                console.warn(`Balance update attempt ${i + 1} failed:`, error);
                if (i === retries - 1) {
                    console.error('All balance update attempts failed:', error);
                    syncInProgress = false;
                    return null;
                }
            }
        }
        
        syncInProgress = false;
        return null;
    }
    
    // Broadcast balance changes to all tabs
    function broadcastBalanceChange(balance) {
        // Use BroadcastChannel for modern browsers
        if (window.BroadcastChannel) {
            const channel = new BroadcastChannel('casino_balance');
            channel.postMessage({ type: 'balance_update', balance: balance });
        }
        
        // Fallback: trigger storage event manually
        window.dispatchEvent(new StorageEvent('storage', {
            key: 'balance',
            newValue: balance.toString(),
            storageArea: localStorage
        }));
    }
    
    // Sync balance to all UI elements comprehensively
    function syncBalanceUI() {
        const balance = localStorage.getItem('balance') || lastKnownBalance || '1000';
        
        // Update all common balance selectors
        const selectors = [
            '.balance-amount', '.balance', '#balance', '#currentBalance', 
            '#userBalance', '#balanceAmount', '.user-balance', '.current-balance'
        ];
        
        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                if (element) {
                    element.textContent = balance;
                }
            });
        });
        
        // Update any data attributes
        document.querySelectorAll('[data-balance]').forEach(element => {
            element.setAttribute('data-balance', balance);
        });
        
        // Update global variables if they exist
        if (typeof window.currentBalance !== 'undefined') {
            window.currentBalance = parseInt(balance);
        }
        if (typeof window.userBalance !== 'undefined') {
            window.userBalance = parseInt(balance);
        }
        if (typeof window.balance !== 'undefined') {
            window.balance = parseInt(balance);
        }
    }
    
    // Listen for balance changes from other tabs/windows
    window.addEventListener('storage', function(e) {
        if (e.key === 'balance' && e.newValue !== lastKnownBalance) {
            lastKnownBalance = parseInt(e.newValue);
            syncBalanceUI();
        }
    });
    
    // Listen for BroadcastChannel messages
    if (window.BroadcastChannel) {
        const channel = new BroadcastChannel('casino_balance');
        channel.addEventListener('message', function(e) {
            if (e.data.type === 'balance_update' && e.data.balance !== lastKnownBalance) {
                lastKnownBalance = e.data.balance;
                localStorage.setItem('balance', e.data.balance.toString());
                syncBalanceUI();
            }
        });
    }
    
    // Periodic balance sync (every 30 seconds)
    let syncInterval;
    function startPeriodicSync() {
        if (syncInterval) clearInterval(syncInterval);
        syncInterval = setInterval(async () => {
            try {
                await fetchBalance();
            } catch (error) {
                console.warn('Periodic sync failed:', error);
            }
        }, 30000);
    }
    
    function stopPeriodicSync() {
        if (syncInterval) {
            clearInterval(syncInterval);
            syncInterval = null;
        }
    }
    
    // Initialize on page load
    async function initialize() {
        try {
            await fetchBalance();
            syncBalanceUI();
            startPeriodicSync();
        } catch (error) {
            console.error('Balance sync initialization failed:', error);
            // Fallback to localStorage
            const storedBalance = localStorage.getItem('balance');
            if (storedBalance) {
                lastKnownBalance = parseInt(storedBalance);
                syncBalanceUI();
            }
        }
        
        // Stop periodic sync when page is hidden
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                stopPeriodicSync();
            } else {
                startPeriodicSync();
            }
        });
    }
    
    // Enhanced BalanceSync API for backward compatibility and new features
    window.BalanceSync = {
        getCurrentBalance: function() {
            const balance = localStorage.getItem('balance') || lastKnownBalance || '1000';
            return parseInt(balance);
        },
        
        setBalance: function(newBalance) {
            return updateBalance(newBalance - this.getCurrentBalance());
        },
        
        addBalance: function(amount) {
            return updateBalance(amount);
        },
        
        deductBalance: function(amount) {
            return updateBalance(-amount);
        },
        
        refresh: function() {
            return fetchBalance();
        },
        
        updateDisplay: function() {
            syncBalanceUI();
        },
        
        init: function() {
            return initialize();
        },
        
        getNavigationUrl: function(baseUrl, additionalParams = {}) {
            const balance = this.getCurrentBalance();
            const userId = getUserId() || 'guest_' + Date.now();
            const userName = localStorage.getItem('userName') || 'Player';
            const demo = localStorage.getItem('demoMode') === 'true' ? '1' : '0';
            
            const params = new URLSearchParams({
                user_id: userId,
                user_name: userName,
                balance: balance.toString(),
                demo: demo,
                ...additionalParams
            });
            
            return `${baseUrl}?${params.toString()}`;
        },
        
        // Real-time sync status
        isSyncing: function() {
            return syncInProgress;
        },
        
        getLastKnownBalance: function() {
            return lastKnownBalance;
        }
    };
    
    // Expose global functions for legacy compatibility
    window.fetchBalance = fetchBalance;
    window.updateBalance = updateBalance;
    window.syncBalanceUI = syncBalanceUI;
    window.getUserId = getUserId;
    
    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
    
})();