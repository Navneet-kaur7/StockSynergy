from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf
from datetime import datetime, timedelta
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error
import warnings
import os
import base64
from io import BytesIO
import traceback

warnings.filterwarnings('ignore')

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "your_secret_key_here"

# Default watchlist tickers - these will always be displayed
DEFAULT_WATCHLIST = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 
                  'HINDUNILVR.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'KOTAKBANK.NS']

def smape_kun(y_true, y_pred):
    """
    Calculate Symmetric Mean Absolute Percentage Error
    """
    return np.mean((np.abs(y_pred - y_true) * 200 / (np.abs(y_pred) + np.abs(y_true))))

def fetch_stock_data(ticker, start_date, end_date):
    """
    Fetch historical stock data for a given ticker using yfinance.
    """
    try:
        # Set auto_adjust explicitly to False as it changed default to True
        data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
        if data.empty:
            return None
        return data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def get_watchlist_data(tickers=None):
    
    # Use Indian stocks if no tickers are provided
    if tickers is None or len(tickers) == 0:
        # Popular Indian stocks with NSE suffix for National Stock Exchange of India
        tickers = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 
                  'HINDUNILVR.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'KOTAKBANK.NS']
    
    try:
        # Get data for the last 30 days to analyze trends
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Initialize stats counters
        stats = {
            'long': 0,
            'short': 0,
            'total': 0,
            'total_volume': 0,
            'total_return': 0
        }
        
        watchlist_data = []
        
        # Process each ticker
        for ticker in tickers:
            try:
                # Download data - explicitly set auto_adjust to False
                data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
                if data.empty:
                    continue
                
                # Calculate metrics - ensure we're extracting scalar values with float() conversion
                latest_price = float(data['Close'].iloc[-1])
                prev_price = float(data['Close'].iloc[-2])
                change = latest_price - prev_price
                change_pct = (change / prev_price) * 100
                volume = int(data['Volume'].iloc[-1])
                
                # Calculate 5-day and 20-day moving averages for signal
                data['MA5'] = data['Close'].rolling(window=5).mean()
                data['MA20'] = data['Close'].rolling(window=20).mean()
                
                # Determine signal - using scalar values for comparison
                signal = "Neutral"
                last_ma5 = float(data['MA5'].iloc[-1])
                last_ma20 = float(data['MA20'].iloc[-1])
                
                if last_ma5 > last_ma20:
                    signal = "Long"
                    stats['long'] += 1
                elif last_ma5 < last_ma20:
                    signal = "Short"
                    stats['short'] += 1
                
                # Calculate 30-day return using scalar values
                first_close = float(data['Close'].iloc[0])
                period_return = ((latest_price / first_close) - 1) * 100
                
                # Format ticker symbol - remove exchange suffix for display
                display_symbol = ticker.split('.')[0]
                
                # Add to watchlist data with ₹ symbol for Indian Rupees
                watchlist_data.append({
                    'symbol': display_symbol,
                    'ltp': f"₹{round(latest_price, 2):,.2f}",  # Format with rupee symbol and commas
                    'change': round(change_pct, 2),
                    'volume': f"{volume:,}",  # Format with commas for readability
                    'signal': signal,
                    'return': round(period_return, 2)
                })
                
                # Update stats
                stats['total'] += 1
                stats['total_volume'] += volume
                stats['total_return'] += period_return
                
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                traceback.print_exc()
                continue
        
        # Calculate percentages for stats
        if stats['total'] > 0:
            stats['long_pct'] = round((stats['long'] / stats['total']) * 100, 2)
            stats['short_pct'] = round((stats['short'] / stats['total']) * 100, 2)
            stats['both_pct'] = round(100 - stats['long_pct'] - stats['short_pct'], 2)
            stats['avg_return'] = round(stats['total_return'] / stats['total'], 2)
            stats['total_volume'] = f"{stats['total_volume']:,}"  # Format with commas
        else:
            stats['long_pct'] = 0
            stats['short_pct'] = 0
            stats['both_pct'] = 0
            stats['avg_return'] = 0
            stats['total_volume'] = 0
        
        return {
            'watchlist': watchlist_data,
            'stats': stats
        }
        
    except Exception as e:
        print(f"Error fetching watchlist data: {e}")
        traceback.print_exc()
        return {
            'watchlist': [],
            'stats': {
                'long_pct': 0,
                'short_pct': 0,
                'both_pct': 0,
                'total_volume': 0,
                'avg_return': 0
            }
        }

