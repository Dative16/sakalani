import vpython as vp
import math
import random
import time
import threading
import numpy as np
from datetime import datetime
import json
import os
import cv2
from PIL import Image
import imageio

from enhanced_sensor_system import EnhancedSensorSystem
from python_connector import create_connector

class VideoRecorder:
    """Records VPython simulation to MP4 video"""
    
    def __init__(self, scene, filename="bucket_elevator_simulation", fps=30, duration=60):
        self.scene = scene
        self.filename = filename
        self.fps = fps
        self.duration = duration
        self.frames = []
        self.recording = False
        self.frame_count = 0
        self.max_frames = fps * duration
        
        # Create output directory
        self.output_dir = "simulation_videos"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def start_recording(self):
        """Start video recording"""
        self.recording = True
        self.frames = []
        self.frame_count = 0
        print(f"🎬 Started recording video: {self.filename}.mp4")
        print(f"📹 Recording {self.duration}s at {self.fps} FPS")
    
    def capture_frame(self):
        """Capture current frame from VPython scene"""
        if not self.recording or self.frame_count >= self.max_frames:
            return False
        
        try:
            # Capture screenshot from VPython canvas
            # Note: This requires the scene to be visible and active
            self.scene.capture(f"temp_frame_{self.frame_count:06d}")
            self.frame_count += 1
            
            if self.frame_count >= self.max_frames:
                self.stop_recording()
                return False
            
            return True
        except Exception as e:
            print(f"Frame capture error: {e}")
            return False
    
    def stop_recording(self):
        """Stop recording and create MP4 file"""
        if not self.recording:
            return
        
        self.recording = False
        print("🎬 Stopping recording and creating MP4...")
        
        try:
            self.create_mp4_from_captures()
            print(f"✅ Video saved: {self.output_dir}/{self.filename}.mp4")
        except Exception as e:
            print(f"❌ Error creating video: {e}")
    
    def create_mp4_from_captures(self):
        """Create MP4 from captured frames"""
        # Collect all temporary frame files
        frame_files = []
        for i in range(self.frame_count):
            frame_file = f"temp_frame_{i:06d}.png"
            if os.path.exists(frame_file):
                frame_files.append(frame_file)
        
        if not frame_files:
            print("❌ No frames captured")
            return
        
        # Create video using imageio
        output_path = f"{self.output_dir}/{self.filename}.mp4"
        
        with imageio.get_writer(output_path, fps=self.fps, codec='libx264') as writer:
            for frame_file in frame_files:
                try:
                    image = imageio.imread(frame_file)
                    writer.append_data(image)
                    # Clean up temporary file
                    os.remove(frame_file)
                except Exception as e:
                    print(f"Error processing frame {frame_file}: {e}")
        
        print(f"🎥 Created video with {len(frame_files)} frames")

class ScreenRecorder:
    """Alternative screen recording approach using OpenCV"""
    
    def __init__(self, filename="bucket_elevator_recording", fps=20, duration=30):
        self.filename = filename
        self.fps = fps
        self.duration = duration
        self.recording = False
        self.writer = None
        
        # Create output directory
        self.output_dir = "simulation_videos"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def start_recording(self, screen_region=None):
        """Start screen recording
        screen_region: (x, y, width, height) tuple for specific region
        """
        try:
            import pyautogui
            import cv2
            
            self.recording = True
            
            # Get screen dimensions
            if screen_region:
                self.region = screen_region
            else:
                screen_size = pyautogui.size()
                # Default to center region where VPython window usually appears
                self.region = (
                    screen_size.width // 4,
                    screen_size.height // 4,
                    screen_size.width // 2,
                    screen_size.height // 2
                )
            
            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            output_path = f"{self.output_dir}/{self.filename}.mp4"
            self.writer = cv2.VideoWriter(
                output_path, 
                fourcc, 
                self.fps, 
                (self.region[2], self.region[3])
            )
            
            print(f"🎬 Started screen recording: {output_path}")
            print(f"📹 Region: {self.region}")
            
            # Start recording in separate thread
            self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
            self.recording_thread.start()
            
        except ImportError:
            print("❌ Screen recording requires: pip install pyautogui opencv-python")
        except Exception as e:
            print(f"❌ Screen recording error: {e}")
    
    def _record_loop(self):
        """Main recording loop"""
        import pyautogui
        import cv2
        import numpy as np
        
        start_time = time.time()
        
        while self.recording and (time.time() - start_time) < self.duration:
            try:
                # Capture screen region
                screenshot = pyautogui.screenshot(region=self.region)
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Write frame
                self.writer.write(frame)
                
                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                print(f"Recording frame error: {e}")
                break
        
        self.stop_recording()
    
    def stop_recording(self):
        """Stop screen recording"""
        if self.recording:
            self.recording = False
            if self.writer:
                self.writer.release()
            print("✅ Screen recording completed")
    
    def record_vpython_window(self, duration=30):
        """Record VPython window specifically"""
        print("🎯 Looking for VPython window...")
        print("📝 Make sure the VPython simulation window is visible")
        print(f"⏱️ Recording will start in 3 seconds for {duration} seconds")
        
        time.sleep(3)  # Give user time to position window
        self.start_recording()
        
        # Keep recording for specified duration
        time.sleep(duration)
        self.stop_recording()
