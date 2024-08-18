
from typing import Any
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.models.notification import Notification
from app.routes.dependencies import get_db
from app.services.auth import get_current_user


router = APIRouter()
@router.get("/notifications/")
async def get_user_notifications(current_user: dict = Depends(get_current_user), db: Any = Depends(get_db)):
    try:
        notifications = list(db.notifications.find({"user": current_user['email']}))
        for notification in notifications:
            notification['_id'] = str(notification['_id'])  # Convert ObjectId to string
        return {"notifications": notifications}  # Return raw notifications list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/notifications/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: Any = Depends(get_db)
):
   
    try:
        result = db.notifications.update_one(
            {"_id": ObjectId(notification_id), "user": current_user['email']},
            {"$set": {"isRead": True}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found or already marked as read")
        
        return {"message": "Notification marked as read successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications/{notification_id}")
async def get_notification_by_id(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        notification = db.notifications.find_one({"_id": ObjectId(notification_id), "user": current_user['email']})
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        notification['_id'] = str(notification['_id'])  # Convert ObjectId to string
        return notification
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
