import vpython as vp
import math
import random
import time
import threading
import numpy as np
from datetime import datetime

class ConveyorBeltSystem:
    def __init__(self):
        # Create the scene
        self.scene = vp.canvas(title='Smart Conveyor Belt - IoT Monitoring System',
                              width=1400, height=900,
                              center=vp.vector(0, 3, 0),
                              background=vp.color.white)
        
        # Conveyor parameters
        self.length = 20
        self.width = 3
        self.height = 1.5
        self.belt_speed = 1.5  # m/s
        self.max_speed = 3.0
        self.min_speed = 0.5
        
        # Material parameters
        self.material_particles = []
        self.material_count = 0
        self.max_material = 200
        self.loading_rate = 0.3  # particles per second
        
        # Operational data
        self.operating_time = 0
        self.last_update_time = time.time()
        
        # Initialize systems
        self.sensor_system = SensorSystem()
        self.predictive_maintenance = PredictiveMaintenance()
        self.control_system = ControlSystem()
        
        # Create physical components
        self.create_structure()
        self.create_belt_system()
        self.create_material_flow()
        self.create_hmi_displays()
        self.create_sensor_visuals()
        
        # Animation parameters
        self.dt = 0.02
        
        # Start monitoring thread
        self.start_monitoring()
        self.animate()

    def create_structure(self):
        """Create the main structural components"""
        # Base foundation
        vp.box(pos=vp.vector(0, -0.2, 0), 
              size=vp.vector(self.length + 4, 0.4, self.width + 1),
              color=vp.color.gray(0.4))
        
        # Support legs
        for x in [-self.length/2, self.length/2]:
            vp.box(pos=vp.vector(x, 0.5, 0),
                  size=vp.vector(0.3, 1.4, 0.3),
                  color=vp.color.gray(0.5))
            
        # Motor housing
        self.motor_housing = vp.box(
            pos=vp.vector(-self.length/2 - 1, 0.5, 0),
            size=vp.vector(1.5, 1, 1.5),
            color=vp.color.blue
        )
        
        # Motor
        self.motor = vp.cylinder(
            pos=vp.vector(-self.length/2 - 1.5, 0.5, 0),
            axis=vp.vector(0.5, 0, 0),
            radius=0.4,
            color=vp.color.red
        )
        
        # Loading hopper
        hopper_height = 4
        hopper_width = 3
        hopper = vp.compound([
            vp.box(pos=vp.vector(-self.length/2, hopper_height/2 + 0.5, 0),
                  size=vp.vector(hopper_width, hopper_height, hopper_width),
                  color=vp.color.orange),
            vp.cone(pos=vp.vector(-self.length/2, 0.5, 0),
                  axis=vp.vector(0, -1, 0),
                  radius=1.2,
                  color=vp.color.orange)
        ])
        
        # Discharge chute
        vp.box(pos=vp.vector(self.length/2 + 1, 1.5, 0),
              size=vp.vector(1.5, 1, 1.5),
              color=vp.color.green)

    def create_belt_system(self):
        """Create the conveyor belt system"""
        # Drive pulley
        self.drive_pulley = vp.cylinder(
            pos=vp.vector(-self.length/2, 0.8, 0),
            axis=vp.vector(0, 0, self.width),
            radius=0.6,
            color=vp.color.gray(0.3),
            texture=vp.textures.metal
        )
        
        # Idler pulley
        self.idler_pulley = vp.cylinder(
            pos=vp.vector(self.length/2, 0.8, 0),
            axis=vp.vector(0, 0, self.width),
            radius=0.6,
            color=vp.color.gray(0.3),
            texture=vp.textures.metal
        )
        
        # Belt
        belt_thickness = 0.1
        self.belt = vp.box(
            pos=vp.vector(0, 0.8, 0),
            size=vp.vector(self.length, belt_thickness, self.width),
            color=vp.color.gray(0.7),
            texture=vp.textures.rug
        )
        
        # Belt sides
        for z in [-self.width/2 + 0.1, self.width/2 - 0.1]:
            vp.box(
                pos=vp.vector(0, 0.85, z),
                size=vp.vector(self.length, belt_thickness*1.5, 0.1),
                color=vp.color.red
            )
        
        # Support rollers
        roller_count = 10
        for i in range(roller_count):
            pos_x = -self.length/2 + (i + 0.5) * (self.length / roller_count)
            vp.cylinder(
                pos=vp.vector(pos_x, 0.4, -self.width/2),
                axis=vp.vector(0, 0, self.width),
                radius=0.15,
                color=vp.color.gray(0.5)
            )

    def create_material_flow(self):
        """Create material particles representing crushed sand"""
        self.material_particles = []
        
        # Initial material in hopper
        for _ in range(20):
            self.add_material_particle(hopper=True)

    def add_material_particle(self, hopper=False):
        """Add a new material particle"""
        if hopper:
            # Position in hopper
            pos = vp.vector(
                -self.length/2 + random.uniform(-1, 1),
                2 + random.uniform(0, 2),
                random.uniform(-1, 1)
            )
        else:
            # Position at loading point
            pos = vp.vector(
                -self.length/2 + 0.5,
                1.2,
                random.uniform(-self.width/2 + 0.3, self.width/2 - 0.3)
            )
            
        particle = vp.sphere(
            pos=pos,
            radius=0.15,
            color=vp.vector(random.uniform(0.7, 1.0), 
                          random.uniform(0.6, 0.8), 
                          random.uniform(0.1, 0.3)),  # Sandy color
            make_trail=False
        )
        
        if hopper:
            particle.velocity = vp.vector(0, 0, 0)
        else:
            particle.velocity = vp.vector(self.belt_speed, 0, 0)
            
        self.material_particles.append(particle)
        self.material_count += 1

    def create_sensor_visuals(self):
        """Create visual indicators for sensors"""
        # Speed sensor (on motor)
        self.speed_sensor_indicator = vp.box(
            pos=vp.vector(-self.length/2 - 1.5, 1.2, 0),
            size=vp.vector(0.2, 0.2, 0.2),
            color=vp.color.green
        )
        
        # Load sensor (under belt)
        self.load_sensor_indicator = vp.box(
            pos=vp.vector(0, 0.2, 0),
            size=vp.vector(0.3, 0.1, 0.3),
            color=vp.color.purple
        )
        
        # Temperature sensor (on motor)
        self.temp_sensor_indicator = vp.sphere(
            pos=vp.vector(-self.length/2 - 1, 1.2, 0.7),
            radius=0.1,
            color=vp.color.red
        )
        
        # Vibration sensor (on structure)
        self.vibration_sensor_indicator = vp.box(
            pos=vp.vector(-self.length/2 + 2, 0.8, self.width/2 + 0.2),
            size=vp.vector(0.2, 0.2, 0.2),
            color=vp.color.orange
        )
        
        # Current sensor (on electrical panel)
        self.current_sensor_indicator = vp.cylinder(
            pos=vp.vector(-self.length/2 - 1, 0.5, -1),
            axis=vp.vector(0, 0, 0.2),
            radius=0.1,
            color=vp.color.blue
        )
        
        # Belt slippage indicator
        self.slippage_sensor_indicator = vp.box(
            pos=vp.vector(self.length/2 - 1, 1.2, 0),
            size=vp.vector(0.2, 0.2, 0.2),
            color=vp.color.yellow
        )

    def create_hmi_displays(self):
        """Create HMI display panels"""
        # Main control panel
        panel = vp.box(
            pos=vp.vector(0, 5, -self.width/2 - 1),
            size=vp.vector(10, 6, 0.1),
            color=vp.color.gray(0.2)
        )
        
        # Sensor value displays
        self.sensor_displays = {}
        sensors = [
            ('speed', 'Speed (m/s)', vp.vector(-3, 6.5, -self.width/2 - 1.1)),
            ('load', 'Load (%)', vp.vector(-3, 5.5, -self.width/2 - 1.1)),
            ('temperature', 'Temp (°C)', vp.vector(-3, 4.5, -self.width/2 - 1.1)),
            ('vibration', 'Vibration (m/s²)', vp.vector(0, 6.5, -self.width/2 - 1.1)),
            ('current', 'Current (A)', vp.vector(0, 5.5, -self.width/2 - 1.1)),
            ('slippage', 'Slippage (%)', vp.vector(0, 4.5, -self.width/2 - 1.1))
        ]
        
        for name, label, pos in sensors:
            # Label
            vp.text(text=label, pos=pos + vp.vector(0, -0.3, 0), 
                   color=vp.color.white, height=0.3)
            
            # Value display
            display = vp.text(text="0.00", pos=pos, 
                             color=vp.color.green, height=0.5)
            self.sensor_displays[name] = display
        
        # Maintenance status
        self.maintenance_display = vp.text(
            text="System Health: 100%", 
            pos=vp.vector(0, 3, -self.width/2 - 1.1),
            color=vp.color.green,
            height=0.4
        )
        
        # Alarms display
        self.alarm_display = vp.wtext(
            text="<b>ALARMS:</b> None",
            pos=self.scene.title_anchor,
            color=vp.color.red
        )

    def start_monitoring(self):
        """Start the monitoring system in a separate thread"""
        def monitoring_loop():
            while True:
                # Calculate material on belt
                belt_material = sum(1 for p in self.material_particles 
                                  if -self.length/2 < p.pos.x < self.length/2)
                
                # Update sensors
                self.sensor_system.update_sensors(
                    belt_speed=self.belt_speed,
                    material_count=belt_material,
                    operating_time=self.operating_time
                )
                
                # Run predictive maintenance analysis
                self.predictive_maintenance.analyze_trends(self.sensor_system)
                
                # Update control system
                self.control_system.update_control(self.sensor_system)
                
                # Update HMI displays
                self.update_hmi_displays()
                
                # Print status every 5 seconds
                current_time = time.time()
                if current_time - self.last_update_time > 5:
                    self.print_status()
                    self.last_update_time = current_time
                
                time.sleep(0.5)  # Update twice per second
        
        monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitoring_thread.start()

    def update_hmi_displays(self):
        """Update HMI display based on sensor values"""
        # Update sensor value displays
        for sensor_name, display in self.sensor_displays.items():
            value = self.sensor_system.sensors[sensor_name]['value']
            unit = self.sensor_system.sensors[sensor_name]['unit']
            
            # Color coding based on thresholds
            threshold = self.sensor_system.sensors[sensor_name]['alarm_threshold']
            if value > threshold:
                color = vp.color.red
            elif value > threshold * 0.8:
                color = vp.color.yellow
            else:
                color = vp.color.green
                
            display.text = f"{value:.2f}"
            display.color = color
        
        # Update maintenance display
        health = self.predictive_maintenance.maintenance_score
        if health > 80:
            color = vp.color.green
        elif health > 60:
            color = vp.color.yellow
        else:
            color = vp.color.red
            
        self.maintenance_display.text = f"System Health: {health:.1f}%"
        self.maintenance_display.color = color
        
        # Update alarms
        if self.sensor_system.alarms:
            latest_alarm = self.sensor_system.alarms[-1]
            alarm_text = (f"<b>ALARM:</b> {latest_alarm['sensor']} = "
                         f"{latest_alarm['value']:.2f} {latest_alarm['unit']} "
                         f"(Threshold: {latest_alarm['threshold']})")
            self.alarm_display.text = alarm_text
        else:
            self.alarm_display.text = "<b>ALARMS:</b> None"

    def print_status(self):
        """Print current system status"""
        print("\n" + "="*80)
        print(f"📊 CONVEYOR BELT STATUS - Runtime: {self.operating_time:.0f}s")
        print("="*80)
        
        # Sensor readings
        print("🔍 SENSOR READINGS:")
        for sensor_name, sensor_data in self.sensor_system.sensors.items():
            status = "🔴" if sensor_data['value'] > sensor_data['alarm_threshold'] else "🟢"
            print(f"  {status} {sensor_name.title()}: {sensor_data['value']:.2f} {sensor_data['unit']}")
        
        # Control system status
        print(f"\n🎛️ CONTROL SYSTEM:")
        print(f"  Auto Mode: {'ON' if self.control_system.auto_mode else 'OFF'}")
        print(f"  Current Speed: {self.belt_speed:.2f} m/s")
        print(f"  Emergency Stop: {'ACTIVE' if self.control_system.emergency_stop else 'NORMAL'}")
        
        # Predictive maintenance
        print(f"\n🔧 PREDICTIVE MAINTENANCE:")
        print(f"  Equipment Health: {self.predictive_maintenance.maintenance_score:.1f}%")
        if self.predictive_maintenance.maintenance_recommendations:
            print("  Recommendations:")
            for rec in self.predictive_maintenance.maintenance_recommendations:
                print(f"    - {rec}")
        
        # Recent alarms
        if self.sensor_system.alarms:
            recent_alarms = self.sensor_system.alarms[-3:]  # Last 3 alarms
            print(f"\n🚨 RECENT ALARMS:")
            for alarm in recent_alarms:
                print(f"  {alarm['timestamp'].strftime('%H:%M:%S')} - {alarm['sensor']}: "
                      f"{alarm['value']:.2f} (Severity: {alarm['severity']})")

    def update_material_flow(self):
        """Update material particle physics"""
        # Add new material if not at max capacity
        if (self.material_count < self.max_material and 
            random.random() < self.loading_rate * self.dt and
            not self.control_system.emergency_stop):
            self.add_material_particle()
        
        # Update existing material
        for particle in self.material_particles:
            # Only move material that's on the belt
            if -self.length/2 < particle.pos.x < self.length/2:
                particle.pos.x += self.belt_speed * self.dt
                
                # Add some random movement
                particle.pos.z += random.uniform(-0.01, 0.01)
                
                # Remove material that reached the end
                if particle.pos.x > self.length/2:
                    particle.visible = False
                    self.material_count -= 1

    def animate(self):
        """Main animation loop"""
        print("🚀 Smart Conveyor Belt System Started!")
        print("📡 IoT sensors active - monitoring in real-time")
        print("🤖 Predictive maintenance system online")
        print("⚡ Automatic control system engaged")
        
        while True:
            vp.rate(50)  # 50 fps
            
            if not self.control_system.emergency_stop:
                self.operating_time += self.dt
                
                # Update belt speed based on control system
                target_speed = self.control_system.target_speed
                self.belt_speed = target_speed
                
                # Rotate pulleys
                rotation_speed = self.belt_speed * self.dt / 0.6
                self.drive_pulley.rotate(angle=rotation_speed, axis=vp.vector(0, 0, 1))
                self.idler_pulley.rotate(angle=rotation_speed, axis=vp.vector(0, 0, 1))
                
                # Update material flow
                self.update_material_flow()
            
            # Clean up invisible particles
            self.material_particles = [p for p in self.material_particles if p.visible]

