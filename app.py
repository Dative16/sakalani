from flask import Flask, render_template, jsonify
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuration matching the frontend
CONFIG = {
    'DASHBOARD': {
        'TITLE': 'Predictive Maintenance Dashboard',
        'SUBTITLE': 'Real-time Monitoring & Anomaly Detection',
        'VERSION': '3.0',
        'MAX_CHART_POINTS': 20,
        'AUTO_REFRESH': True,
        'REFRESH_INTERVAL': 5000
    },
    'SYSTEMS': {
        'BUCKET_ELEVATOR': {
            'id': 1,
            'name': 'Bucket Elevator',
            'icon': '⬆️',
            'sensors': {
                'SPEED': { 
                    'name': 'Speed', 'unit': 'rpm', 
                    'min': 105, 'max': 130, 
                    'warning_low': 100, 'warning_high': 135,
                    'danger_low': 95, 'danger_high': 140,
                    'color': '#3b82f6', 'icon': '📊' 
                },
                'LOAD': { 
                    'name': 'Load', 'unit': 'kg', 
                    'min': 460, 'max': 560, 
                    'warning_low': 440, 'warning_high': 580,
                    'danger_low': 420, 'danger_high': 600,
                    'color': '#ef4444', 'icon': '🏋️' 
                },
                'TEMPERATURE': { 
                    'name': 'Temperature', 'unit': '°C', 
                    'min': 35, 'max': 50, 
                    'warning_low': 32, 'warning_high': 53,
                    'danger_low': 30, 'danger_high': 55,
                    'color': '#f97316', 'icon': '🌡️' 
                },
                'VIBRATION': { 
                    'name': 'Vibration', 'unit': 'm/s²', 
                    'min': 0.6, 'max': 1.3, 
                    'warning_low': 0.5, 'warning_high': 1.4,
                    'danger_low': 0.4, 'danger_high': 1.5,
                    'color': '#8b5cf6', 'icon': '📳' 
                },
                'CURRENT': { 
                    'name': 'Current', 'unit': 'A', 
                    'min': 2.8, 'max': 4.2, 
                    'warning_low': 2.6, 'warning_high': 4.4,
                    'danger_low': 2.4, 'danger_high': 4.6,
                    'color': '#10b981', 'icon': '⚡' 
                }
            }
        },
        'CONVEYOR_BELT': {
            'id': 2,
            'name': 'Conveyor Belt',
            'icon': '↔️',
            'sensors': {
                'SPEED': { 
                    'name': 'Speed', 'unit': 'rpm', 
                    'min': 80, 'max': 120, 
                    'warning_low': 75, 'warning_high': 125,
                    'danger_low': 70, 'danger_high': 130,
                    'color': '#3b82f6', 'icon': '📊' 
                },
                'LOAD': { 
                    'name': 'Load', 'unit': 'kg', 
                    'min': 200, 'max': 400, 
                    'warning_low': 190, 'warning_high': 420,
                    'danger_low': 180, 'danger_high': 440,
                    'color': '#ef4444', 'icon': '🏋️' 
                },
                'TEMPERATURE': { 
                    'name': 'Temperature', 'unit': '°C', 
                    'min': 30, 'max': 45, 
                    'warning_low': 28, 'warning_high': 48,
                    'danger_low': 26, 'danger_high': 50,
                    'color': '#f97316', 'icon': '🌡️' 
                },
                'VIBRATION': { 
                    'name': 'Vibration', 'unit': 'm/s²', 
                    'min': 0.4, 'max': 1.0, 
                    'warning_low': 0.35, 'warning_high': 1.1,
                    'danger_low': 0.3, 'danger_high': 1.2,
                    'color': '#8b5cf6', 'icon': '📳' 
                },
                'CURRENT': { 
                    'name': 'Current', 'unit': 'A', 
                    'min': 1.5, 'max': 3.0, 
                    'warning_low': 1.4, 'warning_high': 3.2,
                    'danger_low': 1.3, 'danger_high': 3.4,
                    'color': '#10b981', 'icon': '⚡' 
                }
            }
        }
    },
    'ROLES': {
        'operator': {'name': 'Operator', 'permissions': ['view'], 'dashboardSections': ['dashboard', 'alarms'], 'color': '#3b82f6'},
        'engineer': {'name': 'Engineer', 'permissions': ['view', 'manage'], 'dashboardSections': ['dashboard', 'alarms', 'reports'], 'color': '#f97316'},
        'admin': {'name': 'Admin', 'permissions': ['view', 'manage', 'configure'], 'dashboardSections': ['dashboard', 'alarms', 'reports', 'settings'], 'color': '#8b5cf6'}
    },
    'UTILS': {
    'calculatePercentage': 'frontend_function',
    'formatValue': 'frontend_function',
    'formatTimestamp': 'frontend_function',
    'getStatusColor': 'frontend_function'
}
}

