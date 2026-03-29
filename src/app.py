"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

from storage import (
    init_db,
    list_activities,
    signup_for_activity as storage_signup_for_activity,
    unregister_from_activity as storage_unregister_from_activity,
    ActivityNotFoundError,
    DuplicateSignupError,
    MissingSignupError,
)

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

init_db()

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return list_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    try:
        storage_signup_for_activity(activity_name, email)
    except ActivityNotFoundError:
        raise HTTPException(status_code=404, detail="Activity not found")
    except DuplicateSignupError:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    try:
        storage_unregister_from_activity(activity_name, email)
    except ActivityNotFoundError:
        raise HTTPException(status_code=404, detail="Activity not found")
    except MissingSignupError:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    return {"message": f"Unregistered {email} from {activity_name}"}