class SensorSystem:
    """Simulates various sensors for the conveyor belt"""
    
    def __init__(self):
        self.sensors = {
            'speed': {'value': 0, 'unit': 'm/s', 'min': 0, 'max': 4, 'alarm_threshold': 3.2},
            'load': {'value': 0, 'unit': '%', 'min': 0, 'max': 100, 'alarm_threshold': 85},
            'temperature': {'value': 25, 'unit': '°C', 'min': 20, 'max': 80, 'alarm_threshold': 70},
            'vibration': {'value': 0, 'unit': 'm/s²', 'min': 0, 'max': 20, 'alarm_threshold': 15},
            'current': {'value': 0, 'unit': 'A', 'min': 0, 'max': 50, 'alarm_threshold': 45},
            'slippage': {'value': 0, 'unit': '%', 'min': 0, 'max': 10, 'alarm_threshold': 8}
        }
        self.history = {sensor: [] for sensor in self.sensors.keys()}
        self.alarms = []
        
    def update_sensors(self, belt_speed, material_count, operating_time):
        """Update sensor values based on conveyor state"""
        # Speed sensor
        self.sensors['speed']['value'] = belt_speed + random.uniform(-0.05, 0.05)
        
        # Load sensor (percentage of max capacity)
        max_capacity = 50  # Max material units on belt
        self.sensors['load']['value'] = min(100, (material_count / max_capacity) * 100)
        
        # Temperature sensor (increases with operation time and load)
        ambient_temp = 25
        load_factor = (self.sensors['load']['value'] / 100) * 25
        time_factor = min(operating_time / 3600, 1) * 15  # Max 15°C increase per hour
        self.sensors['temperature']['value'] = ambient_temp + load_factor + time_factor + random.uniform(-1, 1)
        
        # Vibration sensor (increases with speed and wear)
        speed_vibration = (belt_speed / 3) * 10
        wear_vibration = min(operating_time / 7200, 1) * 6  # Wear factor
        self.sensors['vibration']['value'] = speed_vibration + wear_vibration + random.uniform(-0.5, 0.5)
        
        # Current sensor (based on load and temperature)
        base_current = 5
        load_current = (self.sensors['load']['value'] / 100) * 25
        temp_current = max(0, (self.sensors['temperature']['value'] - 40) * 0.5)
        self.sensors['current']['value'] = base_current + load_current + temp_current + random.uniform(-1, 1)
        
        # Belt slippage (increases with load and wear)
        base_slippage = 0.5
        load_slippage = (self.sensors['load']['value'] / 100) * 5
        wear_slippage = min(operating_time / 10000, 1) * 4
        self.sensors['slippage']['value'] = base_slippage + load_slippage + wear_slippage + random.uniform(-0.2, 0.2)
        
        # Ensure values stay within realistic bounds
        for sensor_name, sensor_data in self.sensors.items():
            sensor_data['value'] = max(sensor_data['min'], 
                                     min(sensor_data['max'], sensor_data['value']))
        
        # Store history
        timestamp = datetime.now()
        for sensor_name, sensor_data in self.sensors.items():
            self.history[sensor_name].append({
                'timestamp': timestamp,
                'value': sensor_data['value']
            })
            # Keep only last 100 readings
            if len(self.history[sensor_name]) > 100:
                self.history[sensor_name].pop(0)
        
        # Check for alarms
        self.check_alarms()
    
    def check_alarms(self):
        """Check for alarm conditions"""
        current_time = datetime.now()
        for sensor_name, sensor_data in self.sensors.items():
            if sensor_data['value'] > sensor_data['alarm_threshold']:
                alarm = {
                    'timestamp': current_time,
                    'sensor': sensor_name,
                    'value': sensor_data['value'],
                    'unit': sensor_data['unit'],
                    'threshold': sensor_data['alarm_threshold'],
                    'severity': 'HIGH' if sensor_data['value'] > sensor_data['alarm_threshold'] * 1.1 else 'MEDIUM'
                }
                self.alarms.append(alarm)
                print(f"🚨 ALARM: {sensor_name} = {sensor_data['value']:.2f} {sensor_data['unit']} "
                      f"(Threshold: {sensor_data['alarm_threshold']} {sensor_data['unit']})")

