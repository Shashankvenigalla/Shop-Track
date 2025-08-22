#!/usr/bin/env python3
"""
ShopTrack Startup Script
Launches all components of the ShopTrack application.
"""
import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import settings

class ShopTrackLauncher:
    """Launcher for ShopTrack application components."""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_api_server(self):
        """Start the FastAPI server."""
        print("🚀 Starting ShopTrack API Server...")
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload" if settings.debug else "--workers", "4"
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.processes.append(("API Server", process))
        print("✅ API Server started on http://localhost:8000")
        
    def start_dashboard(self):
        """Start the Dash dashboard."""
        print("📊 Starting ShopTrack Dashboard...")
        cmd = [
            sys.executable, "app/dashboard/main.py"
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.processes.append(("Dashboard", process))
        print("✅ Dashboard started on http://localhost:8050")
        
    def start_celery_worker(self):
        """Start Celery worker for background tasks."""
        print("🔧 Starting Celery Worker...")
        cmd = [
            sys.executable, "-m", "celery",
            "-A", "app.worker.celery",
            "worker",
            "--loglevel=info",
            "--concurrency=4"
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.processes.append(("Celery Worker", process))
        print("✅ Celery Worker started")
        
    def start_celery_beat(self):
        """Start Celery beat for scheduled tasks."""
        print("⏰ Starting Celery Beat...")
        cmd = [
            sys.executable, "-m", "celery",
            "-A", "app.worker.celery",
            "beat",
            "--loglevel=info"
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.processes.append(("Celery Beat", process))
        print("✅ Celery Beat started")
        
    def check_dependencies(self):
        """Check if required dependencies are available."""
        print("🔍 Checking dependencies...")
        
        # Check if .env file exists
        if not os.path.exists(".env"):
            print("⚠️  .env file not found. Please copy env.example to .env and configure it.")
            return False
            
        # Check if models directory exists
        models_dir = Path("models")
        if not models_dir.exists():
            models_dir.mkdir(exist_ok=True)
            print("📁 Created models directory")
            
        return True
        
    def monitor_processes(self):
        """Monitor running processes and restart if needed."""
        while self.running:
            for name, process in self.processes:
                if process.poll() is not None:
                    print(f"❌ {name} stopped unexpectedly")
                    if self.running:
                        print(f"🔄 Restarting {name}...")
                        # Restart logic could be added here
            time.sleep(5)
            
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n🛑 Shutting down ShopTrack...")
        self.running = False
        self.shutdown()
        
    def shutdown(self):
        """Shutdown all processes."""
        print("🔄 Stopping all processes...")
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"⚠️  {name} force killed")
            except Exception as e:
                print(f"❌ Error stopping {name}: {e}")
                
    def run(self):
        """Run the ShopTrack application."""
        print("🎯 ShopTrack - Real-Time Inventory & Checkout Prediction")
        print("=" * 60)
        
        # Check dependencies
        if not self.check_dependencies():
            print("❌ Dependency check failed. Please fix the issues above.")
            return
            
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Start all components
            self.start_api_server()
            time.sleep(2)
            
            self.start_dashboard()
            time.sleep(2)
            
            self.start_celery_worker()
            time.sleep(2)
            
            self.start_celery_beat()
            time.sleep(2)
            
            print("\n🎉 ShopTrack is now running!")
            print("📱 API Documentation: http://localhost:8000/docs")
            print("📊 Dashboard: http://localhost:8050")
            print("🔍 Health Check: http://localhost:8000/health")
            print("\nPress Ctrl+C to stop all services")
            
            # Start monitoring thread
            monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
            monitor_thread.start()
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal")
        except Exception as e:
            print(f"❌ Error starting ShopTrack: {e}")
        finally:
            self.shutdown()
            print("👋 ShopTrack stopped")


if __name__ == "__main__":
    launcher = ShopTrackLauncher()
    launcher.run() 