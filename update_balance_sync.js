// Universal balance update script to replace legacy balance code with sync API
// This script contains the replacement logic for all games

// Standard balance sync implementation for all games
const UNIVERSAL_BALANCE_SYNC = `
// Universal balance functions using balance_sync.js
async function updateBalance(amount) {
    const newBalance = await window.updateBalance(amount);
    if (newBalance !== null) {
        currentBalance = newBalance;
        updateBalanceDisplay();
        return newBalance;
    }
    return currentBalance;
}

function updateBalanceDisplay() {
    window.syncBalanceUI();
    const balance = window.BalanceSync.getCurrentBalance();
    currentBalance = balance;
    
    // Update all balance displays
    const balanceElements = document.querySelectorAll('.balance-amount, #balance, #currentBalance, #userBalance');
    balanceElements.forEach(el => {
        if (el) el.textContent = balance;
    });
}

async function initializeBalance() {
    await window.fetchBalance();
    currentBalance = window.BalanceSync.getCurrentBalance();
    updateBalanceDisplay();
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    if (window.BalanceSync) {
        initializeBalance();
    }
});
`;

console.log('Universal balance sync code template ready');
console.log('Use this code to replace balance functions in all game files');