class PredictiveMaintenance:
    """Predictive maintenance system using sensor data"""
    
    def __init__(self):
        self.maintenance_score = 100  # Start at 100% health
        self.maintenance_recommendations = []
        
    def analyze_trends(self, sensor_system):
        """Analyze sensor trends for predictive maintenance"""
        # Calculate health degradation based on sensor values
        degradation_factors = 0
        
        # Vibration impact
        vib_ratio = sensor_system.sensors['vibration']['value'] / 15
        if vib_ratio > 0.7:
            degradation_factors += (vib_ratio - 0.7) * 15
            
        # Temperature impact
        temp_ratio = sensor_system.sensors['temperature']['value'] / 70
        if temp_ratio > 0.8:
            degradation_factors += (temp_ratio - 0.8) * 10
            
        # Slippage impact
        slip_ratio = sensor_system.sensors['slippage']['value'] / 8
        if slip_ratio > 0.8:
            degradation_factors += (slip_ratio - 0.8) * 12
            
        # Current impact (indicates motor strain)
        curr_ratio = sensor_system.sensors['current']['value'] / 45
        if curr_ratio > 0.8:
            degradation_factors += (curr_ratio - 0.8) * 8
        
        # Update maintenance score
        self.maintenance_score = max(0, self.maintenance_score - degradation_factors * 0.01)
        
        # Generate recommendations
        self.maintenance_recommendations.clear()
        
        if self.maintenance_score < 90:
            self.maintenance_recommendations.append("Schedule routine inspection")
        if self.maintenance_score < 80:
            self.maintenance_recommendations.append("Check belt tension and alignment")
        if self.maintenance_score < 70:
            self.maintenance_recommendations.append("Lubricate bearings and inspect pulleys")
        if self.maintenance_score < 60:
            self.maintenance_recommendations.append("⚠️ URGENT: Check for belt wear and misalignment")
        if self.maintenance_score < 50:
            self.maintenance_recommendations.append("🔴 CRITICAL: Shutdown required for belt replacement")

