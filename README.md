# Autonomous Guided Vehicle (AGV)
**PMDS x DevNut Autonomous Guided Vehicle Project**

## Table of Contents
- [TODOs](#todos)
- [Development Environment Setup](#development-environment-setup)
- [Webots Configuration](#webots-configuration)
- [Project Rules](#project-rules)
- [Docker Database Setup](#docker-database-setup)
- [Container Management](#container-management)

---

## TODOs
Please refer to [TODO.md](./TODO.md) for the active list of project tasks and milestones.

---

## Development Environment Setup

### Installing Dependencies

**Option A: Automatic Setup (Recommended)**  
Run the provided setup script. It will automatically create a virtual environment and install all necessary dependencies. At the end of the script, it will print the absolute path to your Python interpreter, which you'll need for Webots.
```bash
./setup.sh
```

**Option B: Manual Setup**  
If you prefer to set up the environment manually, follow these steps:
1. **Create the virtual environment:**
   ```bash
   python3.12 -m venv .venv
   ```
2. **Activate the virtual environment** *(You must do this every time you open a new terminal):*
   ```bash
   source .venv/bin/activate
   ```
3. **Install the requirements:**
   *(Note: `requirements.txt` was last updated on 04/15/2026. If you experience dependency issues, ensure you pull the latest version).*
   ```bash
   pip install -r requirements.txt
   ```

---

## Webots Configuration

To link your Python virtual environment with Webots:
1. **Get the Python Path:** Use the path printed by the `setup.sh` script. Alternatively, you can find the absolute path manually by navigating to `.venv/bin/python3.12` and copying it.
2. **Set the Path in Webots:** Open Webots and navigate to `Webots > Preferences > Python commands`. Paste the copied absolute path into the dedicated input box.

---

## Project Rules

> [!WARNING]
> **Never save the world directly from Webots** using `Cmd + Shift + S` or `Ctrl + Shift + S`. Doing so overwrites the `.wbt` file and strips all custom comments. If you accidentally save it, do not commit or push the resulting code to the repository!

---

## Docker Database Setup

This section outlines how to install Docker, start a MySQL container, and set up the database structure required to store the robotic simulator logs.

### Step 1: Install Docker Desktop
1. Download **Docker Desktop** for your operating system from the official site: [docker.com](https://www.docker.com/products/docker-desktop).
2. Follow the standard installation process for your OS.
3. Open Docker Desktop and **wait for the Docker Engine to fully start**.

### Step 2: Start the MySQL Container
Open your terminal and execute the following command to download and run the MySQL container in the background:

```bash
docker run --name agv-logger -e MYSQL_ROOT_PASSWORD=agv_pass -p 3306:3306 -d mysql:latest
```
- `--name agv-logger`: Assigns an easy-to-remember name to your container.
- `-e MYSQL_ROOT_PASSWORD=agv_pass`: Sets the MySQL root password to `agv_pass` (you can change this, but make sure to remember it!).
- `-d`: Runs the container in detached mode (background).
- `-p 3306:3306`: Maps the standard MySQL port to allow your Python script to communicate with the database.
- `mysql:latest`: Pulls the latest official MySQL image from Docker Hub.

### Step 3: Access the MySQL Console
To create the database, access the container's interactive terminal:

```bash
docker exec -it agv-logger mysql -u root -p
```
*When prompted for a password, type `agv_pass` and press Enter (the characters will be hidden as you type).*

### Step 4: Create the Database and Tables
Once inside the MySQL console (you will see the `mysql>` prompt), execute the following commands:

1. **Create and select the database:**
   ```sql
   CREATE DATABASE agv_data;
   USE agv_data;
   ```

2. **Initialize the log tables:**
   Open the `Database_Structure.sql` file in your editor and copy-paste the queries into the console. Ensure you execute each query separately rather than all at once.

If successful, you will see a `Query OK` message. You can exit the console by typing `EXIT;`.

> [!NOTE]
> - Ensure the `mysql-connector-python` package is installed in your Python environment.
> - Always check `Database_Structure.sql` when pulling new updates. If the database schema has changed, you must run the new queries to update your local database structure.

---

## Container Management

### 1. Exiting the MySQL Console
If you are inside the MySQL command line (`mysql>`), you must exit to return to your normal system terminal. Type:
```sql
exit;
```
*(You will see a "Bye" message).*

### 2. Stopping the Container
Even after exiting the MySQL console, the database container remains running in the background. To stop it and free up system resources, run:
```bash
docker stop agv-logger
```

### 3. Restarting the Container
When you are ready to resume your Webots simulation, **do not** use `docker run` again (this will throw an error since the container name already exists). Instead, simply start the existing container:
```bash
docker start agv-logger
```

Once started, if you need to manage the database manually, you can re-enter the console using `docker exec -it agv-logger mysql -u root -p`, enter the password, and select the database (`USE agv_data;`) before executing any queries.

---

## Real-Time Dashboard

We have a built-in Streamlit dashboard to monitor the AGV's telemetry, local planning grid, and AI camera feed in real-time.

**Starting the Dashboard:**
The dashboard is seamlessly integrated into the controller. **You do not need to start it manually.** When you run the Webots simulation, the `DefaultController` will automatically launch the Streamlit server in the background and open a new browser tab directed to `http://localhost:8501`.

**Stopping the Dashboard:**
Because it runs in the background, the dashboard will persist even if you stop the Webots simulation (allowing you to restart Webots without losing the dashboard window). 
If you want to completely terminate the running dashboard and free up its port, open your terminal and run:
```bash
pkill -f "streamlit run .*web-app/app.py"
```

For more details, see [docs/dashboard.md](docs/dashboard.md).
