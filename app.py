from flask import Flask, render_template, request, jsonify
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

warnings.filterwarnings('ignore')

app = Flask(__name__, template_folder='templates', static_folder='static')

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
        data = yf.download(ticker, start=start_date, end=end_date)
        if data.empty:
            return None
        return data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def analyze_and_predict_stock(ticker, start_date, end_date):
    """
    Analyze stock data and make predictions using ARIMA
    """
    data = fetch_stock_data(ticker, start_date, end_date)
    if data is None:
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
    results['description'] = data.describe().T.to_html()
    results['actual_vs_predicted'] = pd.DataFrame({
        'Actual': test_ar,
        'Predicted': predictions
    }).head(10).to_html(classes='table table-striped')
    
    # Future predictions as table
    results['future_predictions'] = future_df.to_html(classes='table table-striped')
    
    return results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/results', methods=['GET', 'POST'])
def results():
    if request.method == 'POST':
        ticker = request.form.get('ticker')
        if not ticker:
            return render_template('results.html', error="Please enter a stock symbol")
        
        # Default date range (1 year of historical data)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        analysis_results = analyze_and_predict_stock(ticker, start_date, end_date)
        
        if analysis_results is None:
            return render_template('results.html', error=f"No data found for ticker {ticker}")
        
        return render_template('prediction_results.html', results=analysis_results)
    
    return render_template('results.html')

@app.route('/api/predict', methods=['POST'])
def api_predict():
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

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)