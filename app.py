from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import threading
import json
import time
import random
from enum import Enum
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hello secret key for predictive maintenance'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///predictive_maintenance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enums
class UserRole(Enum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    OPERATOR = "operator"

class SystemType(Enum):
    CONVEYOR = "conveyor"
    BUCKET_ELEVATOR = "bucket_elevator"

class FaultType(Enum):
    BALL_BEARING = 0
    BELT_SLIPPAGE = 1
    CENTRAL_SHAFT = 2
    DRIVE_MOTOR = 3
    IDLER_ROLLER = 4
    PULLEY = 5

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

# Data classes
@dataclass
class SensorReading:
    timestamp: datetime
    system_type: SystemType
    sensor_type: str
    value: float
    unit: str
    normal_range: tuple
    is_anomaly: bool = False

@dataclass
class FaultPrediction:
    timestamp: datetime
    system_type: SystemType
    fault_type: FaultType
    confidence: float
    severity: str
    recommendations: List[str]
    maintenance_actions: List[str]

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.Enum(UserRole), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    system_type = db.Column(db.Enum(SystemType), nullable=False)
    sensor_type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    is_anomaly = db.Column(db.Boolean, default=False)
    
class FaultLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    system_type = db.Column(db.Enum(SystemType), nullable=False)
    fault_type = db.Column(db.Enum(FaultType), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='open')  # open, acknowledged, resolved
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolved_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)

class MaintenanceAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fault_log_id = db.Column(db.Integer, db.ForeignKey('fault_log.id'))
    action_description = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    estimated_duration = db.Column(db.Integer)  # in minutes
    required_tools = db.Column(db.Text)
    safety_precautions = db.Column(db.Text)
    is_completed = db.Column(db.Boolean, default=False)
    completed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    completed_at = db.Column(db.DateTime)

class SystemStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    system_type = db.Column(db.Enum(SystemType), nullable=False)
    is_running = db.Column(db.Boolean, default=True)
    health_score = db.Column(db.Float, default=100.0)
    last_maintenance = db.Column(db.DateTime)
    next_maintenance = db.Column(db.DateTime)
    total_runtime = db.Column(db.Float, default=0.0)  # in hours
    fault_count = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

# Global variables for simulation data
simulation_data = {
    SystemType.CONVEYOR: {
        'running': False,
        'thread': None,
        'current_readings': {},
        'fault_injection': None
    },
    SystemType.BUCKET_ELEVATOR: {
        'running': False,
        'thread': None,
        'current_readings': {},
        'fault_injection': None
    }
}