class ControlSystem:
    """Automated control system for conveyor belt"""
    
    def __init__(self):
        self.auto_mode = True
        self.target_speed = 1.5  # m/s
        self.emergency_stop = False
        
    def update_control(self, sensor_system):
        """Update control parameters based on sensor feedback"""
        if not self.auto_mode or self.emergency_stop:
            return
        
        # Speed control based on load
        load_ratio = sensor_system.sensors['load']['value'] / 100
        if load_ratio > 0.9:
            self.target_speed = 0.8  # Reduce speed for high load
        elif load_ratio < 0.3:
            self.target_speed = 2.0   # Increase speed for low load
        else:
            self.target_speed = 1.5     # Normal speed
            
        # Apply limits
        self.target_speed = max(0.5, min(3.0, self.target_speed))
            
        # Emergency conditions
        if (sensor_system.sensors['temperature']['value'] > 75 or
            sensor_system.sensors['vibration']['value'] > 18 or
            sensor_system.sensors['current']['value'] > 48 or
            sensor_system.sensors['slippage']['value'] > 9):
            self.emergency_stop = True
            print("🛑 EMERGENCY STOP ACTIVATED - Critical sensor values detected!")

# Create and run the conveyor belt system
if __name__ == "__main__":
    print("🏭 Starting Smart Conveyor Belt with IoT Monitoring...")
    print("📋 Features:")
    print("  ✓ Real-time sensor monitoring (Speed, Load, Temperature, Vibration, Current, Slippage)")
    print("  ✓ Predictive maintenance analysis")
    print("  ✓ Automatic control system")
    print("  ✓ Alarm management")
    print("  ✓ Equipment health tracking")
    print("\n🔧 Dependencies required:")
    print("  pip install vpython numpy")
    print("\nClose the VPython window to exit.")
    
    try:
        conveyor = ConveyorBeltSystem()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have the required dependencies installed.")
        print("Run: pip install vpython numpy")