class SensorSystem:
    """Simulates various sensors for the bucket elevator"""
    
    def __init__(self):
        self.sensors = {
            'speed_rpm': {'value': 0, 'unit': 'rpm', 'min': 0, 'max': 100, 'alarm_threshold': 90},
            'load_kg': {'value': 0, 'unit': 'kg', 'min': 0, 'max': 1000, 'alarm_threshold': 900},
            'temperature_c': {'value': 25, 'unit': '°C', 'min': 20, 'max': 80, 'alarm_threshold': 70},
            'vibration_ms2': {'value': 0, 'unit': 'm/s²', 'min': 0, 'max': 20, 'alarm_threshold': 15},
            'current_a': {'value': 0, 'unit': 'A', 'min': 0, 'max': 50, 'alarm_threshold': 45}
        }
        self.history = {sensor: [] for sensor in self.sensors.keys()}
        self.alarms = []
        
    def update_sensors(self, belt_speed, material_count, operating_time):
        """Update sensor values based on elevator state"""
        # Speed sensor (convert m/s to rpm based on pulley diameter)
        pulley_circumference = 2 * math.pi * 0.6  # 0.6m radius
        self.sensors['speed_rpm']['value'] = (belt_speed / pulley_circumference) * 60
        
        # Load sensor (based on material in buckets)
        base_load = 100  # Base weight of elevator
        material_load = material_count * 2  # 2kg per material unit
        self.sensors['load_kg']['value'] = base_load + material_load + random.uniform(-10, 10)
        
        # Temperature sensor (increases with operation time and load)
        ambient_temp = 25
        load_factor = (self.sensors['load_kg']['value'] / 1000) * 20
        time_factor = min(operating_time / 3600, 1) * 15  # Max 15°C increase per hour
        self.sensors['temperature_c']['value'] = ambient_temp + load_factor + time_factor + random.uniform(-2, 2)
        
        # Vibration sensor (increases with speed and wear)
        speed_vibration = (self.sensors['speed_rpm']['value'] / 100) * 8
        wear_vibration = min(operating_time / 7200, 1) * 5  # Wear factor
        self.sensors['vibration_ms2']['value'] = speed_vibration + wear_vibration + random.uniform(-1, 1)
        
        # Current sensor (based on load and temperature)
        base_current = 5
        load_current = (self.sensors['load_kg']['value'] / 1000) * 25
        temp_current = max(0, (self.sensors['temperature_c']['value'] - 40) * 0.5)
        self.sensors['current_a']['value'] = base_current + load_current + temp_current + random.uniform(-2, 2)
        
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
        
        # Temperature impact
        temp_ratio = sensor_system.sensors['temperature_c']['value'] / 70
        if temp_ratio > 0.8:
            degradation_factors += (temp_ratio - 0.8) * 10
            
        # Vibration impact
        vib_ratio = sensor_system.sensors['vibration_ms2']['value'] / 15
        if vib_ratio > 0.7:
            degradation_factors += (vib_ratio - 0.7) * 15
            
        # Current impact (indicates motor strain)
        curr_ratio = sensor_system.sensors['current_a']['value'] / 45
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
            self.maintenance_recommendations.append("⚠️ URGENT: Replace worn components")
        if self.maintenance_score < 50:
            self.maintenance_recommendations.append("🔴 CRITICAL: Shutdown required for major maintenance")