# Fault definitions and maintenance instructions
FAULT_DEFINITIONS = {
    FaultType.BALL_BEARING: {
        'name': 'Ball Bearing Fault',
        'description': 'Bearing wear or damage detected',
        'symptoms': ['Increased vibration', 'Unusual noise', 'Temperature rise'],
        'immediate_actions': [
            'Reduce operational speed to 50%',
            'Monitor temperature and vibration closely',
            'Schedule bearing inspection within 24 hours'
        ],
        'maintenance_steps': [
            '1. Safely shutdown the system',
            '2. Lock out/Tag out (LOTO) procedures',
            '3. Remove guards and access panels',
            '4. Inspect bearing housing for damage',
            '5. Check bearing alignment and lubrication',
            '6. Replace bearing if necessary',
            '7. Reassemble and test system'
        ],
        'tools_required': ['Bearing pullers', 'Alignment tools', 'Lubricants', 'Torque wrench'],
        'safety_precautions': [
            'Follow LOTO procedures',
            'Wear safety glasses and gloves',
            'Ensure proper ventilation',
            'Use appropriate lifting equipment'
        ]
    },
    FaultType.BELT_SLIPPAGE: {
        'name': 'Belt Slippage',
        'description': 'Belt is slipping on pulleys',
        'symptoms': ['Reduced throughput', 'Belt tracking issues', 'Unusual wear patterns'],
        'immediate_actions': [
            'Reduce load on conveyor',
            'Check belt tension immediately',
            'Inspect pulley surfaces for contamination'
        ],
        'maintenance_steps': [
            '1. Stop conveyor system safely',
            '2. Check belt tension using tension gauge',
            '3. Inspect pulleys for wear or contamination',
            '4. Clean pulley surfaces if necessary',
            '5. Adjust belt tension to specification',
            '6. Check belt tracking and alignment',
            '7. Resume operation and monitor'
        ],
        'tools_required': ['Belt tension gauge', 'Cleaning supplies', 'Adjustment tools'],
        'safety_precautions': [
            'Never adjust belt while running',
            'Use proper lifting techniques',
            'Ensure hands are clear of pinch points'
        ]
    },
    FaultType.CENTRAL_SHAFT: {
        'name': 'Central Shaft Fault',
        'description': 'Central shaft misalignment or damage',
        'symptoms': ['Excessive vibration', 'Uneven wear', 'Noise from drive assembly'],
        'immediate_actions': [
            'Reduce speed to minimum operational level',
            'Monitor vibration levels continuously',
            'Schedule immediate inspection'
        ],
        'maintenance_steps': [
            '1. Shutdown system completely',
            '2. Perform shaft alignment check',
            '3. Inspect shaft for cracks or wear',
            '4. Check coupling connections',
            '5. Realign shaft if necessary',
            '6. Replace damaged components',
            '7. Test alignment after reassembly'
        ],
        'tools_required': ['Laser alignment tools', 'Dial indicators', 'Shaft keys', 'Coupling tools'],
        'safety_precautions': [
            'Use proper fall protection',
            'Ensure stable work platform',
            'Follow confined space procedures if applicable'
        ]
    },
    FaultType.DRIVE_MOTOR: {
        'name': 'Drive Motor Fault',
        'description': 'Motor performance degradation or failure',
        'symptoms': ['Overcurrent', 'Overheating', 'Unusual noise', 'Reduced power'],
        'immediate_actions': [
            'Check motor temperature',
            'Verify electrical connections',
            'Reduce load if possible',
            'Contact electrical technician'
        ],
        'maintenance_steps': [
            '1. Electrical isolation and LOTO',
            '2. Check motor windings with megger',
            '3. Inspect motor bearings',
            '4. Verify electrical connections',
            '5. Check motor mounting and alignment',
            '6. Test motor performance',
            '7. Replace motor if necessary'
        ],
        'tools_required': ['Multimeter', 'Megger', 'Infrared thermometer', 'Motor testing equipment'],
        'safety_precautions': [
            'Qualified electrician required',
            'Verify electrical isolation',
            'Use appropriate PPE',
            'Test equipment before use'
        ]
    },
    FaultType.IDLER_ROLLER: {
        'name': 'Idler Roller Fault',
        'description': 'Idler roller bearing failure or misalignment',
        'symptoms': ['Belt mistracking', 'Increased noise', 'Uneven belt wear'],
        'immediate_actions': [
            'Inspect affected roller visually',
            'Check belt tracking',
            'Adjust speed if tracking is poor'
        ],
        'maintenance_steps': [
            '1. Identify specific faulty roller',
            '2. Remove belt from roller area',
            '3. Remove roller from frame',
            '4. Inspect roller bearings',
            '5. Replace bearings or entire roller',
            '6. Reinstall and check alignment',
            '7. Test belt tracking'
        ],
        'tools_required': ['Roller removal tools', 'Bearing pullers', 'Alignment tools'],
        'safety_precautions': [
            'Support belt during roller removal',
            'Use proper lifting techniques',
            'Ensure roller is properly secured'
        ]
    },
    FaultType.PULLEY: {
        'name': 'Pulley Fault',
        'description': 'Pulley wear, damage, or misalignment',
        'symptoms': ['Belt damage', 'Slippage', 'Excessive wear', 'Noise'],
        'immediate_actions': [
            'Inspect pulley surface condition',
            'Check pulley alignment',
            'Reduce belt tension if safe to do so'
        ],
        'maintenance_steps': [
            '1. Remove belt from pulley',
            '2. Inspect pulley surface for wear',
            '3. Check pulley alignment',
            '4. Measure pulley dimensions',
            '5. Resurface or replace pulley',
            '6. Reinstall belt with proper tension',
            '7. Verify tracking and operation'
        ],
        'tools_required': ['Pulley alignment tools', 'Measuring calipers', 'Surfacing tools'],
        'safety_precautions': [
            'Never work on pulleys while belt is running',
            'Use proper guarding during operation',
            'Ensure proper belt tension'
        ]
    }
}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def requires_role(required_role):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role.value not in [required_role.value, UserRole.ADMIN.value]:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

