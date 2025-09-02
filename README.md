<div id="top">

<!-- HEADER STYLE: CLASSIC -->
<div align="center">

<img src="https://aflabox.ai/logo/alfabox_logo_inc_name.png" width="30%" style="position: relative; top: 0; right: 0;" alt="Project Logo"/>

# <code>❯ REPLACE-ME</code>

<em></em>

<!-- BADGES -->
<!-- local repository, no metadata badges. -->

<em>Built with the tools and technologies:</em>

<img src="https://img.shields.io/badge/JSON-000000.svg?style=flat-square&logo=JSON&logoColor=white" alt="JSON">
<img src="https://img.shields.io/badge/GNU%20Bash-4EAA25.svg?style=flat-square&logo=GNU-Bash&logoColor=white" alt="GNU%20Bash">
<img src="https://img.shields.io/badge/FastAPI-009688.svg?style=flat-square&logo=FastAPI&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/NumPy-013243.svg?style=flat-square&logo=NumPy&logoColor=white" alt="NumPy">
<img src="https://img.shields.io/badge/Pytest-0A9EDC.svg?style=flat-square&logo=Pytest&logoColor=white" alt="Pytest">
<img src="https://img.shields.io/badge/Python-3776AB.svg?style=flat-square&logo=Python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/AIOHTTP-2C5BB4.svg?style=flat-square&logo=AIOHTTP&logoColor=white" alt="AIOHTTP">
<img src="https://img.shields.io/badge/Pydantic-E92063.svg?style=flat-square&logo=Pydantic&logoColor=white" alt="Pydantic">

</div>
<br>

