// Option 1: Frontend JavaScript solution using Yahoo Finance API directly

// Configuration
const WATCHLIST_SYMBOLS = ['RELIANCE.NS', 'TATASTEEL.NS', 'INFY.NS', 'HDFCBANK.NS', 'TCS.NS', 'WIPRO.NS'];
const UPDATE_INTERVAL = 10000; // Update every 10 seconds

// DOM Elements
const watchlistTable = document.querySelector('.watchlist-table tbody');
const statsContainer = document.querySelector('.stats-grid');
const matchesCount = document.querySelector('.matches-count span');

// Initialize the watchlist
document.addEventListener('DOMContentLoaded', function() {
    // Initial data load
    fetchStockData();
    
    // Set up interval for real-time updates
    setInterval(fetchStockData, UPDATE_INTERVAL);
    
    // Set up UI event listeners
    setupEventListeners();
});

// Fetch stock data from Yahoo Finance API
// Modify the fetchStockData function in yfin.js
// Modified fetchStockData function in yfin.js to use your backend proxy

async function fetchStockData() {
    try {
        // Show loading state
        showLoadingState(true);
        
        // Using your backend proxy
        const symbols = WATCHLIST_SYMBOLS.join(',');
        const url = `/api/stocks?symbols=${symbols}`;
        
        const response = await fetch(url);
        const data = await response.json();
        const quotes = data.quoteResponse.result;
        
        // Process the stock data
        const stockData = quotes.map(quote => {
            return {
                symbol: quote.symbol.replace('.NS', ''), // Remove .NS suffix for display
                price: quote.regularMarketPrice.toFixed(2),
                change: quote.regularMarketChange.toFixed(2),
                changePercent: quote.regularMarketChangePercent.toFixed(2),
                volume: formatNumber(quote.regularMarketVolume),
                signal: determineSignal(quote.regularMarketChangePercent)
            };
        });
        
        // Update the UI
        updateWatchlistTable(stockData);
        updateStatistics(stockData);
        
        // Update last fetched time
        matchesCount.textContent = `${stockData.length} stocks • Updated at ${new Date().toLocaleTimeString()}`;
        
        // Hide loading state
        showLoadingState(false);
        
    } catch (error) {
        console.error('Error fetching stock data:', error);
        showLoadingState(false);
        matchesCount.textContent = `Error fetching data. Retrying...`;
    }
}

// Update the watchlist table with new data
function updateWatchlistTable(stockData) {
    // Clear existing rows
    watchlistTable.innerHTML = '';
    
    // Add new rows
    stockData.forEach(stock => {
        const row = document.createElement('tr');
        
        // Determine CSS class for change values
        const changeClass = stock.change >= 0 ? 'positive' : 'negative';
        const changeSign = stock.change >= 0 ? '+' : '';
        
        // Build row HTML
        row.innerHTML = `
            <td>${stock.symbol}</td>
            <td>${stock.price}</td>
            <td class="${changeClass}">${changeSign}${stock.change} (${changeSign}${stock.changePercent}%)</td>
            <td>${stock.volume}</td>
            <td><span class="signal ${stock.signal.toLowerCase()}">${stock.signal}</span></td>
        `;
        
        watchlistTable.appendChild(row);
    });
}

// Update the statistics section with aggregated data
function updateStatistics(stockData) {
    // Calculate statistics
    const totalVolume = stockData.reduce((total, stock) => {
        return total + parseInt(stock.volume.replace(/,/g, ''));
    }, 0);
    
    const positiveStocks = stockData.filter(stock => parseFloat(stock.change) > 0);
    const negativeStocks = stockData.filter(stock => parseFloat(stock.change) < 0);
    const neutralStocks = stockData.filter(stock => parseFloat(stock.change) === 0);
    
    const longPercentage = ((positiveStocks.length / stockData.length) * 100).toFixed(2);
    const shortPercentage = ((negativeStocks.length / stockData.length) * 100).toFixed(2);
    const bothPercentage = ((neutralStocks.length / stockData.length) * 100).toFixed(2);
    
    // Calculate average returns
    const averageReturn = stockData.reduce((total, stock) => {
        return total + parseFloat(stock.changePercent);
    }, 0) / stockData.length;
    
    // Update statistics in the UI
    const stats = [
        { label: 'Long:', value: `${longPercentage}%`, class: 'positive' },
        { label: 'Short:', value: `${shortPercentage}%`, class: 'negative' },
        { label: 'Both:', value: `${bothPercentage}%`, class: 'neutral' },
        { label: 'Vol:', value: formatNumber(totalVolume), class: '' },
        { label: 'Returns:', value: `${averageReturn.toFixed(2)}%`, class: averageReturn >= 0 ? 'positive' : 'negative' }
    ];
    
    // Update stats in the UI
    updateStatsGrid(stats);
}

// Update the stats grid with new values
function updateStatsGrid(stats) {
    // Keep existing elements but update their values
    const statItems = document.querySelectorAll('.stat-item');
    
    stats.forEach((stat, index) => {
        if (statItems[index]) {
            const valueElement = statItems[index].querySelector('.stat-value');
            valueElement.textContent = stat.value;
            valueElement.className = `stat-value ${stat.class}`;
        }
    });
}

// Helper function to determine buy/sell/hold signal based on price change
function determineSignal(changePercent) {
    if (changePercent > 1.5) return 'BUY';
    if (changePercent < -1.5) return 'SELL';
    return 'HOLD';
}

// Helper function to format large numbers
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(2) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(2) + 'K';
    }
    return num.toString();
}