def simulate_sensor_reading(system_type: SystemType, sensor_type: str, 
                          base_value: float, variance: float, 
                          fault_injection: Optional[FaultType] = None) -> SensorReading:
    """Simulate sensor reading with optional fault injection"""
    
    # Normal reading
    value = base_value + random.uniform(-variance, variance)
    is_anomaly = False
    
    # Inject faults to test system behavior
    if fault_injection:
        if fault_injection == FaultType.BALL_BEARING and sensor_type == 'vibration':
            value *= random.uniform(2.0, 4.0)  # Significant vibration increase
            is_anomaly = True
        elif fault_injection == FaultType.BELT_SLIPPAGE and sensor_type == 'speed':
            value *= random.uniform(0.6, 0.8)  # Speed reduction
            is_anomaly = True
        elif fault_injection == FaultType.DRIVE_MOTOR and sensor_type == 'current':
            value *= random.uniform(1.5, 2.5)  # Current increase
            is_anomaly = True
        elif fault_injection == FaultType.CENTRAL_SHAFT and sensor_type == 'vibration':
            value *= random.uniform(1.8, 3.0)  # Vibration increase
            is_anomaly = True
        elif fault_injection == FaultType.IDLER_ROLLER and sensor_type == 'temperature':
            value *= random.uniform(1.3, 1.8)  # Temperature increase
            is_anomaly = True
        elif fault_injection == FaultType.PULLEY and sensor_type in ['speed', 'vibration']:
            value *= random.uniform(1.2, 2.0)  # Multiple symptoms
            is_anomaly = True
    
    # Define normal ranges for different sensors
    normal_ranges = {
        'speed': (0.5, 3.0),
        'vibration': (0, 15),
        'temperature': (20, 70),
        'current': (5, 45),
        'load': (0, 100),
        'slippage': (0, 8)
    }
    
    normal_range = normal_ranges.get(sensor_type, (0, 100))
    
    return SensorReading(
        timestamp=datetime.utcnow(),
        system_type=system_type,
        sensor_type=sensor_type,
        value=value,
        unit=get_sensor_unit(sensor_type),
        normal_range=normal_range,
        is_anomaly=is_anomaly
    )

def get_sensor_unit(sensor_type: str) -> str:
    """Get unit for sensor type"""
    units = {
        'speed': 'm/s',
        'vibration': 'm/s²',
        'temperature': '°C',
        'current': 'A',
        'load': '%',
        'slippage': '%'
    }
    return units.get(sensor_type, '')

def store_sensor_reading(reading: SensorReading):
    """Store sensor reading in database"""
    sensor_data = SensorData(
        timestamp=reading.timestamp,
        system_type=reading.system_type,
        sensor_type=reading.sensor_type,
        value=reading.value,
        unit=reading.unit,
        is_anomaly=reading.is_anomaly
    )
    db.session.add(sensor_data)
    db.session.commit()

def simulate_system_data(system_type: SystemType):
    """Simulate continuous sensor data for a system"""
    logger.info(f"Starting simulation for {system_type.value}")

    system_status = SystemStatus.query.filter_by(system_type=system_type).first()
    if not system_status:
        system_status = SystemStatus(system_type=system_type)
        db.session.add(system_status)
    
    system_status.is_running = True
    db.session.commit()
    
    sensor_configs = {
        'speed': {'base': 1.5, 'variance': 0.1},
        'vibration': {'base': 5.0, 'variance': 1.0},
        'temperature': {'base': 45.0, 'variance': 5.0},
        'current': {'base': 15.0, 'variance': 2.0},
        'load': {'base': 60.0, 'variance': 10.0},
        'slippage': {'base': 2.0, 'variance': 0.5}
    }
    
    while simulation_data[system_type]['running']:
        try:
            current_readings = {}
            fault_injection = simulation_data[system_type]['fault_injection']
            
            # Generate readings for all sensors
            for sensor_type, config in sensor_configs.items():
                reading = simulate_sensor_reading(
                    system_type=system_type,
                    sensor_type=sensor_type,
                    base_value=config['base'],
                    variance=config['variance'],
                    fault_injection=fault_injection
                )
                
                current_readings[sensor_type] = reading
                store_sensor_reading(reading)
            
            # Update global simulation data
            simulation_data[system_type]['current_readings'] = current_readings
            
            # Check for fault conditions and create predictions
            if fault_injection:
                create_fault_prediction(system_type, fault_injection, current_readings)
            
            time.sleep(2)  # Update every 2 seconds
            
        except Exception as e:
            logger.error(f"Error in simulation for {system_type.value}: {e}")
            time.sleep(5)

