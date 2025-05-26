# app/main.py

from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os, requests, json, datetime
from typing import Optional
import csv
from io import StringIO

from .database import SessionLocal, Base, engine
from .dependencies import get_db, get_current_user
from .routers import users, weather
from . import auth, models
from jose.exceptions import JWTError

# Environment & API endpoints
API_KEY      = os.getenv("OPENWEATHER_API_KEY")
CURRENT_URL  = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

# 1. Create tables
Base.metadata.create_all(bind=engine)

# 2. Init app
app = FastAPI(title="Weather API")

# 3. Templates & Static
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 4. DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 5. Current user
# Get current user from cookie
def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = auth.decode_token(token)
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        return None
    return db.query(models.User).get(user_id)

@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db:      Session     = Depends(get_db),
    user:    models.User = Depends(get_current_user)
):
    # If not logged in, show the welcome/index page
    if not user:
        return templates.TemplateResponse("index.html", {"request": request, "user": user})

    # Fetch only this user's saved weather entries
    raw_entries = (
        db.query(models.WeatherRequest)
          .filter(models.WeatherRequest.user_id == user.id)
          .all()
    )

    # Build a minimal list of current-weather snapshots for the template
    entries = []
    for e in raw_entries:
        try:
            data = json.loads(e.response)
        except json.JSONDecodeError:
            continue
        # If forecast JSON, take the first slot, else the current data
        if data.get("list"):
            slot = data["list"][0]
            city = data.get("city", {}).get("name", "")
        else:
            slot = data
            city = data.get("name", "")
        if slot.get("main") and slot.get("weather"):
            entries.append({
                "id":          e.id,
                "city":        city,
                "temp":        slot["main"]["temp"],
                "humidity":    slot["main"]["humidity"],
                "description": slot["weather"][0]["description"],
                "icon":        slot["weather"][0]["icon"]
            })

    return templates.TemplateResponse("home.html", {
        "request": request,
        "user":    user,
        "entries": entries
    })


@app.get("/weather-ui", response_class=HTMLResponse)
def weather_page(
    request: Request,
    user:    models.User = Depends(get_current_user)
):
    # Only logged-in users can fetch new weather
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("weather.html", {
        "request": request,
        "user":    user
    })


@app.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    user:    models.User = Depends(get_current_user)
):
    # Redirect if already logged in
    if user:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("register.html", {
        "request": request,
        "user":    user
    })


@app.post("/register")
def register_user(
    email:    str     = Form(...),
    password: str     = Form(...),
    db:       Session = Depends(get_db)
):
    # Prevent duplicate emails
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(email=email, hashed_pw=auth.hash_pw(password))
    db.add(user)
    db.commit()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    user:    models.User = Depends(get_current_user)
):
    # Redirect if already logged in
    if user:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "user":    user
    })


@app.post("/login")
def login_user(
    email:    str     = Form(...),
    password: str     = Form(...),
    db:       Session = Depends(get_db)
):
    # Authenticate
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not auth.verify_pw(password, user.hashed_pw):
        raise HTTPException(status_code=401, detail="Bad credentials")

    token = auth.create_token(str(user.id))
    resp  = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie("access_token", token, httponly=True)
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie("access_token")
    return resp


@app.get("/history", response_class=HTMLResponse)
def history_page(
    request: Request,
    db:      Session     = Depends(get_db),
    user:    models.User = Depends(get_current_user)
):
    # Aliased to home (same logic and template)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    return home(request, db, user)


@app.get("/history/{weather_id}/edit", response_class=HTMLResponse)
def edit_page(
    weather_id: int,
    request:    Request,
    db:         Session     = Depends(get_db),
    user:       models.User = Depends(get_current_user)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    rec = db.get(models.WeatherRequest, weather_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "user":    user,
        "entry":   rec
    })


@app.post("/history/{weather_id}/edit")
def edit_submit(
    weather_id:    int,
    location:      str              = Form(...),
    start_date_raw: str | None      = Form(None),
    end_date_raw:   str | None      = Form(None),
    db:            Session          = Depends(get_db),
    user:          models.User      = Depends(get_current_user)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    rec = db.get(models.WeatherRequest, weather_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    # Parse optional dates
    start_date = None
    end_date   = None
    if start_date_raw:
        try:
            start_date = datetime.date.fromisoformat(start_date_raw)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    if end_date_raw:
        try:
            end_date = datetime.date.fromisoformat(end_date_raw)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    # Validate if both provided
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="Invalid date range")

    # Update fields
    rec.location = location.strip()
    if start_date is not None:
        rec.start_date = start_date
    if end_date is not None:
        rec.end_date = end_date

    # Re-fetch JSON for updated location
    params      = {"appid": API_KEY, "units": "imperial", "q": rec.location}
    use_fc      = bool(rec.start_date and rec.end_date)
    fetch_url   = FORECAST_URL if use_fc else CURRENT_URL
    resp        = requests.get(fetch_url, params=params, timeout=5)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch updated weather")

    rec.response = resp.text
    db.commit()
    return RedirectResponse("/history", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/history/{weather_id}/delete")
def delete_entry(
    weather_id: int,
    db:         Session     = Depends(get_db),
    user:       models.User = Depends(get_current_user)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    rec = db.get(models.WeatherRequest, weather_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    db.delete(rec)
    db.commit()
    return RedirectResponse("/history", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/export")
def export_data(
    format: str = "json",
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    entries = (
        db.query(models.WeatherRequest)
          .filter(models.WeatherRequest.user_id == user.id)
          .all()
    )
    export_list = [
        {
            "id": e.id,
            "location": e.location,
            "start_date": e.start_date.isoformat() if e.start_date else None,
            "end_date": e.end_date.isoformat() if e.end_date else None,
            "response": e.response,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]
    if format == "csv":
        si = StringIO()
        writer = csv.DictWriter(si, fieldnames=export_list[0].keys() if export_list else [])
        writer.writeheader()
        writer.writerows(export_list)
        si.seek(0)
        return StreamingResponse(si, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=weather_export.csv"})
    else:
        return JSONResponse(export_list)

# 14. JSON API routers
app.include_router(users.router)
app.include_router(weather.router)