@app.route('/')
def index():
    safe_config = CONFIG.copy()
    safe_config['UTILS'] = {k: 'frontend_function' for k in safe_config['UTILS']}
    return render_template('index.html', config=safe_config)

@app.route('/api/current_data')
def current_data():
    """API endpoint to get current sensor data"""
    now = datetime.now()
    data = {
        'BUCKET_ELEVATOR': {'timestamp': now.isoformat()},
        'CONVEYOR_BELT': {'timestamp': now.isoformat()}
    }
    
    # Generate bucket elevator data
    for sensor_key, sensor in CONFIG['SYSTEMS']['BUCKET_ELEVATOR']['sensors'].items():
        sensor_key_lower = sensor_key.lower()
        range_val = sensor['max'] - sensor['min']
        base_value = sensor['min'] + (range_val * 0.3) + random.random() * (range_val * 0.4)
        data['BUCKET_ELEVATOR'][sensor_key_lower] = max(sensor['danger_low'], min(sensor['danger_high'], base_value))
    
    # Generate conveyor belt data
    for sensor_key, sensor in CONFIG['SYSTEMS']['CONVEYOR_BELT']['sensors'].items():
        sensor_key_lower = sensor_key.lower()
        range_val = sensor['max'] - sensor['min']
        base_value = sensor['min'] + (range_val * 0.3) + random.random() * (range_val * 0.4)
        data['CONVEYOR_BELT'][sensor_key_lower] = max(sensor['danger_low'], min(sensor['danger_high'], base_value))
    
    return jsonify(data)

@app.route('/api/historical_data')
def historical_data():
    """API endpoint to get historical sensor data"""
    now = datetime.now()
    data = {
        'BUCKET_ELEVATOR': [],
        'CONVEYOR_BELT': []
    }
    
    # Generate historical data for both systems
    for i in range(CONFIG['DASHBOARD']['MAX_CHART_POINTS']):
        timestamp = now - timedelta(minutes=(CONFIG['DASHBOARD']['MAX_CHART_POINTS'] - i - 1))
        
        # Bucket elevator data point
        bucket_data = {'timestamp': timestamp.isoformat()}
        for sensor_key, sensor in CONFIG['SYSTEMS']['BUCKET_ELEVATOR']['sensors'].items():
            sensor_key_lower = sensor_key.lower()
            range_val = sensor['max'] - sensor['min']
            base_value = sensor['min'] + (range_val * 0.3) + random.random() * (range_val * 0.4)
            bucket_data[sensor_key_lower] = max(sensor['danger_low'], min(sensor['danger_high'], base_value))
        data['BUCKET_ELEVATOR'].append(bucket_data)
        
        # Conveyor belt data point
        conveyor_data = {'timestamp': timestamp.isoformat()}
        for sensor_key, sensor in CONFIG['SYSTEMS']['CONVEYOR_BELT']['sensors'].items():
            sensor_key_lower = sensor_key.lower()
            range_val = sensor['max'] - sensor['min']
            base_value = sensor['min'] + (range_val * 0.3) + random.random() * (range_val * 0.4)
            conveyor_data[sensor_key_lower] = max(sensor['danger_low'], min(sensor['danger_high'], base_value))
        data['CONVEYOR_BELT'].append(conveyor_data)
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)