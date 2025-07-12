"""
Enhanced Sensor System for Bucket Elevator IoT Integration
Replaces the basic SensorSystem in main9.py with advanced features:
- PHP backend integration
- Predictive maintenance calculations
- Advanced alarm management
- Performance analytics
- Real-time data transmission
"""

import random
import math
import time
import threading
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedSensorSystem:
    """Advanced sensor system with IoT integration and predictive analytics"""
    
    def __init__(self, machine_id=1, php_connector=None):
        self.machine_id = machine_id
        self.php_connector = php_connector
        
        # Sensor configuration with enhanced parameters
        self.sensors = {
            'speed_rpm': {
                'value': 0, 'unit': 'rpm', 'min': 0, 'max': 100, 
                'alarm_threshold': 90, 'critical_threshold': 95,
                'optimal_range': (40, 60), 'calibration_factor': 1.0
            },
            'load_kg': {
                'value': 0, 'unit': 'kg', 'min': 0, 'max': 1000, 
                'alarm_threshold': 900, 'critical_threshold': 950,
                'optimal_range': (400, 700), 'calibration_factor': 1.0
            },
            'temperature_c': {
                'value': 25, 'unit': '°C', 'min': 20, 'max': 80, 
                'alarm_threshold': 70, 'critical_threshold': 75,
                'optimal_range': (25, 45), 'calibration_factor': 1.0
            },
            'vibration_ms2': {
                'value': 0, 'unit': 'm/s²', 'min': 0, 'max': 20, 
                'alarm_threshold': 15, 'critical_threshold': 18,
                'optimal_range': (2, 8), 'calibration_factor': 1.0
            },
            'current_a': {
                'value': 0, 'unit': 'A', 'min': 0, 'max': 50, 
                'alarm_threshold': 45, 'critical_threshold': 48,
                'optimal_range': (15, 35), 'calibration_factor': 1.0
            }
        }
        
        # Historical data storage
        self.history = {sensor: [] for sensor in self.sensors.keys()}
        self.max_history_points = 1000
        
        # Alarm management
        self.alarms = []
        self.alarm_history = []
        self.last_alarm_time = {}
        self.alarm_cooldown = 30  # seconds between same type alarms
        
        # Health and performance tracking
        self.health_score = 100.0
        self.performance_metrics = {
            'efficiency': 0.95,
            'uptime': 0.98,
            'throughput': 0.85,
            'energy_consumption': 100.0
        }
        
        # Predictive maintenance
        self.maintenance_recommendations = []
        self.remaining_useful_life = 85.0  # percentage
        self.operating_hours = 0
        self.total_cycles = 0
        
        # Trend analysis
        self.trend_data = {sensor: {'slope': 0, 'r_squared': 0} for sensor in self.sensors.keys()}
        
        # Failure prediction models (simplified)
        self.failure_indicators = {
            'bearing_wear': 0.0,
            'belt_degradation': 0.0,
            'motor_efficiency': 1.0,
            'lubrication_quality': 1.0
        }
        
        # Data transmission settings
        self.last_transmission = 0
        self.transmission_interval = 3  # seconds
        self.batch_size = 5  # Send data every 5 readings in batch mode
        self.reading_count = 0
        
        # Load configuration from backend if available
        if self.php_connector:
            self.load_sensor_config()
        
        logger.info(f"Enhanced Sensor System initialized for machine {machine_id}")
    
    def load_sensor_config(self):
        """Load sensor configuration from PHP backend"""
        try:
            if self.php_connector and self.php_connector.connected:
                config = self.php_connector.get_sensor_config()
                if config:
                    for sensor_config in config:
                        sensor_type = sensor_config.get('type')
                        if sensor_type in self.sensors:
                            self.sensors[sensor_type]['alarm_threshold'] = sensor_config.get('threshold_value', 
                                                                                           self.sensors[sensor_type]['alarm_threshold'])
                            self.sensors[sensor_type]['max'] = sensor_config.get('max_value', 
                                                                               self.sensors[sensor_type]['max'])
                            logger.info(f"Updated {sensor_type} config from backend")
        except Exception as e:
            logger.warning(f"Could not load sensor config: {e}")
    
    def update_sensors(self, belt_speed, material_count, operating_time):
        """Enhanced sensor update with realistic physics modeling"""
        try:
            self.operating_hours = operating_time / 3600
            self.reading_count += 1
            
            # Update all sensor values
            self._update_speed_sensor(belt_speed)
            self._update_load_sensor(material_count, operating_time)
            self._update_temperature_sensor(operating_time)
            self._update_vibration_sensor(operating_time)
            self._update_current_sensor(operating_time)
            
            # Apply calibration factors and noise
            self._apply_sensor_calibration()
            self._add_realistic_noise()
            
            # Ensure values stay within bounds
            self._enforce_sensor_bounds()
            
            # Store historical data
            self._store_historical_data()
            
            # Calculate performance metrics
            self._calculate_performance_metrics(operating_time)
            
            # Update health score and predictions
            self._update_health_score()
            self._update_failure_predictions(operating_time)
            
            # Perform trend analysis
            if len(self.history['speed_rpm']) > 10:
                self._perform_trend_analysis()
            
            # Check for alarms
            new_alarms = self._check_comprehensive_alarms()
            
            # Generate maintenance recommendations
            self._generate_maintenance_recommendations()
            
            # Transmit data to backend
            self._handle_data_transmission(new_alarms)
            
        except Exception as e:
            logger.error(f"Error updating sensors: {e}")
    
    def _update_speed_sensor(self, belt_speed):
        """Update speed sensor with realistic modeling"""
        # Convert belt speed to RPM
        pulley_circumference = 2 * math.pi * 0.6  # 0.6m radius pulley
        base_rpm = (belt_speed / pulley_circumference) * 60
        
        # Add mechanical variations
        mechanical_variation = math.sin(time.time() * 2) * 2  # ±2 RPM variation
        load_effect = (self.sensors['load_kg']['value'] / 1000) * -5  # Load reduces speed
        
        self.sensors['speed_rpm']['value'] = max(0, base_rpm + mechanical_variation + load_effect)
    
    def _update_load_sensor(self, material_count, operating_time):
        """Update load sensor with material dynamics"""
        # Base elevator weight
        base_load = 100
        
        # Material weight with distribution
        material_load = material_count * 2.5  # 2.5kg per material unit
        
        # Dynamic loading effects
        loading_cycles = math.sin(operating_time * 0.1) * 50  # Cyclical loading
        settling_effect = math.cos(operating_time * 0.05) * 20  # Material settling
        
        # Wear-based load increase (worn components require more force)
        wear_factor = min(self.operating_hours / 1000, 0.2) * 30
        
        self.sensors['load_kg']['value'] = base_load + material_load + loading_cycles + settling_effect + wear_factor
    
    def _update_temperature_sensor(self, operating_time):
        """Update temperature with thermal modeling"""
        ambient_temp = 25
        
        # Heat generation sources
        motor_heat = (self.sensors['current_a']['value'] / 50) * 25  # Motor heating
        friction_heat = (self.sensors['load_kg']['value'] / 1000) * 15  # Friction heating
        speed_heat = (self.sensors['speed_rpm']['value'] / 100) * 10  # Speed-related heating
        
        # Thermal mass and cooling
        thermal_buildup = min(self.operating_hours / 4, 1) * 20  # Gradual heat buildup
        cooling_efficiency = 0.95 - (self.operating_hours / 5000) * 0.1  # Cooling degrades over time
        
        # Environmental factors
        time_of_day_factor = math.sin((operating_time / 86400) * 2 * math.pi) * 5  # Daily temperature cycle
        
        target_temp = (ambient_temp + motor_heat + friction_heat + speed_heat + 
                      thermal_buildup + time_of_day_factor)
        
        # Thermal inertia (temperature changes gradually)
        current_temp = self.sensors['temperature_c']['value']
        temp_change_rate = 0.1  # How quickly temperature responds
        self.sensors['temperature_c']['value'] = current_temp + (target_temp - current_temp) * temp_change_rate
    
    def _update_vibration_sensor(self, operating_time):
        """Update vibration with detailed mechanical modeling"""
        base_vibration = 2
        
        # Speed-related vibration
        speed_vib = (self.sensors['speed_rpm']['value'] / 100) * 6
        
        # Load imbalance vibration
        load_imbalance = abs(self.sensors['load_kg']['value'] - 500) / 500 * 4
        
        # Bearing wear vibration (increases over time)
        bearing_wear = min(self.operating_hours / 1000, 1) * 8
        
        # Belt misalignment (periodic)
        misalignment = math.sin(operating_time * 0.3) * 2
        
        # Resonance effects at specific speeds
        resonance = 0
        rpm = self.sensors['speed_rpm']['value']
        if 45 <= rpm <= 55:  # Critical speed range
            resonance = 3 * math.sin((rpm - 50) * math.pi / 5)
        
        # Random mechanical noise
        mechanical_noise = random.uniform(-1, 1)
        
        self.sensors['vibration_ms2']['value'] = (base_vibration + speed_vib + load_imbalance + 
                                                bearing_wear + misalignment + resonance + mechanical_noise)
    
    def _update_current_sensor(self, operating_time):
        """Update current consumption with electrical modeling"""
        # Base current (no-load)
        base_current = 5
        
        # Load-proportional current
        load_current = (self.sensors['load_kg']['value'] / 1000) * 25
        
        # Speed-dependent current
        speed_current = (self.sensors['speed_rpm']['value'] / 100) * 8
        
        # Temperature effects (higher resistance at higher temps)
        temp_factor = 1 + (max(0, self.sensors['temperature_c']['value'] - 40) * 0.01)
        
        # Efficiency degradation over time
        efficiency_loss = min(self.operating_hours / 2000, 0.15)  # Up to 15% efficiency loss
        efficiency_factor = 1 + efficiency_loss
        
        # Power factor variations
        power_factor_variation = math.sin(operating_time * 0.7) * 0.1 + 1
        
        # Starting current spikes (periodic)
        starting_spike = 0
        if int(operating_time) % 300 < 2:  # 2-second spike every 5 minutes
            starting_spike = 10 * math.exp(-(operating_time % 300))
        
        self.sensors['current_a']['value'] = ((base_current + load_current + speed_current + starting_spike) * 
                                            temp_factor * efficiency_factor * power_factor_variation)
    
    def _apply_sensor_calibration(self):
        """Apply calibration factors and sensor-specific adjustments"""
        for sensor_name, sensor_data in self.sensors.items():
            # Apply calibration factor
            sensor_data['value'] *= sensor_data['calibration_factor']
            
            # Sensor-specific adjustments
            if sensor_name == 'temperature_c':
                # Temperature sensors have thermal lag
                pass  # Already handled in thermal modeling
            elif sensor_name == 'vibration_ms2':
                # Vibration sensors have frequency filtering
                sensor_data['value'] = max(0, sensor_data['value'])  # No negative vibration
    
    def _add_realistic_noise(self):
        """Add realistic sensor noise and uncertainties"""
        noise_levels = {
            'speed_rpm': 0.5,
            'load_kg': 2.0,
            'temperature_c': 0.3,
            'vibration_ms2': 0.2,
            'current_a': 0.1
        }
        
        for sensor_name, noise_level in noise_levels.items():
            if sensor_name in self.sensors:
                noise = random.gauss(0, noise_level)
                self.sensors[sensor_name]['value'] += noise
    
    def _enforce_sensor_bounds(self):
        """Ensure sensor values stay within realistic bounds"""
        for sensor_name, sensor_data in self.sensors.items():
            sensor_data['value'] = max(sensor_data['min'], 
                                     min(sensor_data['max'], sensor_data['value']))
    
    def _store_historical_data(self):
        """Store sensor data in historical buffers"""
        timestamp = datetime.now()
        
        for sensor_name, sensor_data in self.sensors.items():
            self.history[sensor_name].append({
                'timestamp': timestamp,
                'value': sensor_data['value']
            })
            
            # Maintain maximum history size
            if len(self.history[sensor_name]) > self.max_history_points:
                self.history[sensor_name].pop(0)
    
    def _calculate_performance_metrics(self, operating_time):
        """Calculate overall performance metrics"""
        try:
            # Efficiency calculation
            optimal_power = 30  # kW optimal power consumption
            actual_power = self.sensors['current_a']['value'] * 0.4  # Simplified power calc
            self.performance_metrics['efficiency'] = min(1.0, optimal_power / max(actual_power, 1))
            
            # Uptime calculation (simplified - based on alarms)
            recent_critical_alarms = sum(1 for alarm in self.alarms[-10:] if alarm.get('severity') == 'CRITICAL')
            uptime_factor = max(0.5, 1.0 - (recent_critical_alarms * 0.1))
            self.performance_metrics['uptime'] = uptime_factor
            
            # Throughput calculation
            speed_efficiency = self.sensors['speed_rpm']['value'] / 60  # Normalized to optimal speed
            load_efficiency = min(1.0, self.sensors['load_kg']['value'] / 600)  # Normalized to good load
            self.performance_metrics['throughput'] = (speed_efficiency * load_efficiency) * 0.95
            
            # Energy consumption tracking
            self.performance_metrics['energy_consumption'] = actual_power
            
        except Exception as e:
            logger.warning(f"Error calculating performance metrics: {e}")
    
    def _update_health_score(self):
        """Calculate overall equipment health score"""
        try:
            health = 100.0
            
            # Deduct points for sensor values outside optimal ranges
            for sensor_name, sensor_data in self.sensors.items():
                optimal_min, optimal_max = sensor_data['optimal_range']
                value = sensor_data['value']
                
                if value < optimal_min or value > optimal_max:
                    # Calculate deviation from optimal range
                    if value < optimal_min:
                        deviation = (optimal_min - value) / optimal_min
                    else:
                        deviation = (value - optimal_max) / optimal_max
                    
                    health -= min(10, deviation * 20)  # Max 10 points per sensor
            
            # Factor in operating hours (gradual degradation)
            age_factor = min(self.operating_hours / 8760, 0.1) * 15  # Max 15 points for age
            health -= age_factor
            
            # Factor in alarm frequency
            recent_alarms = len([a for a in self.alarms[-20:] if a.get('severity') in ['HIGH', 'CRITICAL']])
            health -= min(20, recent_alarms * 2)
            
            self.health_score = max(0, min(100, health))
            
        except Exception as e:
            logger.warning(f"Error updating health score: {e}")
    
    def _update_failure_predictions(self, operating_time):
        """Update failure prediction indicators"""
        try:
            # Bearing wear prediction
            vibration_trend = self.trend_data['vibration_ms2']['slope']
            self.failure_indicators['bearing_wear'] = min(1.0, 
                max(0, (self.sensors['vibration_ms2']['value'] - 5) / 15) + vibration_trend * 0.1)
            
            # Belt degradation prediction
            speed_variation = abs(self.sensors['speed_rpm']['value'] - 50) / 50
            self.failure_indicators['belt_degradation'] = min(1.0, 
                speed_variation + (self.operating_hours / 5000))
            
            # Motor efficiency prediction
            current_trend = self.trend_data['current_a']['slope']
            expected_current = 25  # Expected current at normal load
            current_deviation = abs(self.sensors['current_a']['value'] - expected_current) / expected_current
            self.failure_indicators['motor_efficiency'] = max(0, 1.0 - current_deviation - current_trend * 0.05)
            
            # Calculate remaining useful life
            worst_indicator = max(self.failure_indicators.values())
            self.remaining_useful_life = max(0, (1 - worst_indicator) * 100)
            
        except Exception as e:
            logger.warning(f"Error updating failure predictions: {e}")
    
    def _perform_trend_analysis(self):
        """Perform trend analysis on sensor data"""
        try:
            for sensor_name in self.sensors.keys():
                if len(self.history[sensor_name]) >= 10:
                    # Get last 20 data points for trend analysis
                    recent_data = self.history[sensor_name][-20:]
                    
                    # Simple linear regression
                    n = len(recent_data)
                    sum_x = sum(range(n))
                    sum_y = sum(point['value'] for point in recent_data)
                    sum_xy = sum(i * point['value'] for i, point in enumerate(recent_data))
                    sum_xx = sum(i * i for i in range(n))
                    
                    # Calculate slope (trend)
                    denominator = n * sum_xx - sum_x * sum_x
                    if denominator != 0:
                        slope = (n * sum_xy - sum_x * sum_y) / denominator
                        
                        # Calculate R-squared (goodness of fit)
                        mean_y = sum_y / n
                        ss_tot = sum((point['value'] - mean_y) ** 2 for point in recent_data)
                        
                        if ss_tot > 0:
                            y_intercept = (sum_y - slope * sum_x) / n
                            ss_res = sum((point['value'] - (slope * i + y_intercept)) ** 2 
                                       for i, point in enumerate(recent_data))
                            r_squared = 1 - (ss_res / ss_tot)
                        else:
                            r_squared = 0
                        
                        self.trend_data[sensor_name] = {
                            'slope': slope,
                            'r_squared': max(0, min(1, r_squared))
                        }
                    
        except Exception as e:
            logger.warning(f"Error in trend analysis: {e}")
    
    def _check_comprehensive_alarms(self):
        """Enhanced alarm checking with multiple criteria"""
        new_alarms = []
        current_time = datetime.now()
        
        try:
            for sensor_name, sensor_data in self.sensors.items():
                value = sensor_data['value']
                
                # Check threshold alarms
                if value > sensor_data['critical_threshold']:
                    severity = 'CRITICAL'
                    priority = 1
                elif value > sensor_data['alarm_threshold']:
                    severity = 'HIGH'
                    priority = 2
                else:
                    continue
                
                # Check cooldown period
                last_alarm_key = f"{sensor_name}_{severity}"
                if last_alarm_key in self.last_alarm_time:
                    time_since_last = (current_time - self.last_alarm_time[last_alarm_key]).total_seconds()
                    if time_since_last < self.alarm_cooldown:
                        continue
                
                # Create alarm
                alarm = {
                    'timestamp': current_time,
                    'sensor': sensor_name,
                    'severity': severity,
                    'priority': priority,
                    'value': value,
                    'threshold': sensor_data['critical_threshold'] if severity == 'CRITICAL' else sensor_data['alarm_threshold'],
                    'message': f"{sensor_name.replace('_', ' ').title()}: {value:.2f} {sensor_data['unit']} "
                              f"(Threshold: {sensor_data['alarm_threshold']} {sensor_data['unit']})"
                }
                
                new_alarms.append(alarm)
                self.alarms.append(alarm)
                self.last_alarm_time[last_alarm_key] = current_time
                
                logger.warning(f"🚨 {severity} ALARM: {alarm['message']}")
            
            # Check trend-based alarms
            trend_alarms = self._check_trend_alarms()
            new_alarms.extend(trend_alarms)
            
            # Limit alarm history
            if len(self.alarms) > 100:
                self.alarms = self.alarms[-100:]
                
        except Exception as e:
            logger.error(f"Error checking alarms: {e}")
        
        return new_alarms
    
    def _check_trend_alarms(self):
        """Check for trend-based alarms"""
        trend_alarms = []
        current_time = datetime.now()
        
        try:
            for sensor_name, trend_data in self.trend_data.items():
                if trend_data['r_squared'] > 0.7 and trend_data['slope'] > 0:  # Strong upward trend
                    # Check if this could lead to threshold breach
                    current_value = self.sensors[sensor_name]['value']
                    threshold = self.sensors[sensor_name]['alarm_threshold']
                    
                    # Predict if threshold will be breached in next 10 readings
                    predicted_value = current_value + (trend_data['slope'] * 10)
                    
                    if predicted_value > threshold:
                        alarm_key = f"{sensor_name}_trend"
                        if alarm_key not in self.last_alarm_time or \
                           (current_time - self.last_alarm_time[alarm_key]).total_seconds() > 300:  # 5 min cooldown
                            
                            alarm = {
                                'timestamp': current_time,
                                'sensor': sensor_name,
                                'severity': 'MEDIUM',
                                'priority': 3,
                                'value': current_value,
                                'threshold': threshold,
                                'message': f"Trend alarm: {sensor_name.replace('_', ' ').title()} "
                                          f"trending upward (slope: {trend_data['slope']:.3f})"
                            }
                            
                            trend_alarms.append(alarm)
                            self.alarms.append(alarm)
                            self.last_alarm_time[alarm_key] = current_time
                            
        except Exception as e:
            logger.warning(f"Error checking trend alarms: {e}")
        
        return trend_alarms
    
    def _generate_maintenance_recommendations(self):
        """Generate predictive maintenance recommendations"""
        self.maintenance_recommendations.clear()
        
        try:
            # Based on health score
            if self.health_score < 85:
                self.maintenance_recommendations.append({
                    'type': 'General Inspection',
                    'priority': 'Medium' if self.health_score > 70 else 'High',
                    'description': f'Equipment health at {self.health_score:.1f}% - schedule comprehensive inspection',
                    'estimated_days': max(1, int((self.health_score - 60) / 5))
                })
            
            # Based on failure indicators
            if self.failure_indicators['bearing_wear'] > 0.7:
                self.maintenance_recommendations.append({
                    'type': 'Bearing Replacement',
                    'priority': 'High',
                    'description': 'Bearing wear indicators suggest replacement needed',
                    'estimated_days': 7
                })
            
            if self.failure_indicators['belt_degradation'] > 0.6:
                self.maintenance_recommendations.append({
                    'type': 'Belt Inspection',
                    'priority': 'Medium',
                    'description': 'Belt showing signs of wear or misalignment',
                    'estimated_days': 14
                })
            
            if self.failure_indicators['motor_efficiency'] < 0.8:
                self.maintenance_recommendations.append({
                    'type': 'Motor Service',
                    'priority': 'Medium',
                    'description': 'Motor efficiency declining - service recommended',
                    'estimated_days': 21
                })
            
            # Based on operating hours
            if self.operating_hours > 500 and self.operating_hours % 500 < 1:  # Every 500 hours
                self.maintenance_recommendations.append({
                    'type': 'Scheduled Maintenance',
                    'priority': 'Low',
                    'description': f'Routine maintenance due at {self.operating_hours:.0f} operating hours',
                    'estimated_days': 30
                })
                
        except Exception as e:
            logger.warning(f"Error generating maintenance recommendations: {e}")
    
    def _handle_data_transmission(self, new_alarms):
        """Handle data transmission to PHP backend"""
        current_time = time.time()
        
        # Check if it's time to transmit
        if (current_time - self.last_transmission) >= self.transmission_interval:
            try:
                if self.php_connector and self.php_connector.connected:
                    # Prepare sensor data
                    sensor_data = {sensor: data['value'] for sensor, data in self.sensors.items()}
                    
                    # Send sensor data
                    self.php_connector.send_sensor_data(sensor_data)
                    
                    # Send alarms if any
                    if new_alarms:
                        self.php_connector.send_alarms(new_alarms)
                    
                    # Send performance metrics
                    self.php_connector.send_performance_metrics(self.performance_metrics)
                    
                    # Send predictions if available
                    if self.maintenance_recommendations:
                        self.php_connector.send_maintenance_predictions(self.maintenance_recommendations)
                    
                    # Update machine status
                    if self.health_score < 70:
                        status = "Maintenance"
                    elif any(alarm.get('severity') == 'CRITICAL' for alarm in new_alarms):
                        status = "Error"
                    else:
                        status = "Running"
                    
                    self.php_connector.update_machine_status(status, self.health_score)
                    
                    self.last_transmission = current_time
                    
                else:
                    logger.debug("PHP connector not available - running in offline mode")
                    
            except Exception as e:
                logger.error(f"Error transmitting data: {e}")
    
    def get_current_readings(self):
        """Get current sensor readings for display"""
        return {
            sensor: {
                'value': data['value'],
                'unit': data['unit'],
                'status': 'CRITICAL' if data['value'] > data['critical_threshold'] else
                         'ALARM' if data['value'] > data['alarm_threshold'] else
                         'NORMAL'
            }
            for sensor, data in self.sensors.items()
        }
    
    def get_health_summary(self):
        """Get equipment health summary"""
        return {
            'health_score': self.health_score,
            'remaining_useful_life': self.remaining_useful_life,
            'performance_metrics': self.performance_metrics,
            'failure_indicators': self.failure_indicators,
            'maintenance_recommendations': self.maintenance_recommendations,
            'active_alarms': len([a for a in self.alarms[-10:] if a.get('severity') in ['HIGH', 'CRITICAL']])
        }
    
    def print_status(self):
        """Print comprehensive system status"""
        print("\n" + "="*80)
        print(f"📊 ENHANCED SENSOR SYSTEM STATUS - Health: {self.health_score:.1f}%")
        print("="*80)
        
        # Current readings
        print("🔍 CURRENT SENSOR READINGS:")
        for sensor_name, sensor_data in self.sensors.items():
            status_icon = "🔴" if sensor_data['value'] > sensor_data['critical_threshold'] else \
                         "🟡" if sensor_data['value'] > sensor_data['alarm_threshold'] else "🟢"
            print(f"  {status_icon} {sensor_name.replace('_', ' ').title()}: "
                  f"{sensor_data['value']:.2f} {sensor_data['unit']}")
        
        # Performance metrics
        print(f"\n📈 PERFORMANCE METRICS:")
        for metric, value in self.performance_metrics.items():
            if metric == 'energy_consumption':
                print(f"  ⚡ {metric.replace('_', ' ').title()}: {value:.1f} kW")
            else:
                print(f"  📊 {metric.replace('_', ' ').title()}: {value:.1%}")
        
        # Failure predictions
        print(f"\n🔮 FAILURE PREDICTIONS:")
        for indicator, value in self.failure_indicators.items():
            risk_level = "🔴 High" if value > 0.7 else "🟡 Medium" if value > 0.4 else "🟢 Low"
            print(f"  {risk_level} {indicator.replace('_', ' ').title()}: {value:.1%}")
        
        # Maintenance recommendations
        if self.maintenance_recommendations:
            print(f"\n🔧 MAINTENANCE RECOMMENDATIONS:")
            for rec in self.maintenance_recommendations:
                priority_icon = "🔴" if rec['priority'] == 'High' else "🟡" if rec['priority'] == 'Medium' else "🟢"
                print(f"  {priority_icon} {rec['type']}: {rec['description']}")
        
        # Recent alarms
        recent_alarms = [a for a in self.alarms[-5:] if a.get('severity') in ['HIGH', 'CRITICAL']]
        if recent_alarms:
            print(f"\n🚨 RECENT CRITICAL ALARMS:")
            for alarm in recent_alarms:
                print(f"  {alarm['timestamp'].strftime('%H:%M:%S')} - {alarm['message']}")
        
        print("="*80)

    def reset_alarms(self):
        """Reset all alarms (for testing purposes)"""
        self.alarms.clear()
        self.last_alarm_time.clear()
        logger.info("All alarms reset")
    
    def calibrate_sensor(self, sensor_name, calibration_factor):
        """Calibrate a specific sensor"""
        if sensor_name in self.sensors:
            self.sensors[sensor_name]['calibration_factor'] = calibration_factor
            logger.info(f"Sensor {sensor_name} calibrated with factor {calibration_factor}")
        else:
            logger.warning(f"Sensor {sensor_name} not found for calibration")
    
    def set_thresholds(self, sensor_name, alarm_threshold=None, critical_threshold=None):
        """Update sensor thresholds"""
        if sensor_name in self.sensors:
            if alarm_threshold is not None:
                self.sensors[sensor_name]['alarm_threshold'] = alarm_threshold
            if critical_threshold is not None:
                self.sensors[sensor_name]['critical_threshold'] = critical_threshold
            logger.info(f"Updated thresholds for {sensor_name}")
        else:
            logger.warning(f"Sensor {sensor_name} not found for threshold update")
    
    def export_data(self, filename=None):
        """Export sensor data and analytics to file"""
        if filename is None:
            filename = f"sensor_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'machine_id': self.machine_id,
                'operating_hours': self.operating_hours,
                'health_score': self.health_score,
                'current_readings': self.get_current_readings(),
                'performance_metrics': self.performance_metrics,
                'failure_indicators': self.failure_indicators,
                'maintenance_recommendations': self.maintenance_recommendations,
                'recent_alarms': self.alarms[-20:],  # Last 20 alarms
                'trend_data': self.trend_data,
                'sensor_config': {name: {k: v for k, v in data.items() if k != 'value'} 
                                 for name, data in self.sensors.items()}
            }
            
            import json
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Data exported to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return None