// Show/hide loading state
function showLoadingState(isLoading) {
    const loadingIndicator = document.querySelector('.loading-indicator') || createLoadingIndicator();
    
    if (isLoading) {
        loadingIndicator.style.display = 'flex';
    } else {
        loadingIndicator.style.display = 'none';
    }
}

// Create a loading indicator element
function createLoadingIndicator() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-indicator';
    loadingDiv.innerHTML = `
        <div class="spinner"></div>
        <p>Updating stock data...</p>
    `;
    
    // Style the loading indicator
    loadingDiv.style.cssText = `
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: rgba(10, 10, 20, 0.8);
        padding: 20px;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
        z-index: 100;
    `;
    
    document.querySelector('.watchlist').appendChild(loadingDiv);
    return loadingDiv;
}

// Setup event listeners for UI interactions
function setupEventListeners() {
    const filterButton = document.querySelector('.filter-button');
    const selectDropdown = document.querySelector('.select-dropdown');
    
    if (filterButton) {
        filterButton.addEventListener('click', () => {
            alert('Filter functionality would be implemented here');
        });
    }
    
    if (selectDropdown) {
        selectDropdown.addEventListener('change', () => {
            const view = selectDropdown.value;
            console.log(`Changed view to: ${view}`);
            // Would implement view switching logic here
        });
    }
}

// Add styles for the loading animation
function addLoadingStyles() {
    const styleSheet = document.createElement('style');
    styleSheet.textContent = `
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid rgba(255, 136, 0, 0.3);
            border-radius: 50%;
            border-top-color: var(--primary-color);
            animation: spin 1s linear infinite;
            margin-bottom: 10px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(styleSheet);
}

// Call the function to add loading styles
addLoadingStyles();
// Add this code to the existing yfin.js file to implement the ticker tape functionality
// Ticker tape functionality
function initializeTickerTape() {
    const tickerContainer = document.querySelector('.ticker-container');
    
    // Create ticker tape items based on the watchlist symbols
    WATCHLIST_SYMBOLS.forEach(symbol => {
        const tickerItem = document.createElement('div');
        tickerItem.className = 'ticker-item';
        tickerItem.innerHTML = `
            <span class="name">${symbol.replace('.NS', '')}</span>
            <span class="value">0.00</span>
            <span class="change">0.00%</span>
        `;
        tickerContainer.appendChild(tickerItem);
    });
    
    // Add a few major indices as well
    const indices = [
        { symbol: 'NIFTY', name: 'NIFTY 50' },
        { symbol: 'SENSEX', name: 'BSE SENSEX' },
        { symbol: 'BANKNIFTY', name: 'BANK NIFTY' }
    ];
    
    indices.forEach(index => {
        const tickerItem = document.createElement('div');
        tickerItem.className = 'ticker-item';
        tickerItem.innerHTML = `
            <span class="name">${index.name}</span>
            <span class="value">0.00</span>
            <span class="change">0.00%</span>
        `;
        tickerContainer.appendChild(tickerItem);
    });
    
    // Initially fetch ticker data
    updateTickerTape();
    
    // Set interval to update ticker tape
    setInterval(updateTickerTape, UPDATE_INTERVAL);
}

// Update ticker tape with live data
async function updateTickerTape() {
    try {
        // For watchlist symbols
        const symbols = WATCHLIST_SYMBOLS.join(',');
        const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${symbols}`;
        
        const response = await fetch(url, {
            headers: {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0'
            }
        });
        
        const data = await response.json();
        const quotes = data.quoteResponse.result;
        
        // Update ticker items with actual data
        quotes.forEach(quote => {
            const symbol = quote.symbol;
            const tickerItems = document.querySelectorAll('.ticker-item');
            
            tickerItems.forEach(item => {
                const nameElement = item.querySelector('.name');
                if (nameElement && nameElement.textContent === symbol.replace('.NS', '')) {
                    const valueElement = item.querySelector('.value');
                    const changeElement = item.querySelector('.change');
                    
                    valueElement.textContent = quote.regularMarketPrice.toFixed(2);
                    
                    const changePercent = quote.regularMarketChangePercent.toFixed(2);
                    const changeText = changePercent >= 0 ? 
                        `+${changePercent}%` : `${changePercent}%`;
                    
                    changeElement.textContent = changeText;
                    changeElement.className = `change ${changePercent >= 0 ? 'positive' : 'negative'}`;
                }
            });
        });
        
        // For indices - in a real implementation, you'd fetch actual index data
        // This is a simplified example using mock data
        updateIndicesMockData();
        
    } catch (error) {
        console.error('Error updating ticker tape:', error);
    }
}

// Generate mock data for indices (in a real implementation, you'd fetch actual data)
function updateIndicesMockData() {
    const indices = [
        { name: 'NIFTY 50', value: 22840.05, change: 0.67 },
        { name: 'BSE SENSEX', value: 74980.42, change: 0.58 },
        { name: 'BANK NIFTY', value: 48650.30, change: -0.24 }
    ];
    
    const tickerItems = document.querySelectorAll('.ticker-item');
    
    tickerItems.forEach(item => {
        const nameElement = item.querySelector('.name');
        
        indices.forEach(index => {
            if (nameElement && nameElement.textContent === index.name) {
                const valueElement = item.querySelector('.value');
                const changeElement = item.querySelector('.change');
                
                valueElement.textContent = index.value.toFixed(2);
                
                const changeText = index.change >= 0 ? 
                    `+${index.change}%` : `${index.change}%`;
                
                changeElement.textContent = changeText;
                changeElement.className = `change ${index.change >= 0 ? 'positive' : 'negative'}`;
            }
        });
    });
}

// Initialize the ticker tape when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize ticker tape
    initializeTickerTape();
    
});