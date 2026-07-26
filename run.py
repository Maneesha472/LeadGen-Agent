import sys
import os
import subprocess
import time
import webbrowser

BANNER = """
======================================================================
               V I L L O W   L E A D   G E N E R A T O R
               Execution Agent & Real-Time Dashboard
======================================================================
"""

REQUIRED_PACKAGES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "requests": "requests",
    "bs4": "beautifulsoup4"
}

def install_dependencies():
    print("Checking system dependencies...")
    missing_packages = []
    
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            missing_packages.append(pip_name)
            
    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_packages])
            print("Successfully installed dependencies.")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            print("Please run manually: pip install fastapi uvicorn sqlalchemy requests beautifulsoup4")
            sys.exit(1)
    else:
        print("All dependencies are satisfied.")

def main():
    print(BANNER)
    install_dependencies()
    
    # Import uvicorn after ensuring it is installed
    import uvicorn
    
    print("\nStarting FastAPI web server...")
    print("Access the dashboard at: http://localhost:8000")
    print("Press Ctrl+C in this terminal to shutdown.")
    
    # Launch browser in a separate thread/delay to let uvicorn bind
    def launch_browser():
        time.sleep(1.5)
        print("Opening web dashboard...")
        webbrowser.open("http://localhost:8000")
        
    import threading
    t = threading.Thread(target=launch_browser)
    t.daemon = True
    t.start()
    
    # Start server — reload=True is broken in Python 3.14+ due to a multiprocessing
    # event loop closure bug (RuntimeError: Cannot close a running event loop).
    # Use reload only on Python ≤ 3.12.
    use_reload = sys.version_info < (3, 13)
    try:
        uvicorn.run(
            "backend.app:app",
            host="127.0.0.1",
            port=8000,
            reload=use_reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nShutdown request received. Exiting Villow Lead Generator.")
    except Exception as e:
        print(f"\nServer failed to start: {e}")

if __name__ == "__main__":
    # Ensure current directory is on path to find backend packages
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    main()
