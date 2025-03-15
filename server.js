const express = require('express');
const axios = require('axios');
const cors = require('cors');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 3000;

// Enable CORS for all routes
app.use(cors());

// Serve static files from 'templates' directory
app.use(express.static(path.join(__dirname, 'templates')));

// Endpoint to fetch stock data
app.get('/api/stocks', async (req, res) => {
  try {
    const symbols = req.query.symbols || 'RELIANCE.NS,TATASTEEL.NS,INFY.NS,HDFCBANK.NS,TCS.NS,WIPRO.NS';
    const response = await axios.get(`https://query1.finance.yahoo.com/v7/finance/quote?symbols=${symbols}`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching stock data:', error);
    res.status(500).json({ error: 'Failed to fetch stock data' });
  }
});

// Send all non-API requests to index.html
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'templates', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Visit http://localhost:${PORT} in your browser`);
});