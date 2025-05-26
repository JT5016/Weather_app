# app/routers/weather.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models, schemas
from ..dependencies import get_db, get_current_user
import requests, os
import json
from datetime import timedelta, datetime, date

router = APIRouter(prefix="/weather", tags=["Weather"])

API_KEY      = os.getenv("OPENWEATHER_API_KEY")
CURRENT_URL  = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

@router.post("/", response_model=schemas.WeatherOut, status_code=status.HTTP_201_CREATED)
def create_weather(
    payload: schemas.WeatherCreate,
    db:      Session     = Depends(get_db),
    user:    models.User = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 1. Validate date range
    if payload.start_date and payload.end_date:
        if payload.start_date > payload.end_date:
            raise HTTPException(400, "start_date must be on or before end_date")
        if (payload.end_date - payload.start_date) > timedelta(days=5):
            raise HTTPException(400, "Date range cannot exceed 5 days on free API")

    # 2. Build API params
    params = {"appid": API_KEY, "units": "imperial"}
    loc = payload.location.strip()
    if loc.replace(" ", "").isdigit():
        params["zip"] = f"{loc},US"
    else:
        params["q"] = f"{loc},US"

    # 3. Choose endpoint
    use_forecast = bool(
        payload.start_date and
        payload.end_date and
        (payload.end_date - payload.start_date) >= timedelta(days=1)
    )
    url = FORECAST_URL if use_forecast else CURRENT_URL

    resp = requests.get(url, params=params, timeout=5)
    if resp.status_code != 200:
        raise HTTPException(404, "Location not found or API error")

    # Filter forecast to only include selected date range
    if use_forecast and payload.start_date and payload.end_date:
        data = resp.json()
        start = payload.start_date
        end = payload.end_date
        filtered_list = [
            item for item in data.get("list", [])
            if start <= date.fromisoformat(item["dt_txt"][:10]) <= end
        ]
        data["list"] = filtered_list
        resp_text = json.dumps(data)
    else:
        resp_text = resp.text

    # 4. Persist with user_id
    record = models.WeatherRequest(
        user_id    = user.id,
        location   = loc,
        start_date = payload.start_date,
        end_date   = payload.end_date,
        response   = resp_text
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=list[schemas.WeatherOut])
def read_all_weather(
    db:   Session        = Depends(get_db),
    user: models.User    = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return (
        db.query(models.WeatherRequest)
          .filter(models.WeatherRequest.user_id == user.id)
          .all()
    )


@router.get("/{weather_id}", response_model=schemas.WeatherOut)
def read_weather(
    weather_id: int,
    db:         Session        = Depends(get_db),
    user:       models.User    = Depends(get_current_user),
):
    rec = db.get(models.WeatherRequest, weather_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(404, "Record not found")
    return rec


@router.put("/{weather_id}", response_model=schemas.WeatherOut)
def update_weather(
    weather_id: int,
    payload:    schemas.WeatherUpdate,
    db:         Session        = Depends(get_db),
    user:       models.User    = Depends(get_current_user),
):
    rec = db.get(models.WeatherRequest, weather_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(404, "Record not found")

    # Validate date range...
    if payload.start_date and payload.end_date:
        if payload.start_date > payload.end_date:
            raise HTTPException(400, "Invalid date range")
        if (payload.end_date - payload.start_date) > timedelta(days=5):
            raise HTTPException(400, "Date range cannot exceed 5 days on free API")

    # Update fields...
    if payload.location:
        rec.location = payload.location.strip()
    if payload.start_date is not None:
        rec.start_date = payload.start_date
    if payload.end_date is not None:
        rec.end_date = payload.end_date

    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/{weather_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weather(
    weather_id: int,
    db:         Session        = Depends(get_db),
    user:       models.User    = Depends(get_current_user),
):
    rec = db.get(models.WeatherRequest, weather_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(404, "Record not found")
    db.delete(rec)
    db.commit()


@router.get("/{weather_id}/forecast")
def get_saved_forecast(
    weather_id: int,
    db:         Session        = Depends(get_db),
    user:       models.User    = Depends(get_current_user),
):
    rec = db.get(models.WeatherRequest, weather_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(404, "Record not found")

    # Always fetch the full 5-day forecast live from the API
    params = {"appid": API_KEY, "units": "imperial", "q": rec.location}
    resp = requests.get(FORECAST_URL, params=params, timeout=5)
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, "Forecast API error")
    return {"response": resp.text}

@router.get("/{weather_id}/sun", response_model=schemas.SunTimes)
def get_sun_times(
    weather_id: int,
    db:         Session     = Depends(get_db),
    user:       models.User = Depends(get_current_user),
):
    rec = db.get(models.WeatherRequest, weather_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    data = json.loads(rec.response)

    # try top-level coord (current weather) or city.coord (forecast)
    coord = data.get("coord") or data.get("city", {}).get("coord")
    if not coord or coord.get("lat") is None or coord.get("lon") is None:
        raise HTTPException(status_code=400, detail="No coordinates available")

    lat, lon = coord["lat"], coord["lon"]

    resp = requests.get(
        "https://api.sunrise-sunset.org/json",
        params={"lat": lat, "lng": lon, "formatted": 0},
        timeout=5
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Sun API error")

    results = resp.json().get("results", {})
    return {
        "sunrise": results["sunrise"],
        "sunset":  results["sunset"]
    }