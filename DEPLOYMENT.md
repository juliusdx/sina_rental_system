# Sinaland Rental System - Deployment Guide

This guide describes how to deploy the Sinaland Rental System to a new machine (e.g., an office server).

## Prerequisites

1.  **Python 3.10+**: Ensure Python is installed on the server.
    *   Download: [python.org](https://www.python.org/downloads/)
    *   **Important**: Check the box **"Add Python to PATH"** during installation.

2.  **Git** (Optional but recommended):
    *   Download: [git-scm.com](https://git-scm.com/downloads)

## Step 1: Transfer the Code

You can either clone from GitHub (recommended) or copy the files via USB/Network share.

### Option A: Using Git (Recommended)
Open Command Prompt (cmd) or PowerShell on the server and run:
```bash
cd C:\Path\To\Where\You\Want\The\App
git clone https://github.com/juliusdx/sina_rental_system.git
cd sina_rental_system
```

### Option B: Manual Copy
1.  Copy the entire `rental_system` folder from your current machine.
2.  Paste it onto the server (e.g., `C:\Sina\rental_system`).

## Step 2: Transfer Data (Important!)

If you want to keep your **existing data** (Tenants, Properties, Photos), you must manually copy these files from your old machine to the new server folder:

1.  **Database**: `rental.db` (Located in the root folder).
2.  **Uploads**: The `static/uploads` folder.
    *   Copy `static/uploads/properties` -> `NewServer/static/uploads/properties`
    *   Copy `static/uploads/tenants` -> `NewServer/static/uploads/tenants`

> **Note**: If you don't copy `rental.db`, the system will create a brand new, empty database.

## Step 3: Setup Environment

1.  Open PowerShell or Command Prompt inside the `rental_system` folder.
2.  Create a virtual environment (keeps dependencies isolated):
    ```bash
    python -m venv venv
    ```
3.  Activate the virtual environment:
    *   **Windows**: `.\venv\Scripts\activate`
    *   **Linux/Mac**: `source venv/bin/activate`
    *(You should see `(venv)` appear at the start of your command line)*

4.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    pip install waitress
    ```
    *(We install `waitress` as a production-ready server for Windows).*

## Step 4: Configure for Production

1.  Create a file named `.env` in the root folder (same place as `app.py`).
2.  Add a secure secret key:
    ```
    SECRET_KEY=PleaseChangeThisToARandomStringOfCharacters
    ```

## Step 5: Run the Server

### Option A: Testing (Dev Mode)
To check if it works:
```bash
python app.py
```
*   Open browser at `http://localhost:5000`.
*   Press `Ctrl+C` to stop.

### Option B: Production (Stable)
To run it effectively on a server so other computers can access it:

1.  Create a new file named `run_server.py`:
    ```python
    from waitress import serve
    from app import create_app

    app = create_app()

    print("Server running on http://0.0.0.0:8080")
    serve(app, host='0.0.0.0', port=8080)
    ```

2.  Run this script:
    ```bash
    python run_server.py
    ```

3.  **Accessing from other computers**:
    *   Find the server's IP address (Run `ipconfig` in cmd, look for IPv4 Address, e.g., `192.168.1.50`).
    *   On your colleague's PC, open Chrome and go to: `http://192.168.1.50:8080`.

## Step 6: Setup Auto-Updater (Optional)

To keep the server automatically updated with the latest code from GitHub every 5 minutes:

1.  Create a file named `auto_update.ps1` in the `rental_system` folder.
2.  Paste the following code into it:

```powershell
Write-Host "Starting Auto-Updater for Sinaland Rental System..."

while($true) {
    Write-Host "Checking for updates..." -NoNewline
    
    # Fetch latest data from GitHub
    git fetch origin
    
    # Check if local branch is behind remote
    $status = git status -uno
    
    if ($status -match "behind") {
        Write-Host " [UPDATES DETECTED]" -ForegroundColor Green
        Write-Host "Pulling latest changes..."
        git pull
        
        Write-Host "Restarting Server Process..." -ForegroundColor Yellow
        # Stop existing python process
        Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
        
        # Start new server process in background
        Start-Process -FilePath "python" -ArgumentList "run_server.py" -WindowStyle Hidden
        Write-Host "Server Restarted." -ForegroundColor Green
    } else {
        Write-Host " [UP TO DATE]" -ForegroundColor Gray
    }
    
    # Wait for 5 minutes (300 seconds)
    Start-Sleep -Seconds 300
}
```

3.  **To Run**:
    *   Open PowerShell as Administrator.
    *   Run: `Set-ExecutionPolicy RemoteSigned` (Allows scripts to run).
    *   Run: `.\auto_update.ps1`
    
    *This script will stay open, check for updates every 5 minutes, and automatically restart the server if new code is detected.*

## Step 7: How to Access the System

### 1. From Other Office Computers (Intranet)
*   **Address**: `http://<SERVER_IP>:8080`
    *   Example: `http://192.168.1.50:8080`
*   **Requirement**: They must be connected to the *same* network/Wi-Fi as the server.

### 2. From Mobile Devices
*   **Address**: Same as above (`http://192.168.1.50:8080`).
*   **Requirement**: The phone/tablet must be connected to the **Office Wi-Fi**. It will NOT work on 4G/5G data unless you have a VPN.

### 3. From Outside the Office (Internet)
By default, this system is **Local Only** for security. To access it from home:
*   **Option A (Recommended):** Set up a **VPN** to your office network. Once connected, access via the local IP.
*   **Option B (Advanced):** Configure **Port Forwarding** on your office router (Forward port 8080 to the Server IP).
    *   *Warning*: This exposes the system to the public internet. Ensure you have a strong `SECRET_KEY` and strong passwords.
*   **Option C (Cloud):** Host this on a cloud server (AWS, DigitalOcean, PythonAnywhere) instead of an office PC.

## Troubleshooting

*   **Firewall**: If other computers can't connect, ensure the server's Windows Firewall allows traffic on Port **8080**.
    *   Open "Windows Defender Firewall with Advanced Security".
    *   Inbound Rules -> New Rule -> Port -> TCP -> Specific Ports: `8080` -> Allow Connection -> Name: "Sina Rental System".
