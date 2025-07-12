"""
Python Connector for PHP Backend Integration
Handles all communication between VPython simulation and PHP dashboard
"""

import requests
import json
import time
import threading
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PHPConnector:
    """Handles communication with PHP backend API"""
    
    def __init__(self, base_url: str = "http://localhost/bucket_elevator_system/api/endpoints"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.connected = False
        self.last_ping = 0
        self.ping_interval = 30  # Ping every 30 seconds
        self.retry_count = 0
        self.max_retries = 3
        self.timeout = 10
        
        # Connection statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'last_success': None,
            'last_failure': None
        }
        
        # Configure session
        self.session.headers.update({
            'User-Agent': 'BucketElevator-IoT-System/1.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Test initial connection
        self.test_connection()
        
        # Start background health monitoring
        self._start_health_monitor()
    
    def test_connection(self) -> bool:
        """Test connection to PHP backend with retry logic"""
        for attempt in range(self.max_retries):
            try:
                self.stats['total_requests'] += 1
                response = self.session.get(
                    f"{self.base_url}/machines.php", 
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    self.connected = True
                    self.retry_count = 0
                    self.stats['successful_requests'] += 1
                    self.stats['last_success'] = datetime.now()
                    logger.info("✅ Connected to PHP backend successfully!")
                    return True
                else:
                    logger.warning(f"⚠️ PHP backend responded with status: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.stats['failed_requests'] += 1
                self.stats['last_failure'] = datetime.now()
                logger.warning(f"❌ Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        self.connected = False
        self.retry_count += 1
        logger.error("🔄 Running in offline mode - backend unavailable")
        return False
    
    def _start_health_monitor(self):
        """Start background thread for connection health monitoring"""
        def health_monitor():
            while True:
                try:
                    current_time = time.time()
                    if current_time - self.last_ping > self.ping_interval:
                        if not self.connected:
                            self.test_connection()
                        else:
                            # Simple health check
                            self._health_check()
                        self.last_ping = current_time
                    
                    time.sleep(10)  # Check every 10 seconds
                    
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
                    time.sleep(30)
        
        health_thread = threading.Thread(target=health_monitor, daemon=True)
        health_thread.start()
        logger.info("Background health monitor started")
    
    def _health_check(self):
        """Perform lightweight health check"""
        try:
            response = self.session.get(
                f"{self.base_url}/machines.php?id=1",
                timeout=5
            )
            if response.status_code != 200:
                self.connected = False
                logger.warning("Health check failed - marking as disconnected")
        except:
            self.connected = False
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request with error handling and retries"""
        if not self.connected and method != 'GET':
            logger.debug(f"Skipping {method} request to {endpoint} - not connected")
            return None
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            self.stats['total_requests'] += 1
            
            if method == 'GET':
                response = self.session.get(url, timeout=self.timeout)
            elif method == 'POST':
                response = self.session.post(url, json=data, timeout=self.timeout)
            elif method == 'PUT':
                response = self.session.put(url, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code in [200, 201]:
                self.stats['successful_requests'] += 1
                self.stats['last_success'] = datetime.now()
                return response.json()
            else:
                self.stats['failed_requests'] += 1
                logger.warning(f"Request failed: {response.status_code} - {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.stats['failed_requests'] += 1
            self.stats['last_failure'] = datetime.now()
            logger.error(f"Request error: {e}")
            
            # Mark as disconnected on repeated failures
            if self.stats['failed_requests'] % 5 == 0:
                self.connected = False
            
            return None
    
    def send_sensor_data(self, sensor_data: Dict[str, float], machine_id: int = 1) -> bool:
        """Send sensor data to backend"""
        payload = {
            "sensor_data": {
                "speed": round(sensor_data.get("speed_rpm", 0), 2),
                "load": round(sensor_data.get("load_kg", 0), 2),
                "temperature": round(sensor_data.get("temperature_c", 0), 2),
                "vibration": round(sensor_data.get("vibration_ms2", 0), 2),
                "current": round(sensor_data.get("current_a", 0), 2)
            },
            "machine_id": machine_id,
            "timestamp": datetime.now().isoformat()
        }
        
        result = self._make_request("python_integration.php", "POST", payload)
        
        if result and result.get("success"):
            logger.debug("Sensor data sent successfully")
            return True
        
        return False
    
    def send_alarms(self, alarms: List[Dict], machine_id: int = 1) -> bool:
        """Send alarms to backend"""
        if not alarms:
            return True
        
        formatted_alarms = []
        for alarm in alarms:
            formatted_alarms.append({
                "type": alarm.get("severity", "MEDIUM"),
                "priority": alarm.get("priority", 3),
                "message": alarm.get("message", "Unknown alarm"),
                "sensor": alarm.get("sensor", "unknown"),
                "threshold_value": alarm.get("threshold", 0),
                "actual_value": alarm.get("value", 0)
            })
        
        payload = {
            "alarms": formatted_alarms,
            "machine_id": machine_id
        }
        
        result = self._make_request("python_integration.php", "POST", payload)
        
        if result and result.get("success"):
            logger.info(f"Sent {len(alarms)} alarms to dashboard")
            return True
        
        return False
    
    def update_machine_status(self, status: str, health_score: Optional[float] = None, machine_id: int = 1) -> bool:
        """Update machine status and health score"""
        payload = {
            "machine_status": status,
            "machine_id": machine_id
        }
        
        if health_score is not None:
            payload["health_score"] = round(health_score, 2)
        
        result = self._make_request("python_integration.php", "POST", payload)
        
        if result and result.get("success"):
            logger.debug(f"Updated machine status: {status}")
            return True
        
        return False
    
    def send_performance_metrics(self, metrics: Dict[str, float], machine_id: int = 1) -> bool:
        """Send performance metrics to backend"""
        payload = {
            "performance_metrics": {
                "efficiency": round(metrics.get("efficiency", 0), 3),
                "uptime": round(metrics.get("uptime", 0), 3),
                "throughput": round(metrics.get("throughput", 0), 3),
                "energy_consumption": round(metrics.get("energy_consumption", 0), 2)
            },
            "machine_id": machine_id
        }
        
        result = self._make_request("python_integration.php", "POST", payload)
        
        if result and result.get("success"):
            logger.debug("Performance metrics sent successfully")
            return True
        
        return False
    
    def send_maintenance_predictions(self, predictions: List[Dict], machine_id: int = 1) -> bool:
        """Send predictive maintenance recommendations"""
        if not predictions:
            return True
        
        formatted_predictions = []
        for pred in predictions:
            formatted_predictions.append({
                "type": pred.get("type", "Unknown"),
                "priority": pred.get("priority", "Medium"),
                "description": pred.get("description", ""),
                "confidence": "High",  # Default confidence
                "predicted_date": (datetime.now() + 
                                 timedelta(days=pred.get("estimated_days", 7))).strftime("%Y-%m-%d")
            })
        
        payload = {
            "maintenance_predictions": formatted_predictions,
            "machine_id": machine_id
        }
        
        result = self._make_request("python_integration.php", "POST", payload)
        
        if result and result.get("success"):
            logger.info(f"Sent {len(predictions)} maintenance predictions")
            return True
        
        return False
    
    def get_machine_config(self, machine_id: int = 1) -> Optional[Dict]:
        """Get machine configuration from backend"""
        result = self._make_request(f"python_integration.php?machine_id={machine_id}&config=machine")
        
        if result and result.get("success"):
            return result.get("data", {}).get("machine")
        
        return None
    
    def get_sensor_config(self, machine_id: int = 1) -> Optional[List[Dict]]:
        """Get sensor configuration from backend"""
        result = self._make_request(f"python_integration.php?machine_id={machine_id}&config=sensors")
        
        if result and result.get("success"):
            return result.get("data", {}).get("sensors", [])
        
        return None
    
    def get_alarm_thresholds(self, machine_id: int = 1) -> Optional[Dict]:
        """Get alarm thresholds from backend"""
        result = self._make_request(f"python_integration.php?machine_id={machine_id}&config=thresholds")
        
        if result and result.get("success"):
            return result.get("data", {}).get("thresholds", {})
        
        return None
    
    def authenticate_user(self, username: str, password: str, role: str = "operator") -> Optional[Dict]:
        """Authenticate user with backend"""
        payload = {
            "username": username,
            "password": password,
            "role": role
        }
        
        result = self._make_request("auth.php", "POST", payload)
        
        if result and result.get("success"):
            logger.info(f"User {username} authenticated successfully")
            return result.get("user")
        
        return None
    
    def get_recent_alarms(self, machine_id: int = 1, limit: int = 10) -> List[Dict]:
        """Get recent alarms from backend"""
        result = self._make_request(f"alarms.php?machine_id={machine_id}&limit={limit}")
        
        if result and result.get("success"):
            return result.get("data", [])
        
        return []
    
    def acknowledge_alarm(self, alarm_id: int, user_id: Optional[int] = None) -> bool:
        """Acknowledge an alarm"""
        payload = {
            "id": alarm_id,
            "acknowledged": True
        }
        
        if user_id:
            payload["acknowledged_by"] = user_id
        
        result = self._make_request("alarms.php", "PUT", payload)
        
        if result and result.get("success"):
            logger.info(f"Alarm {alarm_id} acknowledged")
            return True
        
        return False
    
    def get_maintenance_schedule(self, machine_id: int = 1, days_ahead: int = 30) -> List[Dict]:
        """Get upcoming maintenance schedule"""
        from datetime import timedelta
        
        date_from = datetime.now().strftime("%Y-%m-%d")
        date_to = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        result = self._make_request(
            f"maintenance.php?type=schedule&machine_id={machine_id}&date_from={date_from}&date_to={date_to}"
        )
        
        if result and result.get("success"):
            return result.get("data", {}).get("schedule", [])
        
        return []
    
    def create_maintenance_task(self, machine_id: int, task_type: str, description: str, 
                               scheduled_date: str, technician_id: Optional[int] = None) -> bool:
        """Create a new maintenance task"""
        payload = {
            "machine_id": machine_id,
            "maintenance_type": task_type,
            "description": description,
            "scheduled_date": scheduled_date
        }
        
        if technician_id:
            payload["technician_id"] = technician_id
        
        result = self._make_request("maintenance.php", "POST", payload)
        
        if result and result.get("success"):
            logger.info(f"Maintenance task created: {task_type}")
            return True
        
        return False
    
    def generate_report(self, report_type: str = "summary", machine_id: int = 1, 
                       period: str = "24h") -> Optional[Dict]:
        """Generate and retrieve a report"""
        # First, generate the report
        payload = {
            "report_type": report_type,
            "machine_id": machine_id,
            "period": period,
            "report_id": f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        result = self._make_request("reports.php", "POST", payload)
        
        if result and result.get("success"):
            logger.info(f"Generated {report_type} report for {period}")
            return result.get("data")
        
        return None
    
    def get_connection_stats(self) -> Dict:
        """Get connection statistics"""
        uptime = (datetime.now() - (self.stats['last_success'] or datetime.now())).total_seconds()
        success_rate = (self.stats['successful_requests'] / max(1, self.stats['total_requests'])) * 100
        
        return {
            "connected": self.connected,
            "total_requests": self.stats['total_requests'],
            "successful_requests": self.stats['successful_requests'],
            "failed_requests": self.stats['failed_requests'],
            "success_rate": round(success_rate, 2),
            "last_success": self.stats['last_success'],
            "last_failure": self.stats['last_failure'],
            "base_url": self.base_url
        }
    
    def test_all_endpoints(self) -> Dict[str, bool]:
        """Test all API endpoints for connectivity"""
        endpoints = {
            "machines": "machines.php",
            "sensor_data": "sensor_data.php", 
            "alarms": "alarms.php",
            "reports": "reports.php",
            "maintenance": "maintenance.php",
            "python_integration": "python_integration.php"
        }
        
        results = {}
        
        for name, endpoint in endpoints.items():
            try:
                response = self.session.get(f"{self.base_url}/{endpoint}", timeout=5)
                results[name] = response.status_code == 200
            except:
                results[name] = False
        
        return results
    
    def close(self):
        """Close the connector and cleanup resources"""
        if hasattr(self, 'session'):
            self.session.close()
        logger.info("PHP Connector closed")

# Helper function for easy integration
def create_connector(base_url: str = None) -> PHPConnector:
    """Create and return a configured PHP connector"""
    if base_url is None:
        base_url = "http://localhost/bucket_elevator_system/api/endpoints"
    
    return PHPConnector(base_url)

# Integration example for main9.py
def integrate_with_main9():
    """
    Example integration code for your main9.py file
    
    Add this to your main9.py:
    
    # At the top of main9.py, add:
    from enhanced_sensor_system import EnhancedSensorSystem
    from python_connector import create_connector
    
    # In your SmartBucketElevator.__init__ method, replace:
    # self.sensor_system = SensorSystem()
    # with:
    connector = create_connector()
    self.sensor_system = EnhancedSensorSystem(machine_id=1, php_connector=connector)
    
    # The enhanced system will automatically:
    # - Send sensor data to your dashboard
    # - Generate and transmit alarms
    # - Update machine status and health
    # - Provide predictive maintenance recommendations
    """
    pass

if __name__ == "__main__":
    # Test the connector
    print("🧪 Testing PHP Connector...")
    
    connector = create_connector()
    
    if connector.connected:
        print("✅ Connection successful!")
        
        # Test endpoints
        print("\n🔍 Testing endpoints...")
        endpoint_results = connector.test_all_endpoints()
        for endpoint, status in endpoint_results.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {endpoint}")
        
        # Show connection stats
        print("\n📊 Connection Statistics:")
        stats = connector.get_connection_stats()
        for key, value in stats.items():
            if key not in ['last_success', 'last_failure']:
                print(f"  {key}: {value}")
    
    else:
        print("❌ Connection failed - check your XAMPP server and API endpoints")
    
    connector.close()