def analyze_and_predict_stock(ticker, start_date, end_date):
    """
    Analyze stock data and make predictions using ARIMA
    """
    try:
        data = fetch_stock_data(ticker, start_date, end_date)
        if data is None or data.empty:
            return None
        
        # Process the data
        data = data[['Close']]
        data.columns = [ticker]
        data.index = pd.to_datetime(data.index)
        
        # Create plots and save as base64 encoded strings
        results = {}
        
        # Price plot
        plt.figure(figsize=(12, 6))
        data.plot(linewidth=2, fontsize=12)
        plt.title(f"{ticker} Stock Prices")
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Price', fontsize=12)
        plt.grid(True)
        
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        results['price_plot'] = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        # Differencing plot
        plt.figure(figsize=(12, 6))
        data.diff().plot(linewidth=2, fontsize=12)
        plt.title(f"{ticker} Differencing Plot")
        plt.xlabel('Date', fontsize=12)
        plt.grid(True)
        
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        results['diff_plot'] = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        # Autocorrelation plot
        plt.figure(figsize=(8, 8))
        pd.plotting.lag_plot(data[ticker], lag=5)
        plt.title(f"{ticker} Autocorrelation Plot")
        
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        results['autocorr_plot'] = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        # Train-test split for ARIMA model
        train_data, test_data = data[0:int(len(data) * 0.8)], data[int(len(data) * 0.8):]
        train_ar = train_data[ticker].values
        test_ar = test_data[ticker].values
        
        # ARIMA prediction
        history = [x for x in train_ar]
        predictions = []
        
        for t in range(len(test_ar)):
            model = ARIMA(history, order=(5, 1, 2))
            model_fit = model.fit()
            output = model_fit.forecast()
            yhat = output[0]
            predictions.append(yhat)
            obs = test_ar[t]
            history.append(obs)
        
        # Calculate errors
        error = mean_squared_error(test_ar, predictions)
        error2 = smape_kun(test_ar, predictions)
        results['mse'] = round(error, 3)
        results['smape'] = round(error2, 3)
        
        # Plot predictions vs actual
        plt.figure(figsize=(12, 6))
        plt.plot(train_data.index, train_data[ticker], color='blue', label='Training Data')
        plt.plot(test_data.index, test_data[ticker], color='red', label='Actual Price')
        plt.plot(test_data.index, predictions, color='green', marker='o', linestyle='dashed', label='Predicted Price')
        plt.title(f"{ticker} Prices Prediction")
        plt.xlabel('Dates')
        plt.ylabel('Prices')
        plt.legend()
        plt.grid(True)
        
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        results['prediction_plot'] = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        # Future predictions
        full_history = list(data[ticker].values)
        last_date = data.index[-1]
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=10, freq='B')
        
        model = ARIMA(full_history, order=(5, 1, 2))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=10)
        
        future_df = pd.DataFrame({
            'Date': future_dates,
            'Predicted_Price': forecast
        })
        
        # Plot future predictions
        plt.figure(figsize=(12, 6))
        plt.plot(data.index[-30:], data[ticker].values[-30:], color='blue', linewidth=2, label='Historical Prices')
        plt.plot(future_df['Date'], future_df['Predicted_Price'], color='green', linewidth=2, marker='o',
                 linestyle='dashed', label='Future Predictions')
        plt.axvline(x=last_date, color='red', linestyle='--', label='Prediction Start')
        plt.title(f"{ticker} Future Price Predictions")
        plt.xlabel('Dates')
        plt.ylabel('Prices')
        plt.legend()
        plt.grid(True)
        
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        results['future_plot'] = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        # Data for display
        results['ticker'] = ticker
        results['description'] = data.describe().T.to_html(classes='table table-striped')
        results['actual_vs_predicted'] = pd.DataFrame({
            'Actual': test_ar,
            'Predicted': predictions
        }).head(10).to_html(classes='table table-striped')
        
        # Future predictions as table
        results['future_predictions'] = future_df.to_html(classes='table table-striped')
        
        return results
    except Exception as e:
        print(f"Error in analyze_and_predict_stock: {e}")
        traceback.print_exc()
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    
    watchlist_data = get_watchlist_data(DEFAULT_WATCHLIST)
    return render_template('dashboard.html', watchlist=watchlist_data['watchlist'], stats=watchlist_data['stats'])


@app.route('/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    flash("Watchlist customization is disabled", "info")
    return redirect(url_for('dashboard'))


@app.route('/remove_from_watchlist', methods=['POST'])
def remove_from_watchlist():
    flash("Watchlist customization is disabled", "info")
    return redirect(url_for('dashboard'))

@app.route('/predict', methods=['GET'])
def predict_form():
    return render_template('results.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        ticker = request.form.get('ticker')
        if not ticker:
            flash("Please enter a valid stock symbol", "error")
            return render_template('results.html', error="Please enter a valid stock symbol")
        
        # Default date range (1 year of historical data)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # Get optional date parameters
        if request.form.get('start_date'):
            start_date = request.form.get('start_date')
        if request.form.get('end_date'):
            end_date = request.form.get('end_date')
        
        ticker = ticker.strip().upper()  # Normalize ticker
        
        analysis_results = analyze_and_predict_stock(ticker, start_date, end_date)
        
        if analysis_results is None:
            flash(f"No data found for ticker {ticker}", "error")
            return render_template('results.html', error=f"No data found for ticker {ticker}")
        
        return render_template('prediction.html', results=analysis_results)
    except Exception as e:
        print(f"Error in analyze route: {e}")
        traceback.print_exc()
        flash("An error occurred while processing your request", "error")
        return render_template('results.html', error="An error occurred. Please try again.")

@app.route('/results')
def results():
    return redirect(url_for('predict_form'))

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data = request.get_json()
        ticker = data.get('ticker')
        start_date = data.get('start_date', (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        if not ticker:
            return jsonify({'error': 'Ticker symbol is required'}), 400
        
        results = analyze_and_predict_stock(ticker, start_date, end_date)
        
        if results is None:
            return jsonify({'error': f'No data found for ticker {ticker}'}), 404
        
        return jsonify(results)
    except Exception as e:
        print(f"Error in API: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500








@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/contact_process', methods=['POST'])
def contact_process():
    # Process contact form
    flash('Your message has been sent!', "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)