"""
Enhanced Flask API Server with Real-time Streaming
Streams coin results as they're analyzed (no waiting for complete scan)
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import sys
import os
import json
import glob
from datetime import datetime
import threading
import time
import queue

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crypto_ema_scanner import CryptoEMAScanner
from multi_timeframe_scanner import MultiTimeframeEMAScanner

app = Flask(__name__)
CORS(app)

# Global state
scan_status = {
    'running': False,
    'progress': 0,
    'total': 0,
    'current_coin': '',
    'status_message': 'Ready',
    'start_time': None,
    'error': None
}

# Queue for streaming results
results_queue = queue.Queue()
active_streams = []

def run_scan_thread(top_n, use_cache):
    """Run scan in background thread"""
    global scan_status
    
    try:
        scan_status['running'] = True
        scan_status['progress'] = 0
        scan_status['total'] = top_n
        scan_status['status_message'] = 'Initializing scanner...'
        scan_status['start_time'] = datetime.now().isoformat()
        scan_status['error'] = None
        
        scanner = CryptoEMAScanner(
            cmc_api_key=None,
            top_n=top_n,
            cache_duration_minutes=60 if use_cache else 0
        )
        
        # Check for cached data first
        if use_cache:
            cached = scanner.get_recent_scan()
            if cached:
                scan_status['running'] = False
                scan_status['progress'] = top_n
                scan_status['status_message'] = 'Loaded from cache'
                return
        
        # Fetch coins
        scan_status['status_message'] = 'Fetching top coins...'
        coins = scanner.get_top_n_coins()
        
        scan_status['total'] = len(coins)
        scan_status['status_message'] = 'Analyzing coins...'
        
        all_results = []
        for i, coin in enumerate(coins, 1):
            scan_status['progress'] = i
            scan_status['current_coin'] = f"{coin['name']} ({coin['symbol']})"
            
            results = scanner.analyze_coin_all_timeframes(coin)
            
            coin_result = {
                'coin_info': coin,
                'weekly': results['weekly'],
                'daily': results['daily'],
                '4h': results['4h']
            }
            all_results.append(coin_result)
            
            # Stream this result immediately
            stream_data = {
                'type': 'coin_result',
                'data': coin_result,
                'progress': i,
                'total': len(coins)
            }
            results_queue.put(stream_data)
            
            time.sleep(0.5)
        
        # Categorize and save
        scan_status['status_message'] = 'Processing results...'
        (results_above_weekly, results_below_weekly, 
         results_above_daily, results_below_daily, 
         results_4h, failed_coins) = scanner.categorize_results(all_results)
        
        scanner.save_results(results_above_weekly, results_below_weekly,
                           results_above_daily, results_below_daily, 
                           results_4h, failed_coins)
        
        # Stream completion
        results_queue.put({
            'type': 'complete',
            'message': 'Scan completed successfully'
        })
        
        scan_status['running'] = False
        scan_status['status_message'] = 'Scan completed successfully'
        
    except Exception as e:
        scan_status['running'] = False
        scan_status['error'] = str(e)
        scan_status['status_message'] = f'Error: {str(e)}'
        results_queue.put({
            'type': 'error',
            'error': str(e)
        })

@app.route('/api/status')
def get_status():
    """Get current scan status"""
    return jsonify(scan_status)

@app.route('/api/scan', methods=['POST'])
def start_scan():
    """Start a new scan"""
    global scan_status
    
    if scan_status['running']:
        return jsonify({'error': 'Scan already in progress'}), 400
    
    data = request.json
    top_n = data.get('top_n', 10)
    use_cache = data.get('use_cache', True)
    
    # Clear queue
    while not results_queue.empty():
        results_queue.get()
    
    # Start scan in background thread
    thread = threading.Thread(target=run_scan_thread, args=(top_n, use_cache))
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Scan started', 'top_n': top_n})

@app.route('/api/stream')
def stream_results():
    """Server-Sent Events stream for real-time results"""
    def event_stream():
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"
        
        while True:
            try:
                # Get result from queue (timeout to allow checking if scan is done)
                result = results_queue.get(timeout=1)
                yield f"data: {json.dumps(result)}\n\n"
                
                # If scan complete, close stream
                if result.get('type') == 'complete' or result.get('type') == 'error':
                    break
                    
            except queue.Empty:
                # Send heartbeat to keep connection alive
                if not scan_status['running']:
                    break
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/api/results/latest')
def get_latest_results():
    """Get latest scan results"""
    try:
        pattern = 'crypto_ema_scan_top*_*.json'
        files = glob.glob(pattern)
        
        if not files:
            return jsonify({'error': 'No scan results found'}), 404
        
        latest_file = max(files, key=os.path.getctime)
        
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/results/list')
def list_results():
    """List all available scan results"""
    try:
        pattern = 'crypto_ema_scan_top*_*.json'
        files = glob.glob(pattern)
        
        results = []
        for file in files:
            stat = os.stat(file)
            results.append({
                'filename': file,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'size': stat.st_size
            })
        
        results.sort(key=lambda x: x['created'], reverse=True)
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/demo')
def run_demo():
    """Run demo scan with simulated data"""
    try:
        from demo_scanner import CryptoEMAScannerDemo
        
        demo = CryptoEMAScannerDemo()
        
        all_results = []
        for coin in demo.demo_coins:
            results = demo.generate_demo_analysis(coin)
            all_results.append({
                'coin_info': coin,
                'weekly': results['weekly'],
                'daily': results['daily'],
                '4h': results['4h']
            })
        
        (results_above_weekly, results_below_weekly, 
         _, _, results_4h, _) = demo.categorize_results(all_results)
        
        coins_to_evaluate, coins_to_avoid, coins_to_trade_now = demo.generate_strategic_summary(
            results_above_weekly, results_below_weekly, results_4h
        )
        
        return jsonify({
            'scan_date': datetime.now().isoformat(),
            'top_n': len(demo.demo_coins),
            'coins_above_weekly_ema50': results_above_weekly,
            'coins_below_weekly_ema50': results_below_weekly,
            'coins_4h_ema50': results_4h,
            'strategic_summary': {
                'coins_to_evaluate_long_term': coins_to_evaluate,
                'coins_to_trade_now_short_term': coins_to_trade_now,
                'coins_to_avoid': coins_to_avoid
            },
            'summary': {
                'total_scanned': len(demo.demo_coins),
                'total_above_weekly': len(results_above_weekly),
                'total_below_weekly': len(results_below_weekly),
                'total_4h_analyzed': len(results_4h),
                'total_to_evaluate': len(coins_to_evaluate),
                'total_to_trade_now': len(coins_to_trade_now),
                'total_to_avoid': len(coins_to_avoid)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan/multi', methods=['POST'])
def start_multi_scan():
    """Start a multi-timeframe scan"""
    global scan_status
    
    if scan_status['running']:
        return jsonify({'error': 'Scan already in progress'}), 400
    
    data = request.json
    top_n = data.get('top_n', 10)
    
    def run_multi_scan():
        global scan_status
        try:
            scan_status['running'] = True
            scan_status['status_message'] = 'Running multi-timeframe scan...'
            
            scanner = MultiTimeframeEMAScanner(top_n=top_n, cache_duration_minutes=0)
            all_results = scanner.scan_all_coins()
            scanner.save_results(all_results)
            
            scan_status['running'] = False
            scan_status['status_message'] = 'Multi-timeframe scan completed'
        except Exception as e:
            scan_status['running'] = False
            scan_status['error'] = str(e)
            scan_status['status_message'] = f'Error: {str(e)}'
    
    thread = threading.Thread(target=run_multi_scan)
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Multi-timeframe scan started', 'top_n': top_n})

@app.route('/api/results/multi/latest')
def get_latest_multi_results():
    """Get latest multi-timeframe scan results"""
    try:
        pattern = 'crypto_ema_multi_scan_top*_*.json'
        files = glob.glob(pattern)
        
        if not files:
            return jsonify({'error': 'No multi-timeframe scan results found'}), 404
        
        latest_file = max(files, key=os.path.getctime)
        
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Starting Enhanced Crypto Scanner API Server...")
    print("📡 API available at: http://localhost:5001")
    print("📊 Real-time streaming enabled!")
    print("\nEndpoints:")
    print("  GET  /api/status          - Get scan status")
    print("  POST /api/scan            - Start new scan")
    print("  GET  /api/stream          - Real-time results stream (SSE)")
    print("  GET  /api/results/latest  - Get latest results")
    print("  GET  /api/results/list    - List all results")
    print("  GET  /api/demo            - Run demo scan")
    print("  GET  /health              - Health check")
    
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)