def create_fault_prediction(system_type: SystemType, fault_type: FaultType, readings: Dict):
    """Create fault prediction based on sensor readings"""
    
    # Calculate confidence based on anomaly detection
    anomaly_count = sum(1 for reading in readings.values() if reading.is_anomaly)
    confidence = min(0.95, 0.6 + (anomaly_count / len(readings)) * 0.35)
    
    # Determine severity
    if confidence > 0.9:
        severity = "CRITICAL"
    elif confidence > 0.7:
        severity = "HIGH"
    elif confidence > 0.5:
        severity = "MEDIUM"
    else:
        severity = "LOW"
    
    # Get fault information
    fault_info = FAULT_DEFINITIONS[fault_type]
    
    # Create fault log entry
    fault_log = FaultLog(
        timestamp=datetime.utcnow(),
        system_type=system_type,
        fault_type=fault_type,
        confidence=confidence,
        severity=severity
    )
    
    db.session.add(fault_log)
    db.session.commit()
    
    # Create maintenance actions
    for i, action in enumerate(fault_info['maintenance_steps']):
        maintenance_action = MaintenanceAction(
            fault_log_id=fault_log.id,
            action_description=action,
            priority=severity,
            estimated_duration=30 + i * 15,  # Estimated duration
            required_tools=', '.join(fault_info['tools_required']),
            safety_precautions=', '.join(fault_info['safety_precautions'])
        )
        db.session.add(maintenance_action)
    
    db.session.commit()
    
    logger.info(f"Created fault prediction: {fault_type.name} for {system_type.value} with confidence {confidence:.2f}")