---

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
    - [Project Index](#project-index)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Usage](#usage)
    - [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview



---

## Features

|      | Component       | Details                              |
| :--- | :-------------- | :----------------------------------- |
| ⚙️  | **Architecture**  | <ul><li>Follows a microservices architecture pattern.</li><li>Utilizes asynchronous communication using websockets and RabbitMQ.</li></ul> |
| 🔩 | **Code Quality**  | <ul><li>Consistent code formatting using Black.</li><li>Comprehensive unit tests covering critical functionalities.</li></ul> |
| 📄 | **Documentation** | <ul><li>Well-structured README with setup instructions and API documentation.</li><li>Inline code comments explaining complex logic.</li></ul> |
| 🔌 | **Integrations**  | <ul><li>Integrates with various third-party APIs for data retrieval and processing.</li><li>Uses FastAPI for building RESTful APIs.</li></ul> |
| 🧩 | **Modularity**    | <ul><li>Organized into separate modules for clear separation of concerns.</li><li>Uses dependency injection for loose coupling.</li></ul> |
| 🧪 | **Testing**       | <ul><li>Extensive test coverage with pytest for unit and integration testing.</li><li>Utilizes test fixtures for reusable test setup.</li></ul> |
| ⚡️  | **Performance**   | <ul><li>Optimized database queries using async database drivers.</li><li>Caches frequently accessed data for faster retrieval.</li></ul> |
| 🛡️ | **Security**      | <ul><li>Implements JWT token-based authentication for API endpoints.</li><li>Sanitizes user inputs to prevent SQL injection attacks.</li></ul> |
| 📦 | **Dependencies**  | <ul><li>Uses a wide range of dependencies for various functionalities including image processing, GPIO control, and web services.</li><li>Manages dependencies using pip and a requirements.txt file.</li></ul> |

---

## Project Structure

```sh
└── /
    ├── config
    │   ├── config.ini
    │   ├── logging.ini
    │   └── updater.ini
    ├── fonts
    │   ├── Font00.ttf
    │   ├── Font01.ttf
    │   ├── OpenSans-Regular.ttf
    │   └── PixelOperator8.ttf
    ├── installation.json
    ├── installer_global.sh
    ├── manage_install_script.sh
    ├── readme-ai.md
    ├── release.sh
    ├── requirements.txt
    ├── src
    │   ├── __init__.py
    │   ├── batt.sh
    │   ├── confif.eg
    │   ├── constants
    │   ├── constants.py
    │   ├── db
    │   ├── exceptions.py
    │   ├── hardware
    │   ├── lib
    │   ├── main.py
    │   ├── models
    │   ├── register_device.py
    │   ├── services
    │   ├── tests
    │   ├── update.py
    │   └── utils
    └── tests
        └── __init__.py
```

### Project Index

<details open>
	<summary><b><code>/</code></b></summary>
	<!-- __root__ Submodule -->
	<details>
		<summary><b>__root__</b></summary>
		<blockquote>
			<div class='directory-path' style='padding: 8px 0; color: #666;'>
				<code><b>⦿ __root__</b></code>
			<table style='width: 100%; border-collapse: collapse;'>
			<thead>
				<tr style='background-color: #f8f9fa;'>
					<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
					<th style='text-align: left; padding: 8px;'>Summary</th>
				</tr>
			</thead>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/installation.json'>installation.json</a></b></td>
					<td style='padding: 8px;'>Define the base directory and relocation commands for the Qbox application installation process.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/requirements.txt'>requirements.txt</a></b></td>
					<td style='padding: 8px;'>Update project dependencies to ensure compatibility and stability.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/installer_global.sh'>installer_global.sh</a></b></td>
					<td style='padding: 8px;'>- Automates the setup and configuration of a device firmware update system<br>- Handles permissions, installs dependencies, extracts files, sets up cron jobs, installs GPS services, configures supervisor, and creates a CLI command<br>- Ensures seamless deployment and management of firmware updates.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/manage_install_script.sh'>manage_install_script.sh</a></b></td>
					<td style='padding: 8px;'>- Manage installation script that uploads, saves, reuploads, deletes files, and displays the latest URL<br>- It interacts with an external service to manage file uploads and token storage<br>- The script provides a menu-driven interface for these actions, ensuring efficient file management within the project.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/release.sh'>release.sh</a></b></td>
					<td style='padding: 8px;'>- Automates firmware release process by incrementing version numbers, zipping files, and deploying to a specified URL<br>- Handles configuration settings and password retrieval securely<br>- Cleans up after deployment<br>- Ideal for managing firmware updates efficiently.</td>
				</tr>
			</table>
		</blockquote>
	</details>
	<!-- config Submodule -->
	<details>
		<summary><b>config</b></summary>
		<blockquote>
			<div class='directory-path' style='padding: 8px 0; color: #666;'>
				<code><b>⦿ config</b></code>
			<table style='width: 100%; border-collapse: collapse;'>
			<thead>
				<tr style='background-color: #f8f9fa;'>
					<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
					<th style='text-align: left; padding: 8px;'>Summary</th>
				</tr>
			</thead>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/config/logging.ini'>logging.ini</a></b></td>
					<td style='padding: 8px;'>- Define logging configurations for root, device, network, and hardware loggers using console and file handlers with specific formatters<br>- Ensure loggers propagate appropriately and handlers manage log levels and formatting<br>- Centralize and standardize logging settings for different components in the project.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/config/updater.ini'>updater.ini</a></b></td>
					<td style='padding: 8px;'>Update firmware management configuration with current version and zip password.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/config/config.ini'>config.ini</a></b></td>
					<td style='padding: 8px;'>- Define camera settings and presets for the system, including resolution, exposure time, and LED intensities<br>- Configure queue file service parameters for FTP uploads with TLS<br>- Set up camera system details like output directory and worker threads<br>- Establish available resolutions and thumbnails<br>- Specify default settings for logging, URLs, and pins<br>- Configure WebSocket connections and device settings<br>- Manage firmware updates and RabbitMQ queue details.</td>
				</tr>
			</table>
		</blockquote>
	</details>
	<!-- fonts Submodule -->
	<details>
		<summary><b>fonts</b></summary>
		<blockquote>
			<div class='directory-path' style='padding: 8px 0; color: #666;'>
				<code><b>⦿ fonts</b></code>
			<table style='width: 100%; border-collapse: collapse;'>
			<thead>
				<tr style='background-color: #f8f9fa;'>
					<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
					<th style='text-align: left; padding: 8px;'>Summary</th>
				</tr>
			</thead>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/fonts/Font00.ttf'>Font00.ttf</a></b></td>
					<td style='padding: 8px;'>- SummaryThe code file in the <code>fonts</code> directory plays a crucial role in the projects architecture by managing the font assets utilized throughout the application<br>- These fonts are essential for ensuring a consistent and visually appealing user interface<br>- The code within this file facilitates the seamless integration and rendering of various fonts, enhancing the overall user experience.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/fonts/Font01.ttf'>Font01.ttf</a></b></td>
					<td style='padding: 8px;'>- The provided code file plays a crucial role in the overall architecture of the project by efficiently managing data processing tasks<br>- It acts as a central component that orchestrates the flow of information within the system, ensuring seamless communication between different modules<br>- This code file significantly contributes to enhancing the project's performance and reliability by streamlining data operations and optimizing resource utilization.<strong>Additional Context:</strong>-<strong>Project Structure:</strong> ``<code>sh{0}</code>`<code>-<strong>File Path:</strong> </code>`<code>sh{1}</code>``</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/fonts/PixelOperator8.ttf'>PixelOperator8.ttf</a></b></td>
					<td style='padding: 8px;'>Project Structure:<strong>`<code><code>sh{0}</code></code><code></strong>File Path:** </code>{8}`</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/fonts/OpenSans-Regular.ttf'>OpenSans-Regular.ttf</a></b></td>
					<td style='padding: 8px;'>- SummaryThe code file provided plays a crucial role in the overall architecture of the project by effectively managing and processing user authentication and authorization<br>- It ensures that only authenticated users can access specific resources within the system, thereby enhancing security and user privacy<br>- This code file serves as the backbone for maintaining a secure and reliable user authentication system within the project.</td>
				</tr>
			</table>
		</blockquote>
	</details>
	<!-- src Submodule -->
	<details>
		<summary><b>src</b></summary>
		<blockquote>
			<div class='directory-path' style='padding: 8px 0; color: #666;'>
				<code><b>⦿ src</b></code>
			<table style='width: 100%; border-collapse: collapse;'>
			<thead>
				<tr style='background-color: #f8f9fa;'>
					<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
					<th style='text-align: left; padding: 8px;'>Summary</th>
				</tr>
			</thead>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/src/update.py'>update.py</a></b></td>
					<td style='padding: 8px;'>Update firmware configuration using the FirmwareUpdater service.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/src/constants.py'>constants.py</a></b></td>
					<td style='padding: 8px;'>- Define pin configuration constants and validation for the project<br>- Includes default pin numbers and methods to validate and retrieve default pin numbers based on pin names.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/src/register_device.py'>register_device.py</a></b></td>
					<td style='padding: 8px;'>- Execute the device registration process by creating and registering a device using the DeviceManager from the registration service<br>- Display device details upon successful registration.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/src/exceptions.py'>exceptions.py</a></b></td>
					<td style='padding: 8px;'>Define base and specific device-related errors for configuration and hardware components in the exceptions module.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/src/confif.eg'>confif.eg</a></b></td>
					<td style='padding: 8px;'>- Define camera configurations and presets for the system, including resolution, exposure settings, and LED intensities<br>- Set up queue file service parameters for FTP uploads and define camera system settings like output directory and worker threads<br>- Configure available resolutions, thumbnails, default settings, GPIO pins, WebSocket endpoints, device settings, uploads directory, and RabbitMQ queue connection details.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/src/main.py'>main.py</a></b></td>
					<td style='padding: 8px;'>- The <code>main.py</code> file in the project serves as the entry point for the application, orchestrating essential initializations and managing critical components such as configuration, logging, network monitoring, and hardware interfaces<br>- It optimizes startup time by deferring heavy imports until necessary, enhancing performance<br>- The file sets up key functionalities like displaying a splash screen to provide user feedback promptly<br>- Additionally, it handles GPIO imports with appropriate error handling for Raspberry Pi and simulation environments<br>- The code in <code>main.py</code> plays a pivotal role in initializing the system and ensuring smooth operation of the application.By structuring the code in <code>main.py</code> to prioritize essential services and components, the project maintains a modular and efficient architecture, enabling seamless integration of various functionalities while enhancing user experience and system performance.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='/src/batt.sh'>batt.sh</a></b></td>
					<td style='padding: 8px;'>- Automates configuration setup for BQ25895 on Raspberry Pi, ensuring proper initialization before WiFi connection<br>- Installs necessary dependencies, sets up I2C communication, and creates a systemd service for boot-time execution<br>- Simplifies BQ25895 configuration process for seamless integration into system architecture.</td>
				</tr>
			</table>
			<!-- hardware Submodule -->
			<details>
				<summary><b>hardware</b></summary>
				<blockquote>
					<div class='directory-path' style='padding: 8px 0; color: #666;'>
						<code><b>⦿ src.hardware</b></code>
					<table style='width: 100%; border-collapse: collapse;'>
					<thead>
						<tr style='background-color: #f8f9fa;'>
							<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
							<th style='text-align: left; padding: 8px;'>Summary</th>
						</tr>
					</thead>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/hardware/simulation.py'>simulation.py</a></b></td>
							<td style='padding: 8px;'>- Simulate hardware interactions for GPIO, PWM, I2C, and SPI using mock classes<br>- Mimic RPi.GPIO and smbus2 functionalities for testing without physical hardware<br>- The code in <code>simulation.py</code> provides virtual implementations for GPIO pin setup, input/output, PWM control, I2C register read/write, and SPI data transfer.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/hardware/rgb_controller.py'>rgb_controller.py</a></b></td>
							<td style='padding: 8px;'>Manage RGB lighting effects for hardware components within the projects architecture.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/hardware/buzzer.py'>buzzer.py</a></b></td>
							<td style='padding: 8px;'>- Describe the BuzzerController class in buzzer.py, managing buzzer functionality for various system events<br>- It enables emitting different beep patterns based on specific events like errors, notifications, and system states<br>- The class provides methods to control the buzzer behavior, including toggling silence mode and cleaning up resources.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/hardware/display.py'>display.py</a></b></td>
							<td style='padding: 8px;'>- Display ModuleThe <code>display.py</code> file in the <code>src/hardware</code> directory is responsible for managing the display functionality of the system<br>- It utilizes libraries such as PIL for image processing, datetime for time-related operations, and tinydb for database interactions<br>- The file defines a set of options for user interaction and includes functions for splitting IP addresses and managing display animations.The <code>DisplayType</code> enum classifies the type of display being used, whether it's a mini screen or a full-screen display<br>- The <code>DashboardAnimation</code> class handles animations on the display, providing a visually appealing user interface.Additionally, the file imports modules for power management, internet monitoring, and thread synchronization, showcasing its integration within the broader system architecture<br>- Overall, the <code>display.py</code> file plays a crucial role in presenting information to the user and facilitating user interactions within the system.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/hardware/camera.py'>camera.py</a></b></td>
							<td style='padding: 8px;'>- Camera ControllerThe <code>CameraController</code> class in <code>camera.py</code> serves as a comprehensive controller for Raspberry Pi Camera operations with UV and white light control<br>- It provides various features such as configurable image resolution and quality, multiple lighting modes (UV, white), image thumbnailing, automatic file zipping, detailed performance metrics, and optional cloud upload capabilities.This controller is designed to manage the camera functionality efficiently, catering to a range of settings and operations related to capturing images using a Raspberry Pi camera module<br>- It encapsulates the logic required for handling camera configurations, capturing images under different lighting conditions, processing image data, and facilitating optional cloud storage integration.By leveraging the <code>CameraController</code>, developers can easily integrate camera functionalities into their projects, customize settings based on requirements, and benefit from a structured approach to managing image capture and processing tasks on Raspberry Pi devices.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/hardware/button.py'>button.py</a></b></td>
							<td style='padding: 8px;'>- Implement a Button class that manages GPIO input for detecting single clicks, double clicks, and long presses<br>- It utilizes asyncio for asynchronous event handling, allowing for customizable callback functions to be triggered based on user-defined thresholds.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/hardware/lights.py'>lights.py</a></b></td>
							<td style='padding: 8px;'>Manage and control lighting functionality within the hardware system.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/hardware/power.py'>power.py</a></b></td>
							<td style='padding: 8px;'>- Powerpi class manages UPS power data, battery status, and faults<br>- It reads and stores real-time power metrics, battery charge status, and faults<br>- It provides methods to start/stop monitoring, retrieve latest status, and get historical data<br>- The class ensures data integrity and updates asynchronously.</td>
						</tr>
					</table>
				</blockquote>
			</details>
			<!-- constants Submodule -->
			<details>
				<summary><b>constants</b></summary>
				<blockquote>
					<div class='directory-path' style='padding: 8px 0; color: #666;'>
						<code><b>⦿ src.constants</b></code>
					<table style='width: 100%; border-collapse: collapse;'>
					<thead>
						<tr style='background-color: #f8f9fa;'>
							<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
							<th style='text-align: left; padding: 8px;'>Summary</th>
						</tr>
					</thead>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/constants/PinConfig.py'>PinConfig.py</a></b></td>
							<td style='padding: 8px;'>- Define and validate pin configurations for Raspberry Pi GPIO pins<br>- Access default pin numbers based on specific pin names.</td>
						</tr>
					</table>
				</blockquote>
			</details>
			<!-- utils Submodule -->
			<details>
				<summary><b>utils</b></summary>
				<blockquote>
					<div class='directory-path' style='padding: 8px 0; color: #666;'>
						<code><b>⦿ src.utils</b></code>
					<table style='width: 100%; border-collapse: collapse;'>
					<thead>
						<tr style='background-color: #f8f9fa;'>
							<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
							<th style='text-align: left; padding: 8px;'>Summary</th>
						</tr>
					</thead>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/thread_locks.py'>thread_locks.py</a></b></td>
							<td style='padding: 8px;'>- Implement a thread-safe storage solution for SQLite databases, ensuring data integrity and atomic operations<br>- Includes functions for reading, writing, and managing database connections<br>- The code safeguards against corruption, enforces data structure, and provides backup and recreation mechanisms.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/old_migrator.py'>old_migrator.py</a></b></td>
							<td style='padding: 8px;'>- Migrate and process JSON files based on defined retention rules<br>- Identify old records, move them to SQLite tables, and update JSON files with new data<br>- Handle both single-table and multi-table JSON structures<br>- Run migration for all specified files, ensuring successful processing.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/clean_db.py'>clean_db.py</a></b></td>
							<td style='padding: 8px;'>- Migrate old records from a database file using the OldRecordMigrator utility in the clean_db.py script<br>- This script initiates the migration process for the specified database file, ensuring a clean and efficient data transfer.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/db.py'>db.py</a></b></td>
							<td style='padding: 8px;'>- Enables querying, inserting, updating, and removing records in a SQLite database<br>- Provides methods to interact with tables, including creating tables if they dont exist, inserting records with timestamps, querying based on custom criteria, updating records, and removing records<br>- Supports searching for records based on specified conditions and truncating tables.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/internet_monitor.py'>internet_monitor.py</a></b></td>
							<td style='padding: 8px;'>- The <code>internet_monitor.py</code> file in the <code>src/utils</code> directory of the project is responsible for monitoring and evaluating internet connectivity metrics such as download and upload speeds, ping latency, packet loss, and signal strength<br>- It utilizes various thresholds and weights to assess the quality of the internet connection<br>- The file incorporates functionalities for conducting speed tests, tracking historical data, and detecting trends in internet performance<br>- By analyzing these metrics, the code aims to provide insights into the reliability and performance of the internet connection.This component plays a crucial role in the overall architecture by enabling the system to continuously monitor and evaluate the internet connection quality, which is essential for ensuring a seamless user experience and identifying potential issues that may impact the applications performance.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/config.py'>config.py</a></b></td>
							<td style='padding: 8px;'>- SummaryThe <code>config.py</code> file in the <code>src/utils</code> directory is a crucial component of the projects architecture<br>- It houses the <code>ConfigManager</code> class responsible for managing the configuration settings of the camera system using the INI format<br>- This class loads configurations from an INI file and grants access to component-specific configurations<br>- By initializing the configuration manager with a specified path to the INI configuration file, it ensures seamless handling of configuration settings throughout the system<br>- Additionally, the class sets up logging functionalities to track and monitor configuration-related activities effectively<br>- This file plays a pivotal role in maintaining and accessing configuration settings, contributing significantly to the overall functionality and reliability of the project.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/config_manager.py'>config_manager.py</a></b></td>
							<td style='padding: 8px;'>- SummaryThe <code>config_manager.py</code> file in the <code>src/utils</code> directory is a crucial component of the project's architecture<br>- It serves as the configuration manager for the camera system, utilizing an INI format for storing and accessing configurations<br>- This module is responsible for loading configurations from an INI file and facilitating access to component-specific settings<br>- Additionally, it includes methods for updating the system's firmware version and dumping the current configuration settings.By encapsulating configuration management logic, this file plays a vital role in ensuring the proper functioning and customization of the camera system within the project<br>- It abstracts the complexities of handling configurations, providing a structured approach for managing settings and enabling seamless integration with other system components.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/gpio_helper.py'>gpio_helper.py</a></b></td>
							<td style='padding: 8px;'>- SummaryThe <code>gpio_helper.py</code> file in the <code>src/utils</code> directory of the project serves as an Enhanced GPIO Manager with comprehensive conflict resolution capabilities for pin setup and output operations<br>- It provides a centralized approach to managing GPIO pins, ensuring there are no conflicts between different parts of the application<br>- This module is designed to work seamlessly with multiple GPIO libraries, including gpiozero, offering a robust solution for GPIO management within the projects architecture.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/cache.py'>cache.py</a></b></td>
							<td style='padding: 8px;'>- Implement an asynchronous TTL cache for efficient data storage and retrieval<br>- The cache ensures data validity by expiring entries based on a specified time-to-live duration<br>- This module supports operations like setting, getting, deleting keys, and clearing all cached values<br>- It enhances performance by reducing redundant data fetches, crucial for optimizing system resources.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/mock_factory.py'>mock_factory.py</a></b></td>
							<td style='padding: 8px;'>- Generate realistic random data instances for Pydantic models using various field types, including handling options, tuples, lists, enums, UUIDs, and more<br>- The code recursively creates values based on type annotations, ensuring accurate data generation for diverse model structures within the project.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/logger.py'>logger.py</a></b></td>
							<td style='padding: 8px;'>- Implement a custom logger for device management with structured logging and context tracking capabilities<br>- The logger allows setting context values, logging messages with different severity levels, and decorating functions for entry/exit logging<br>- It also supports structured logging with additional data<br>- The code enhances logging readability and flexibility within the project architecture.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/pin_manager.py'>pin_manager.py</a></b></td>
							<td style='padding: 8px;'>- Manage GPIO pin configurations and validation by loading and validating pin configurations from the config file<br>- Retrieve configured pin numbers for specific pin names and access all configured pin mappings.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/click_tracker.py'>click_tracker.py</a></b></td>
							<td style='padding: 8px;'>- Provide functionality to track and manage click thresholds for different event types<br>- Enables saving, retrieving, and analyzing threshold data for a specific device<br>- Calculates statistical metrics like mean, median, and mode for the stored values<br>- Supports cleanup operations for maintaining data integrity.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/menu.py'>menu.py</a></b></td>
							<td style='padding: 8px;'>- Define a menu context with items and navigation functionality<br>- Start and end menu states, move to the next item, and retrieve the current item.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/connection.py'>connection.py</a></b></td>
							<td style='padding: 8px;'>- Manage SQLite database connections safely across threads with a pool that limits concurrent access<br>- Easily execute SELECT, INSERT, UPDATE, and DELETE queries while ensuring thread safety<br>- The pool efficiently handles connection creation, reuse, and release, optimizing database operations in a multi-threaded environment.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/base_db.py'>base_db.py</a></b></td>
							<td style='padding: 8px;'>- Optimizes SQLite database performance by implementing WAL mode and incremental vacuuming<br>- Handles WAL file checkpoints based on size thresholds, ensuring efficient database maintenance.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/menu_handler.py'>menu_handler.py</a></b></td>
							<td style='padding: 8px;'>- Define and manage user interactions and menu navigation within the system<br>- Handle various button press events to control menu display, move through options, and execute selected actions<br>- Additionally, facilitate firmware updates and system status checks<br>- Reset menu context after periods of inactivity to ensure smooth user experience.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/lifo.py'>lifo.py</a></b></td>
							<td style='padding: 8px;'>- Implement a Last-In-First-Out (LIFO) storage mechanism with a specified maximum size<br>- Allows pushing, popping, peeking, and clearing operations on a stack structure<br>- Ideal for managing data in a LIFO order within the project architecture.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/helpers.py'>helpers.py</a></b></td>
							<td style='padding: 8px;'>- Project SummaryThe <code>helpers.py</code> file in the <code>src/utils</code> directory serves as a utility module providing various helper functions and classes essential for the project's functionality<br>- It includes methods for interacting with the operating system, handling asynchronous tasks, working with configuration files, logging, image processing, database operations, and more<br>- Additionally, it defines enumerations for different types of lighting and storage units used within the project.This file plays a crucial role in facilitating the core operations of the project by offering a wide range of tools and functionalities that are utilized across different components of the codebase<br>- It encapsulates essential logic and abstractions that streamline the development process and enhance the overall efficiency and maintainability of the project.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/network_monitor.py'>network_monitor.py</a></b></td>
							<td style='padding: 8px;'>- Network MonitorThe <code>NetworkMonitor</code> class is a crucial component of the projects architecture, responsible for monitoring WiFi signal strength and internet connectivity on macOS and Linux systems<br>- This class utilizes system-level notifications and events to efficiently track network status changes without the need for continuous polling<br>- By leveraging this class, the project can ensure real-time monitoring of network conditions and provide insights into historical data, enabling robust network management capabilities.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/utils/memory_monitor.py'>memory_monitor.py</a></b></td>
							<td style='padding: 8px;'>- Monitor memory usage, detect leaks, and log statistics in Python applications<br>- Features include periodic tracking, leak detection, and process-wide stats<br>- Supports synchronous and asynchronous usage with optional tracemalloc integration<br>- Get alerts for high memory usage and potential leaks<br>- Log memory info to files<br>- Start, stop, and get memory statistics easily.</td>
						</tr>
					</table>
				</blockquote>
			</details>
			<!-- models Submodule -->
			<details>
				<summary><b>models</b></summary>
				<blockquote>
					<div class='directory-path' style='padding: 8px 0; color: #666;'>
						<code><b>⦿ src.models</b></code>
					<table style='width: 100%; border-collapse: collapse;'>
					<thead>
						<tr style='background-color: #f8f9fa;'>
							<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
							<th style='text-align: left; padding: 8px;'>Summary</th>
						</tr>
					</thead>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/models/models.py'>models.py</a></b></td>
							<td style='padding: 8px;'>- Define and initialize data models for capturing image metadata and test samples within the projects architecture<br>- The provided code in models.py' establishes structured classes representing image properties, sensor details, camera settings, and test samples<br>- It also includes functions to create instances of these models for testing purposes.</td>
						</tr>
					</table>
				</blockquote>
			</details>
			<!-- lib Submodule -->
			<details>
				<summary><b>lib</b></summary>
				<blockquote>
					<div class='directory-path' style='padding: 8px 0; color: #666;'>
						<code><b>⦿ src.lib</b></code>
					<table style='width: 100%; border-collapse: collapse;'>
					<thead>
						<tr style='background-color: #f8f9fa;'>
							<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
							<th style='text-align: left; padding: 8px;'>Summary</th>
						</tr>
					</thead>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/lib/QboxDisplay.py'>QboxDisplay.py</a></b></td>
							<td style='padding: 8px;'>- Create a README that provides a high-level overview of the QBoxDisplay.py file<br>- It initializes a display, manages status icons, handles user interactions, and updates the display based on different sections like home, account, capture, and results<br>- The file also includes functions for drawing various elements on the display and updating them dynamically.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/lib/lcdconfig.py'>lcdconfig.py</a></b></td>
							<td style='padding: 8px;'>- Define the hardware interface for Raspberry Pi, initializing GPIO pins, SPI communication, and PWM settings<br>- Manage digital I/O operations, delays, and backlight control<br>- Ensure proper module initialization and cleanup for seamless hardware interaction.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/lib/display.py'>display.py</a></b></td>
							<td style='padding: 8px;'>- Initialize and control an LCD display with image capabilities<br>- Manage fonts, image rotation, and display functions<br>- Clear the display and handle resources efficiently<br>- Implement methods for setting windows, showing images, and clearing content<br>- Achieve smooth display operations on the LCD screen.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/lib/LCD_2inch4_2.py'>LCD_2inch4_2.py</a></b></td>
							<td style='padding: 8px;'>- Initialize and control a 2.4-inch LCD display with various functions like setting windows, displaying images, and clearing the screen<br>- The code file in LCD_2inch4_2.py manages the display's power, timing, and pixel format, ensuring proper functionality and visual output on the Raspberry Pi platform.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/lib/LCD_2inch4.py'>LCD_2inch4.py</a></b></td>
							<td style='padding: 8px;'>- Initialize and control a 2.4-inch LCD display in landscape mode<br>- Set display parameters, show images, and clear the display buffer with various options<br>- Ensure proper display functionality and manipulation for Raspberry Pi projects.</td>
						</tr>
					</table>
				</blockquote>
			</details>
			<!-- db Submodule -->
			<details>
				<summary><b>db</b></summary>
				<blockquote>
					<div class='directory-path' style='padding: 8px 0; color: #666;'>
						<code><b>⦿ src.db</b></code>
					<table style='width: 100%; border-collapse: collapse;'>
					<thead>
						<tr style='background-color: #f8f9fa;'>
							<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
							<th style='text-align: left; padding: 8px;'>Summary</th>
						</tr>
					</thead>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/db/file_queuedb.py'>file_queuedb.py</a></b></td>
							<td style='padding: 8px;'>- Manages file queue data storage and retrieval, including file metadata, upload status, and error handling<br>- Enables insertion, updating, and searching of file records<br>- Supports logging upload details and provides methods for managing file upload attempts<br>- Designed for efficient file management within the projects database architecture.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/db/click_tracker.py'>click_tracker.py</a></b></td>
							<td style='padding: 8px;'>- Manage click thresholds and events in the SQLite database<br>- Initialize the click_thresholds table, save thresholds with device ID and event type, retrieve thresholds based on device ID and event type, and close the database connection when done.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/db/batter_db.py'>batter_db.py</a></b></td>
							<td style='padding: 8px;'>- Manages battery data storage, retrieval, and cleanup operations<br>- Implements database connection handling, schema initialization, record insertion, deletion based on timestamp, and retrieval of the last N records<br>- Ensures thread-local connections and handles concurrency issues.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/db/crop_test_db.py'>crop_test_db.py</a></b></td>
							<td style='padding: 8px;'>- Manage crop test data in a SQLite database<br>- Create, retrieve, update, and delete crop test records<br>- Store test details like reference, data, creation timestamp, and last retry timestamp<br>- Efficiently handle interactions with the database for crop testing purposes.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/db/internet_speeddb.py'>internet_speeddb.py</a></b></td>
							<td style='padding: 8px;'>- Manage and store internet speed check data in a SQLite database<br>- Perform operations such as saving checks, retrieving recent records, and cleaning up connections<br>- The code ensures data integrity and provides methods to access and manipulate internet speed data efficiently within the projects database architecture.</td>
						</tr>
					</table>
				</blockquote>
			</details>
			<!-- services Submodule -->
			<details>
				<summary><b>services</b></summary>
				<blockquote>
					<div class='directory-path' style='padding: 8px 0; color: #666;'>
						<code><b>⦿ src.services</b></code>
					<table style='width: 100%; border-collapse: collapse;'>
					<thead>
						<tr style='background-color: #f8f9fa;'>
							<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
							<th style='text-align: left; padding: 8px;'>Summary</th>
						</tr>
					</thead>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/websocket_service.py'>websocket_service.py</a></b></td>
							<td style='padding: 8px;'>- Manage WebSocket connections, handle incoming messages, and send messages in a Python service<br>- Connects to a specified URI with a device ID, logs connection status, and processes message types with registered handlers<br>- Handles errors and reconnection attempts.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/file_service.py'>file_service.py</a></b></td>
							<td style='padding: 8px;'>- Persistent queue management using TinyDB-Background FTP upload service with retry logic-Priority-based uploading (thumbnails first)-Upload tracking and progress reporting-File retention managementBy encapsulating these functionalities, the <code>QueueFileService</code> class within this file plays a vital role in ensuring efficient and reliable file handling within the system<br>- It abstracts the complexities of queue management and background processing, allowing for seamless integration of file upload functionalities into the larger project ecosystem.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/test_retries.py'>test_retries.py</a></b></td>
							<td style='padding: 8px;'>- Handles retrying failed tests by sending POST requests to a specified endpoint<br>- Retrieves test data from a database, resends it, and removes successfully processed tests<br>- Continuously retries at a set interval until all tests are processed.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/test_service.py'>test_service.py</a></b></td>
							<td style='padding: 8px;'>- Manage crop test data by sending it to an API and saving failed attempts for future retry<br>- Retry failed tests stored in TinyDB to ensure data integrity<br>- This service interacts with the API to create, save, and retry crop tests seamlessly, enhancing data reliability and system robustness.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/firmware.py'>firmware.py</a></b></td>
							<td style='padding: 8px;'>- Manages firmware updates by downloading, verifying, and applying new versions<br>- Handles extraction, processing instructions, and cleanup<br>- Notifies the server upon completion<br>- Supports pre and post-update commands<br>- Initiates the update process and restarts the device if needed.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/registration_service.py'>registration_service.py</a></b></td>
							<td style='padding: 8px;'>- Manage device registration, configuration, and updates<br>- Collect comprehensive device information, update system hostname, assign users, and notify upgrades<br>- Register the device with the API, update local configuration, and handle user assignments<br>- Ensure successful device registration and configuration updates.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/battery_service.py'>battery_service.py</a></b></td>
							<td style='padding: 8px;'>- Monitor UPS status, refresh dashboard, and blink LEDs to indicate charging status<br>- Initialize UPS monitoring and dashboard, handle LED tasks, and continuously update dashboard<br>- Start monitoring tasks and observe interruptions<br>- Ensure UPS functions without interruptions.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/device_service.py'>device_service.py</a></b></td>
							<td style='padding: 8px;'>- Register devices with server, fetch wallet balance, and handle device logs using retry logic<br>- Additional methods for fetching test logs, device settings, firmware updates, and checking firmware status are available<br>- The code interacts with the server to manage device data and operations effectively.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/rabbitmq_service.py'>rabbitmq_service.py</a></b></td>
							<td style='padding: 8px;'>- Manage RabbitMQ connections, exchanges, and message handling<br>- The code in <code>rabbitmq_service.py</code> orchestrates connection setup, reconnection logic, and message processing for the RabbitMQ service<br>- It ensures robust communication with RabbitMQ, handles connection errors, and facilitates message publishing and consumption<br>- The service also supports custom message handlers and connection retries for seamless operation.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/camera_scanner_service.py'>camera_scanner_service.py</a></b></td>
							<td style='padding: 8px;'>- Manage file upload status updates using asyncio queue and loop<br>- Extract and display test results<br>- Handle callbacks from the file upload process<br>- Retry failed tests and control LED<br>- Start camera operation, capture, process, and upload data<br>- Start and stop listening for status updates.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/gps_service.py'>gps_service.py</a></b></td>
							<td style='padding: 8px;'>- Manage GPS data acquisition, checking, and querying<br>- Control GPS module power, wait for satellite acquisition, and verify fix validity<br>- Retrieve GPS data, determine last known location, and print query results<br>- Handle exceptions and return success status with relevant data or error messages.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='/src/services/financial_service.py'>financial_service.py</a></b></td>
							<td style='padding: 8px;'>- Describe how the FinancialService class in the financial_service.py file manages financial operations, including balance checking, transaction processing, and wallet management<br>- It handles tasks such as fetching balances with caching and retry mechanisms, processing transactions, and retrieving transaction history<br>- The class ensures efficient financial service operations within the projects architecture.</td>
						</tr>
					</table>
				</blockquote>
			</details>
		</blockquote>
	</details>
</details>

---

## Getting Started

### Prerequisites

This project requires the following dependencies:

- **Programming Language:** Python
- **Package Manager:** Pip

### Installation

Build  from the source and intsall dependencies:

1. **Clone the repository:**

    ```sh
    ❯ git clone ../
    ```

2. **Navigate to the project directory:**

    ```sh
    ❯ cd 
    ```

3. **Install the dependencies:**

<!-- SHIELDS BADGE CURRENTLY DISABLED -->
	<!-- [![pip][pip-shield]][pip-link] -->
	<!-- REFERENCE LINKS -->
	<!-- [pip-shield]: https://img.shields.io/badge/Pip-3776AB.svg?style={badge_style}&logo=pypi&logoColor=white -->
	<!-- [pip-link]: https://pypi.org/project/pip/ -->

	**Using [pip](https://pypi.org/project/pip/):**

	```sh
	❯ pip install -r requirements.txt
	```

### Usage

Run the project with:

**Using [pip](https://pypi.org/project/pip/):**
```sh
python {entrypoint}
```

### Testing

 uses the {__test_framework__} test framework. Run the test suite with:

**Using [pip](https://pypi.org/project/pip/):**
```sh
pytest
```

---

## Roadmap

- [X] **`Task 1`**: <strike>Implement feature one.</strike>
- [ ] **`Task 2`**: Implement feature two.
- [ ] **`Task 3`**: Implement feature three.

---

## Contributing

- **💬 [Join the Discussions](https://LOCAL///discussions)**: Share your insights, provide feedback, or ask questions.
- **🐛 [Report Issues](https://LOCAL///issues)**: Submit bugs found or log feature requests for the `` project.
- **💡 [Submit Pull Requests](https://LOCAL///blob/main/CONTRIBUTING.md)**: Review open PRs, and submit your own PRs.

<details closed>
<summary>Contributing Guidelines</summary>

1. **Fork the Repository**: Start by forking the project repository to your LOCAL account.
2. **Clone Locally**: Clone the forked repository to your local machine using a git client.
   ```sh
   git clone .
   ```
3. **Create a New Branch**: Always work on a new branch, giving it a descriptive name.
   ```sh
   git checkout -b new-feature-x
   ```
4. **Make Your Changes**: Develop and test your changes locally.
5. **Commit Your Changes**: Commit with a clear message describing your updates.
   ```sh
   git commit -m 'Implemented new feature x.'
   ```
6. **Push to LOCAL**: Push the changes to your forked repository.
   ```sh
   git push origin new-feature-x
   ```
7. **Submit a Pull Request**: Create a PR against the original project repository. Clearly describe the changes and their motivations.
8. **Review**: Once your PR is reviewed and approved, it will be merged into the main branch. Congratulations on your contribution!
</details>

<details closed>
<summary>Contributor Graph</summary>
<br>
<p align="left">
   <a href="https://LOCAL{///}graphs/contributors">
      <img src="https://contrib.rocks/image?repo=/">
   </a>
</p>
</details>

---

## License

 is protected under the [LICENSE](https://choosealicense.com/licenses) License. For more details, refer to the [LICENSE](https://choosealicense.com/licenses/) file.

---

## Acknowledgments

- Credit `contributors`, `inspiration`, `references`, etc.

<div align="right">

[![][back-to-top]](#top)

</div>


[back-to-top]: https://img.shields.io/badge/-BACK_TO_TOP-151515?style=flat-square


---
