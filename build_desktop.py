#!/usr/bin/env python3
"""
Desktop Build Script for Miner Detector
=====================================

This script automates the building of a desktop executable for the Miner Detector application.
It handles dependency installation, environment setup, and PyInstaller packaging.

Author: Desktop Build Assistant
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

class DesktopBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.venv_dir = self.project_root / "venv_desktop"
        
    def log(self, message):
        """Log messages with timestamp"""
        print(f"[BUILD] {message}")
        
    def run_command(self, command, check=True):
        """Run shell command with error handling"""
        self.log(f"Running: {command}")
        try:
            result = subprocess.run(command, shell=True, check=check, 
                                 capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            raise
            
    def setup_virtual_environment(self):
        """Create and setup virtual environment"""
        self.log("Setting up virtual environment...")
        
        if self.venv_dir.exists():
            self.log("Removing existing virtual environment...")
            shutil.rmtree(self.venv_dir)
            
        # Create virtual environment
        self.run_command(f"{sys.executable} -m venv {self.venv_dir}")
        
        # Determine activation script based on OS
        if platform.system() == "Windows":
            activate_script = self.venv_dir / "Scripts" / "activate.bat"
            pip_path = self.venv_dir / "Scripts" / "pip.exe"
        else:
            activate_script = self.venv_dir / "bin" / "activate"
            pip_path = self.venv_dir / "bin" / "pip"
            
        return str(pip_path)
        
    def install_dependencies(self, pip_path):
        """Install required dependencies"""
        self.log("Installing dependencies...")
        
        # Upgrade pip first
        self.run_command(f"{pip_path} install --upgrade pip")
        
        # Install desktop requirements
        requirements_file = self.project_root / "desktop_requirements.txt"
        if requirements_file.exists():
            self.run_command(f"{pip_path} install -r {requirements_file}")
        else:
            self.log("desktop_requirements.txt not found, using requirements.txt")
            self.run_command(f"{pip_path} install -r requirements.txt")
            self.run_command(f"{pip_path} install PyInstaller auto-py-to-exe")
            
    def clean_previous_builds(self):
        """Clean previous build artifacts"""
        self.log("Cleaning previous builds...")
        
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            
    def fix_spec_file(self):
        """Fix the spec file for current environment"""
        spec_file = self.project_root / "miner_detector_desktop.spec"
        
        if spec_file.exists():
            # Read and fix the spec file
            with open(spec_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Replace workspace path with current directory
            content = content.replace('/workspace', str(self.project_root))
            
            # Add import os if not present
            if 'import os' not in content:
                content = 'import os\n' + content
                
            with open(spec_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
    def build_executable(self, pip_path):
        """Build the executable using PyInstaller"""
        self.log("Building executable...")
        
        # Get PyInstaller path
        if platform.system() == "Windows":
            pyinstaller_path = self.venv_dir / "Scripts" / "pyinstaller.exe"
        else:
            pyinstaller_path = self.venv_dir / "bin" / "pyinstaller"
            
        # Fix spec file first
        self.fix_spec_file()
        
        # Build using spec file if it exists
        spec_file = self.project_root / "miner_detector_desktop.spec"
        if spec_file.exists():
            self.run_command(f"{pyinstaller_path} {spec_file}")
        else:
            # Fallback to direct command
            self.log("Spec file not found, using direct PyInstaller command...")
            gui_file = self.project_root / "miner_detector_gui.py"
            cmd = (f"{pyinstaller_path} --onefile --windowed "
                  f"--name=MinerDetector "
                  f"--add-data=\"*.ttf;.\" "
                  f"--add-data=\"*.html;.\" "
                  f"--hidden-import=PyQt5.QtCore "
                  f"--hidden-import=PyQt5.QtWidgets "
                  f"--hidden-import=sklearn.ensemble "
                  f"{gui_file}")
            self.run_command(cmd)
            
    def create_installer_script(self):
        """Create an installer script"""
        installer_script = self.project_root / "install_desktop.sh"
        
        installer_content = f"""#!/bin/bash
