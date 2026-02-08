from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from database.db import get_db
from database.models import ActionLog
from pydantic import BaseModel

router = APIRouter(prefix="/api/actions", tags=["actions"])

class ActionResponse(BaseModel):
    id: int
    product_id: int
    action_type: str
    reason: str = None
    success: bool
    created_at: str
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[ActionResponse])
def list_actions(
    action_type: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List action logs"""
    query = db.query(ActionLog)
    
    if action_type:
        query = query.filter(ActionLog.action_type == action_type)
    
    actions = query.order_by(ActionLog.created_at.desc()).offset(skip).limit(limit).all()
    return actions

@router.get("/summary")
def actions_summary(db: Session = Depends(get_db)) -> Dict:
    """Get summary of actions"""
    
    summary = db.query(
        ActionLog.action_type,
        func.count(ActionLog.id).label('count')
    ).group_by(ActionLog.action_type).all()
    
    return {
        "summary": [{"action_type": s[0], "count": s[1]} for s in summary]
    }