class ControlSystem:
    """Automated control system for material handling"""
    
    def __init__(self):
        self.auto_mode = True
        self.target_speed = 2.0  # m/s
        self.speed_adjustment = 0
        self.emergency_stop = False
        
    def update_control(self, sensor_system):
        """Update control parameters based on sensor feedback"""
        if not self.auto_mode or self.emergency_stop:
            return
        
        # Speed control based on load
        load_ratio = sensor_system.sensors['load_kg']['value'] / 800
        if load_ratio > 0.9:
            self.speed_adjustment = -0.5  # Reduce speed for high load
        elif load_ratio < 0.3:
            self.speed_adjustment = 0.3   # Increase speed for low load
        else:
            self.speed_adjustment = 0     # Normal speed
            
        # Emergency conditions
        if (sensor_system.sensors['temperature_c']['value'] > 75 or
            sensor_system.sensors['vibration_ms2']['value'] > 18 or
            sensor_system.sensors['current_a']['value'] > 48):
            self.emergency_stop = True
            print("🛑 EMERGENCY STOP ACTIVATED - Critical sensor values detected!")

class SmartBucketElevator:
    def __init__(self):
        # Create the scene with enhanced UI
        self.scene = vp.canvas(title='Smart Bucket Elevator - IoT Monitoring System',
                              width=1400, height=900,
                              center=vp.vector(5, 10, 0),
                              background=vp.color.white)
        
        # Initialize recording system
        self.video_recorder = VideoRecorder(self.scene, "smart_bucket_elevator_demo", fps=30, duration=60)
        self.screen_recorder = ScreenRecorder("smart_bucket_elevator_screen", fps=20, duration=30)
        
        # Initialize systems
        connector = create_connector()
        self.sensor_system = EnhancedSensorSystem(machine_id=1, php_connector=connector)
        self.predictive_maintenance = PredictiveMaintenance()
        self.control_system = ControlSystem()
        
        # Add recording controls
        self.setup_recording_controls()
        
        # Elevator parameters
        self.elevator_height = 20
        self.elevator_width = 2
        self.bucket_count = 20
        self.base_belt_speed = 2.0  # m/s
        self.current_belt_speed = self.base_belt_speed
        self.bucket_spacing = 1.2
        
        # Operational data
        self.material_particles = []
        self.buckets = []
        self.bucket_positions = []
        self.operating_time = 0
        
        # Create physical components
        self.create_structure()
        self.create_belt_system()
        self.create_buckets()
        self.create_material_flow()
        self.create_hmi_displays()
        
        # Animation parameters
        self.time = 0
        self.dt = 0.02
        
        # Start systems
        self.start_monitoring()
        self.setup_recording_ui()
        self.animate()
    
    def create_structure(self):
        """Create the main structural components with sensors"""
        # Base foundation
        base = vp.box(pos=vp.vector(5, 0, 0), 
                     size=vp.vector(8, 0.5, 3),
                     color=vp.color.gray(0.3))
        
        # Main support columns
        left_column = vp.box(pos=vp.vector(2, self.elevator_height/2, 0),
                            size=vp.vector(0.3, self.elevator_height, 0.3),
                            color=vp.color.gray(0.4))
        
        right_column = vp.box(pos=vp.vector(8, self.elevator_height/2, 0),
                             size=vp.vector(0.3, self.elevator_height, 0.3),
                             color=vp.color.gray(0.4))
        
        # Cross bracing
        for i in range(5):
            height = i * (self.elevator_height / 5) + 2
            brace1 = vp.cylinder(pos=vp.vector(2, height, 0),
                               axis=vp.vector(6, 2, 0),
                               radius=0.05,
                               color=vp.color.gray(0.5))
            brace2 = vp.cylinder(pos=vp.vector(8, height, 0),
                               axis=vp.vector(-6, 2, 0),
                               radius=0.05,
                               color=vp.color.gray(0.5))
        
        # Drive housing with motor
        self.drive_housing = vp.box(pos=vp.vector(5, self.elevator_height + 1, 0),
                                   size=vp.vector(3, 2, 2),
                                   color=vp.color.blue)
        
        motor = vp.cylinder(pos=vp.vector(6.5, self.elevator_height + 1, 0),
                           axis=vp.vector(1.5, 0, 0),
                           radius=0.4,
                           color=vp.color.red)
        
        # Pulleys
        self.top_pulley = vp.cylinder(pos=vp.vector(8, self.elevator_height, 0),
                                     axis=vp.vector(0, 0, 0.8),
                                     radius=0.6,
                                     color=vp.color.gray(0.2))
        
        self.bottom_pulley = vp.cylinder(pos=vp.vector(2, 2, 0),
                                        axis=vp.vector(0, 0, 0.8),
                                        radius=0.6,
                                        color=vp.color.gray(0.2))
        
        # Sensor installations (visual indicators)
        self.create_sensor_indicators()
        
        # Feed hopper and discharge chute
        self.create_hopper()
        self.create_discharge_chute()
        
        # Boot section
        boot = vp.box(pos=vp.vector(2, 1.5, 0),
                     size=vp.vector(2, 3, 2),
                     color=vp.color.yellow)
    
    def create_sensor_indicators(self):
        """Create visual indicators for sensors"""
        # Speed sensor (on top pulley)
        self.speed_sensor = vp.box(pos=vp.vector(8.5, self.elevator_height + 0.5, 0),
                                  size=vp.vector(0.3, 0.3, 0.3),
                                  color=vp.color.green)
        
        # Temperature sensor (on motor)
        self.temp_sensor = vp.sphere(pos=vp.vector(6.5, self.elevator_height + 1.5, 0),
                                    radius=0.1,
                                    color=vp.color.red)
        
        # Vibration sensor (on structure)
        self.vibration_sensor = vp.box(pos=vp.vector(2.5, self.elevator_height/2, 0),
                                      size=vp.vector(0.2, 0.2, 0.2),
                                      color=vp.color.orange)
        
        # Current sensor (electrical panel)
        electrical_panel = vp.box(pos=vp.vector(9, 3, 0),
                                 size=vp.vector(0.8, 1.5, 0.2),
                                 color=vp.color.gray(0.8))
        self.current_sensor = vp.cylinder(pos=vp.vector(9, 3.5, 0.2),
                                         axis=vp.vector(0, 0, 0.3),
                                         radius=0.1,
                                         color=vp.color.blue)
        
        # Load sensor (on base)
        self.load_sensor = vp.box(pos=vp.vector(5, 0.3, 0),
                                 size=vp.vector(0.4, 0.1, 0.4),
                                 color=vp.color.purple)
    
    def create_hopper(self):
        """Create feed hopper"""
        hopper_top = vp.box(pos=vp.vector(1, 6, 0),
                           size=vp.vector(2.5, 0.2, 2.5),
                           color=vp.color.orange)
        
        for i in range(4):
            angle = i * math.pi / 2
            x_offset = 1.2 * math.cos(angle)
            z_offset = 1.2 * math.sin(angle)
            
            side = vp.box(pos=vp.vector(1 + x_offset, 4.5, z_offset),
                         size=vp.vector(0.1, 3, 2.5),
                         color=vp.color.orange)
            side.rotate(angle=angle, axis=vp.vector(0, 1, 0))
        
        outlet = vp.box(pos=vp.vector(1.5, 3, 0),
                       size=vp.vector(0.8, 0.5, 0.8),
                       color=vp.color.orange)
    
    def create_discharge_chute(self):
        """Create discharge chute"""
        chute = vp.box(pos=vp.vector(8.5, self.elevator_height - 1, 0),
                      size=vp.vector(2, 1, 1.5),
                      color=vp.color.green)
        
        spout = vp.cylinder(pos=vp.vector(9.5, self.elevator_height - 1.5, 0),
                           axis=vp.vector(1, -0.5, 0),
                           radius=0.3,
                           color=vp.color.green)
    
    def create_belt_system(self):
        """Create belt system"""
        self.belt_segments = []
        
        # Right side belt (going up)
        for i in range(100):
            height = 2 + (i/100) * (self.elevator_height - 2)
            segment = vp.cylinder(pos=vp.vector(8, height, 0),
                                axis=vp.vector(0, (self.elevator_height - 2)/100, 0),
                                radius=0.05,
                                color=vp.color.black)
            self.belt_segments.append(segment)
        
        # Left side belt (going down)
        for i in range(100):
            height = self.elevator_height - (i/100) * (self.elevator_height - 2)
            segment = vp.cylinder(pos=vp.vector(2, height, 0),
                                axis=vp.vector(0, -(self.elevator_height - 2)/100, 0),
                                radius=0.05,
                                color=vp.color.black)
            self.belt_segments.append(segment)
    
    def create_buckets(self):
        """Create elevator buckets"""
        self.buckets = []
        self.bucket_positions = []
        
        for i in range(self.bucket_count):
            progress = i / self.bucket_count
            pos = self.get_belt_position(progress)
            
            bucket = vp.compound([
                vp.box(pos=vp.vector(0, 0, -0.15), 
                      size=vp.vector(0.8, 0.6, 0.05),
                      color=vp.color.gray(0.7)),
                vp.box(pos=vp.vector(0, -0.25, 0), 
                      size=vp.vector(0.8, 0.1, 0.3),
                      color=vp.color.gray(0.7)),
                vp.box(pos=vp.vector(-0.35, -0.1, 0), 
                      size=vp.vector(0.1, 0.4, 0.3),
                      color=vp.color.gray(0.7)),
                vp.box(pos=vp.vector(0.35, -0.1, 0), 
                      size=vp.vector(0.1, 0.4, 0.3),
                      color=vp.color.gray(0.7))
            ])
            
            bucket.pos = pos
            self.buckets.append(bucket)
            self.bucket_positions.append(progress)
    
    def get_belt_position(self, progress):
        """Calculate position along belt path"""
        progress = progress % 1.0
        
        if progress < 0.25:  # Bottom horizontal
            t = progress * 4
            x = 2 + t * 6
            y = 2
        elif progress < 0.5:  # Right vertical (up)
            t = (progress - 0.25) * 4
            x = 8
            y = 2 + t * (self.elevator_height - 2)
        elif progress < 0.75:  # Top horizontal
            t = (progress - 0.5) * 4
            x = 8 - t * 6
            y = self.elevator_height
        else:  # Left vertical (down)
            t = (progress - 0.75) * 4
            x = 2
            y = self.elevator_height - t * (self.elevator_height - 2)
        
        return vp.vector(x, y, 0)
    
    def create_material_flow(self):
        """Create material particles"""
        self.material_particles = []
        
        for i in range(30):
            particle = vp.sphere(pos=vp.vector(1 + random.uniform(-0.5, 0.5),
                                             4 + random.uniform(-1, 1),
                                             random.uniform(-0.3, 0.3)),
                               radius=0.05,
                               color=vp.color.yellow)
            particle.velocity = vp.vector(0, 0, 0)
            self.material_particles.append(particle)
    
    def create_hmi_displays(self):
        """Create HMI display panels"""
        # Main control panel
        panel = vp.box(pos=vp.vector(-2, 8, 0),
                      size=vp.vector(0.1, 6, 4),
                      color=vp.color.black)
        
        # Status indicators
        self.status_indicators = {}
        colors = [vp.color.green, vp.color.yellow, vp.color.red, vp.color.blue, vp.color.purple]
        sensor_names = ['Speed', 'Load', 'Temp', 'Vibration', 'Current']
        
        for i, (name, color) in enumerate(zip(sensor_names, colors)):
            indicator = vp.cylinder(pos=vp.vector(-2.1, 10 - i * 1.2, 1.5),
                                   axis=vp.vector(0, 0, 0.2),
                                   radius=0.2,
                                   color=color)
            self.status_indicators[name.lower()] = indicator
    
    def setup_recording_ui(self):
        """Setup recording user interface"""
        print("\n🎬 VIDEO RECORDING OPTIONS:")
        print("="*50)
        print("1. VPython Native Recording (Recommended)")
        print("   - Records directly from VPython canvas")
        print("   - Best quality, synchronized with simulation")
        print("   - Usage: Press 'R' to start/stop recording")
        
        print("\n2. Screen Recording")
        print("   - Records screen region containing VPython window")
        print("   - Works with any application")
        print("   - Usage: Press 'S' to start screen recording")
        
        print("\n3. Manual Screenshot Capture")
        print("   - Saves individual frames as PNG images")
        print("   - Usage: Press 'C' to capture current frame")
        
        print("\n🎮 RECORDING CONTROLS:")
        print("  R - Start/Stop VPython recording")
        print("  S - Start screen recording (30 seconds)")
        print("  C - Capture screenshot")
        print("  V - Export current view as image")
        print("="*50)
        
        # Bind keyboard events
        self.scene.bind('keydown', self.handle_keyboard_input)
    
    def setup_recording_controls(self):
        """Initialize recording control variables"""
        self.recording_active = False
        self.screenshot_counter = 0
        
        # Create recording indicator
        self.recording_indicator = vp.sphere(pos=vp.vector(-3, 15, 0),
                                           radius=0.3,
                                           color=vp.color.red,
                                           visible=False)
        
        # Add recording status text
        self.recording_text = vp.text(text="REC", pos=vp.vector(-3, 14, 0),
                                    color=vp.color.red, height=0.5,
                                    visible=False)
    
    def handle_keyboard_input(self, event):
        """Handle keyboard input for recording controls"""
        key = event.key.lower()
        
        if key == 'r':
            self.toggle_vpython_recording()
        elif key == 's':
            self.start_screen_recording()
        elif key == 'c':
            self.capture_screenshot()
        elif key == 'v':
            self.export_current_view()
    
    def toggle_vpython_recording(self):
        """Toggle VPython native recording"""
        if not self.recording_active:
            self.video_recorder.start_recording()
            self.recording_active = True
            self.recording_indicator.visible = True
            self.recording_text.visible = True
            print("🔴 VPython recording STARTED")
        else:
            self.video_recorder.stop_recording()
            self.recording_active = False
            self.recording_indicator.visible = False
            self.recording_text.visible = False
            print("⏹️ VPython recording STOPPED")
    
    def start_screen_recording(self):
        """Start screen recording"""
        if not hasattr(self, '_screen_recording_active'):
            self._screen_recording_active = False
        
        if not self._screen_recording_active:
            self._screen_recording_active = True
            print("🎥 Starting screen recording...")
            
            # Start screen recording in separate thread
            def record_screen():
                self.screen_recorder.record_vpython_window(duration=30)
                self._screen_recording_active = False
            
            threading.Thread(target=record_screen, daemon=True).start()
        else:
            print("⚠️ Screen recording already in progress")
    
    def capture_screenshot(self):
        """Capture single screenshot"""
        try:
            filename = f"screenshot_{self.screenshot_counter:04d}"
            self.scene.capture(filename)
            self.screenshot_counter += 1
            print(f"📸 Screenshot saved: {filename}.png")
        except Exception as e:
            print(f"❌ Screenshot error: {e}")
    
    def export_current_view(self):
        """Export current view as high-quality image"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bucket_elevator_view_{timestamp}"
            self.scene.capture(filename)
            print(f"🖼️ View exported: {filename}.png")
        except Exception as e:
            print(f"❌ Export error: {e}")
    
    def update_hmi_displays(self):
        """Update HMI display based on sensor values"""
        # Update indicator brightness based on sensor values
        for sensor_name, sensor_data in self.sensor_system.sensors.items():
            display_name = sensor_name.split('_')[0]  # Get first part of sensor name
            if display_name in self.status_indicators:
                # Calculate intensity based on sensor value relative to max
                intensity = min(1.0, sensor_data['value'] / (sensor_data['max'] * 0.8))
                # Update indicator color intensity
                base_color = self.status_indicators[display_name].color
                self.status_indicators[display_name].emissive = True
    
    def start_monitoring(self):
        """Start the monitoring system in a separate thread"""
        def monitoring_loop():
            while True:
                # Update sensors
                material_count = len([p for p in self.material_particles if p.pos.y > 1])
                self.sensor_system.update_sensors(self.current_belt_speed, material_count, self.operating_time)
                
                # Run predictive maintenance analysis
                self.predictive_maintenance.analyze_trends(self.sensor_system)
                
                # Update control system
                self.control_system.update_control(self.sensor_system)
                
                # Print status every 5 seconds
                if int(self.operating_time) % 5 == 0 and self.operating_time > 0:
                    self.print_status()
                
                time.sleep(1)  # Update every second
        
        monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitoring_thread.start()
    
    def print_status(self):
        """Print current system status"""
        print("\n" + "="*80)
        print(f"📊 BUCKET ELEVATOR STATUS - Runtime: {self.operating_time:.0f}s")
        print("="*80)
        
        # Sensor readings
        print("🔍 SENSOR READINGS:")
        for sensor_name, sensor_data in self.sensor_system.sensors.items():
            status = "🔴" if sensor_data['value'] > sensor_data['alarm_threshold'] else "🟢"
            print(f"  {status} {sensor_name.replace('_', ' ').title()}: {sensor_data['value']:.2f} {sensor_data['unit']}")
        
        # Control system status
        print(f"\n🎛️ CONTROL SYSTEM:")
        print(f"  Auto Mode: {'ON' if self.control_system.auto_mode else 'OFF'}")
        print(f"  Current Speed: {self.current_belt_speed:.2f} m/s")
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
        for particle in self.material_particles:
            if particle.pos.y > 0.5:
                particle.velocity.y -= 9.8 * self.dt
                particle.pos += particle.velocity * self.dt
                
                # Check bucket interaction
                for bucket in self.buckets:
                    if (abs(particle.pos.x - bucket.pos.x) < 0.4 and
                        abs(particle.pos.y - bucket.pos.y) < 0.3 and
                        abs(particle.pos.z - bucket.pos.z) < 0.2):
                        particle.pos = bucket.pos + vp.vector(0, -0.2, 0)
                        particle.velocity = vp.vector(0, 0, 0)
                        break
        
        # Add new particles
        if random.random() < 0.15 and not self.control_system.emergency_stop:
            new_particle = vp.sphere(pos=vp.vector(1.5, 3.5, random.uniform(-0.2, 0.2)),
                                   radius=0.05,
                                   color=vp.color.yellow)
            new_particle.velocity = vp.vector(0, -1, 0)
            self.material_particles.append(new_particle)
    
    def animate(self):
        """Main animation loop"""
        print("🚀 Smart Bucket Elevator System Started!")
        print("📡 IoT sensors active - monitoring in real-time")
        print("🤖 Predictive maintenance system online")
        print("⚡ Automatic control system engaged")
        
        while True:
            vp.rate(50)  # 50 fps
            
            if not self.control_system.emergency_stop:
                self.time += self.dt
                self.operating_time += self.dt
                
                # Update belt speed based on control system
                target_speed = self.base_belt_speed + self.control_system.speed_adjustment
                self.current_belt_speed = target_speed
                
                # Rotate pulleys
                rotation_speed = self.current_belt_speed * self.dt / 0.6
                self.top_pulley.rotate(angle=rotation_speed, axis=vp.vector(0, 0, 1))
                self.bottom_pulley.rotate(angle=rotation_speed, axis=vp.vector(0, 0, 1))
                
                # Update bucket positions
                for i, bucket in enumerate(self.buckets):
                    self.bucket_positions[i] += self.current_belt_speed * self.dt / (4 * (self.elevator_height + 6))
                    bucket.pos = self.get_belt_position(self.bucket_positions[i])
                    bucket.up = vp.vector(0, 1, 0)
                
                # Update material flow
                self.update_material_flow()
                
                # Update HMI
                self.update_hmi_displays()
                
                # Capture frame for video recording if active
                if self.recording_active:
                    self.video_recorder.capture_frame()
            
            # Clean up fallen particles
            self.material_particles = [p for p in self.material_particles if p.pos.y > -5]

# Create and run the smart elevator system
if __name__ == "__main__":
    print("🏭 Starting Smart Bucket Elevator with IoT Monitoring...")
    print("📋 Features:")
    print("  ✓ Real-time sensor monitoring (Speed, Load, Temperature, Vibration, Current)")
    print("  ✓ Predictive maintenance analysis")
    print("  ✓ Automatic control system")
    print("  ✓ Alarm management")
    print("  ✓ Equipment health tracking")
    print("\n🔧 Dependencies required:")
    print("  pip install vpython numpy")
    print("\nClose the VPython window to exit.")
    
    try:
        elevator = SmartBucketElevator()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have the required dependencies installed.")
        print("Run: pip install vpython numpy")