# Miner Detector Desktop Installer
# Generated automatically

INSTALL_DIR="$HOME/MinerDetector"
EXECUTABLE_NAME="MinerDetector"

echo "Installing Miner Detector Desktop Application..."

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Copy executable
if [ -f "dist/$EXECUTABLE_NAME" ]; then
    cp "dist/$EXECUTABLE_NAME" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/$EXECUTABLE_NAME"
    echo "Executable copied to $INSTALL_DIR"
else
    echo "Error: Executable not found in dist/ directory"
    exit 1
fi

# Copy fonts and other assets
cp *.ttf "$INSTALL_DIR/" 2>/dev/null || true
cp *.html "$INSTALL_DIR/" 2>/dev/null || true

# Create desktop shortcut
DESKTOP_FILE="$HOME/Desktop/MinerDetector.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Miner Detector
Comment=Advanced Miner Detection System
Exec=$INSTALL_DIR/$EXECUTABLE_NAME
Icon=$INSTALL_DIR/icon.png
Terminal=false
StartupWMClass=MinerDetector
Categories=Utility;Security;
EOF

chmod +x "$DESKTOP_FILE"

echo "Installation completed!"
echo "You can run the application from: $INSTALL_DIR/$EXECUTABLE_NAME"
echo "Or use the desktop shortcut: Miner Detector"
"""

        with open(installer_script, 'w') as f:
            f.write(installer_content)
            
        # Make installer executable
        os.chmod(installer_script, 0o755)
        self.log(f"Created installer script: {installer_script}")
        
    def create_windows_installer(self):
        """Create Windows batch installer"""
        installer_script = self.project_root / "install_desktop.bat"
        
        installer_content = f"""@echo off
REM Miner Detector Desktop Installer for Windows
REM Generated automatically

set INSTALL_DIR=%USERPROFILE%\\MinerDetector
set EXECUTABLE_NAME=MinerDetector.exe

echo Installing Miner Detector Desktop Application...

REM Create installation directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy executable
if exist "dist\\%EXECUTABLE_NAME%" (
    copy "dist\\%EXECUTABLE_NAME%" "%INSTALL_DIR%\\"
    echo Executable copied to %INSTALL_DIR%
) else (
    echo Error: Executable not found in dist\\ directory
    pause
    exit /b 1
)

REM Copy fonts and other assets
copy *.ttf "%INSTALL_DIR%\\" >nul 2>&1
copy *.html "%INSTALL_DIR%\\" >nul 2>&1

REM Create desktop shortcut
set DESKTOP_SHORTCUT=%USERPROFILE%\\Desktop\\MinerDetector.lnk
powershell "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP_SHORTCUT%'); $s.TargetPath = '%INSTALL_DIR%\\%EXECUTABLE_NAME%'; $s.Save()"

echo Installation completed!
echo You can run the application from: %INSTALL_DIR%\\%EXECUTABLE_NAME%
echo Or use the desktop shortcut: Miner Detector
pause
"""

        with open(installer_script, 'w') as f:
            f.write(installer_content)
            
        self.log(f"Created Windows installer script: {installer_script}")
        
    def build(self):
        """Main build process"""
        self.log("Starting desktop build process...")
        
        try:
            # Setup environment
            pip_path = self.setup_virtual_environment()
            
            # Install dependencies
            self.install_dependencies(pip_path)
            
            # Clean previous builds
            self.clean_previous_builds()
            
            # Build executable
            self.build_executable(pip_path)
            
            # Create installer scripts
            self.create_installer_script()
            if platform.system() == "Windows":
                self.create_windows_installer()
                
            self.log("Build completed successfully!")
            self.log(f"Executable location: {self.dist_dir}")
            
            # List built files
            if self.dist_dir.exists():
                self.log("Built files:")
                for file in self.dist_dir.iterdir():
                    self.log(f"  - {file.name}")
                    
        except Exception as e:
            self.log(f"Build failed: {e}")
            sys.exit(1)

def main():
    """Main entry point"""
    builder = DesktopBuilder()
    builder.build()

if __name__ == "__main__":
    main()