@app.route('/api/stop-simulation/<system_type>')
@login_required
@requires_role(UserRole.ENGINEER)
def stop_simulation(system_type):
    """API endpoint to stop system simulation"""
    try:
        system_enum = SystemType(system_type)
        simulation_data[system_enum]['running'] = False
        
        # Update system status
        system_status = SystemStatus.query.filter_by(system_type=system_enum).first()
        if system_status:
            system_status.is_running = False
            db.session.commit()
        
        return jsonify({'status': 'stopped', 'message': f'{system_type} simulation stopped'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get system status
    conveyor_status = SystemStatus.query.filter_by(system_type=SystemType.CONVEYOR).first()
    elevator_status = SystemStatus.query.filter_by(system_type=SystemType.BUCKET_ELEVATOR).first()
    
    # Get recent faults
    recent_faults = FaultLog.query.order_by(FaultLog.timestamp.desc()).limit(10).all()
    
    # Get active alarms
    active_alarms = FaultLog.query.filter_by(status='open').all()
    
    # Pass user information to the template
    return render_template('dashboard.html', 
                         current_user=current_user,
                         conveyor_status=conveyor_status,
                         elevator_status=elevator_status,
                         recent_faults=recent_faults,
                         active_alarms=active_alarms)

@app.route('/api/sensor-data/<system_type>')
@login_required
def get_sensor_data(system_type):
    """API endpoint to get current sensor data"""
    try:
        system_enum = SystemType(system_type)
        readings = simulation_data[system_enum]['current_readings']
        
        data = {}
        for sensor_type, reading in readings.items():
            data[sensor_type] = {
                'value': reading.value,
                'unit': reading.unit,
                'timestamp': reading.timestamp.isoformat(),
                'is_anomaly': reading.is_anomaly
            }
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/start-simulation/<system_type>')
@login_required
@requires_role(UserRole.ENGINEER)
def start_simulation(system_type):
    """API endpoint to start system simulation"""
    try:
        system_enum = SystemType(system_type)
        
        if not simulation_data[system_enum]['running']:
            simulation_data[system_enum]['running'] = True
            thread = threading.Thread(target=simulate_system_data, args=(system_enum,))
            thread.daemon = True
            thread.start()
            simulation_data[system_enum]['thread'] = thread
            
            return jsonify({'status': 'started', 'message': f'{system_type} simulation started'})
        else:
            return jsonify({'status': 'already_running', 'message': f'{system_type} simulation already running'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/inject-fault/<system_type>/<fault_type>')
@login_required
@requires_role(UserRole.ENGINEER)
def inject_fault(system_type, fault_type):
    """API endpoint to inject fault for testing"""
    try:
        system_enum = SystemType(system_type)
        fault_enum = FaultType(int(fault_type))
        
        simulation_data[system_enum]['fault_injection'] = fault_enum
        
        return jsonify({
            'status': 'fault_injected',
            'message': f'Fault {fault_enum.name} injected into {system_type}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/clear-fault/<system_type>')
@login_required
@requires_role(UserRole.ENGINEER)
def clear_fault(system_type):
    """API endpoint to clear fault injection"""
    try:
        system_enum = SystemType(system_type)
        simulation_data[system_enum]['fault_injection'] = None
        
        return jsonify({
            'status': 'fault_cleared',
            'message': f'Fault injection cleared for {system_type}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
# Add these routes to your Flask app

@app.route('/api/system-status')
@login_required
def get_system_status():
    """API endpoint to get system status for both systems"""
    conveyor_status = SystemStatus.query.filter_by(system_type=SystemType.CONVEYOR).first()
    elevator_status = SystemStatus.query.filter_by(system_type=SystemType.BUCKET_ELEVATOR).first()
    
    if not conveyor_status:
        conveyor_status = SystemStatus(system_type=SystemType.CONVEYOR)
        db.session.add(conveyor_status)
        db.session.commit()
    
    if not elevator_status:
        elevator_status = SystemStatus(system_type=SystemType.BUCKET_ELEVATOR)
        db.session.add(elevator_status)
        db.session.commit()
    
    return jsonify({
        'CONVEYOR': {
            'is_running': conveyor_status.is_running,
            'health_score': conveyor_status.health_score,
            'last_maintenance': conveyor_status.last_maintenance.isoformat() if conveyor_status.last_maintenance else None,
            'next_maintenance': conveyor_status.next_maintenance.isoformat() if conveyor_status.next_maintenance else None,
            'total_runtime': conveyor_status.total_runtime,
            'fault_count': conveyor_status.fault_count
        },
        'BUCKET_ELEVATOR': {
            'is_running': elevator_status.is_running,
            'health_score': elevator_status.health_score,
            'last_maintenance': elevator_status.last_maintenance.isoformat() if elevator_status.last_maintenance else None,
            'next_maintenance': elevator_status.next_maintenance.isoformat() if elevator_status.next_maintenance else None,
            'total_runtime': elevator_status.total_runtime,
            'fault_count': elevator_status.fault_count
        }
    })

@app.route('/api/recent-faults')
@login_required
def get_recent_faults():
    """API endpoint to get recent faults"""
    recent_faults = FaultLog.query.order_by(FaultLog.timestamp.desc()).limit(10).all()
    
    faults_data = []
    for fault in recent_faults:
        faults_data.append({
            'id': fault.id,
            'timestamp': fault.timestamp.isoformat(),
            'system_type': fault.system_type.value,
            'fault_type': fault.fault_type.value,
            'confidence': fault.confidence,
            'severity': fault.severity,
            'status': fault.status,
            'acknowledged_by': fault.acknowledged_by,
            'resolved_by': fault.resolved_by,
            'resolved_at': fault.resolved_at.isoformat() if fault.resolved_at else None,
            'notes': fault.notes
        })
    
    return jsonify(faults_data)

@app.route('/api/active-alarms')
@login_required
def get_active_alarms():
    """API endpoint to get active alarms"""
    active_alarms = FaultLog.query.filter_by(status='open').all()
    
    alarms_data = []
    for alarm in active_alarms:
        alarms_data.append({
            'id': alarm.id,
            'timestamp': alarm.timestamp.isoformat(),
            'system_type': alarm.system_type.value,
            'fault_type': alarm.fault_type.value,
            'confidence': alarm.confidence,
            'severity': alarm.severity,
            'status': alarm.status
        })
    
    return jsonify(alarms_data)

@app.route('/api/acknowledge-alarm/<int:alarm_id>', methods=['POST'])
@login_required
@requires_role(UserRole.ENGINEER)
def acknowledge_alarm(alarm_id):
    """API endpoint to acknowledge an alarm"""
    alarm = FaultLog.query.get(alarm_id)
    if not alarm:
        return jsonify({'error': 'Alarm not found'}), 404
    
    alarm.status = 'acknowledged'
    alarm.acknowledged_by = current_user.id
    db.session.commit()
    
    return jsonify({'status': 'acknowledged', 'message': f'Alarm {alarm_id} acknowledged'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create default admin user if doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com', role=UserRole.ADMIN)
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Create default system status entries
            for system in SystemType:
                if not SystemStatus.query.filter_by(system_type=system).first():
                    status = SystemStatus(system_type=system)
                    db.session.add(status)
            
            db.session.commit()
            logger.info("Default admin user and system status entries created")
    
        app.run(debug=True, host='0.0.0.0', port=5000)