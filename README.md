# Weather App (Technical Assessment 1 & 2)

## Overview
This is a full-stack weather application built for Technical Assessments 1 and 2. It uses FastAPI (Python) for the backend, SQLAlchemy for the database, Jinja2 for templating, and a modern frontend with custom CSS and JavaScript.

## Features
- User registration and login (secure authentication)
- Weather lookup by city and optional date range
- 5-day forecast and current weather display
- Saved weather lookups for each user
- View full 5-day forecast or sunrise/sunset times for any saved entry
- Export all your weather data as JSON or CSV
- Responsive, modern UI
- Caching and timeouts for speed and reliability

## Setup & Running
1. **Clone the repository** and navigate to the project folder.
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up your environment variables:**
   - Create a `.env` file with your OpenWeatherMap API key and database URL, e.g.:
     ```
     OPENWEATHER_API_KEY=your_api_key_here
     DATABASE_URL=sqlite:///./weather.db
     SECRET_KEY=your_secret_key_here
     ```
5. **Run the app:**
   ```bash
   uvicorn app.main:app --reload
   ```
6. **Open your browser and go to:**
   - [http://localhost:8000/](http://localhost:8000/) (main app)
   - [http://localhost:8000/export](http://localhost:8000/export) (export data as JSON)
   - [http://localhost:8000/export?format=csv](http://localhost:8000/export?format=csv) (export data as CSV)

## How to View Exported Data
- **JSON:**
  - Log in to your account, then visit [http://localhost:8000/export](http://localhost:8000/export) in your browser. You'll see/download your weather data as JSON.
- **CSV:**
  - Log in, then visit [http://localhost:8000/export?format=csv](http://localhost:8000/export?format=csv) to download your data as a CSV file.

## What Was Done
- Built a full-stack weather app with user authentication, weather lookup, and persistent storage.
- Implemented date range filtering for forecasts, and always show the full 5-day forecast from the home screen.
- Added sunrise/sunset info, error handling, and caching for speed.
- Added a data export endpoint for both JSON and CSV formats, accessible from any web browser.
- Modern, responsive UI with custom CSS and JavaScript for a smooth user experience.

---
If you have any questions or need further instructions, feel free to ask! 