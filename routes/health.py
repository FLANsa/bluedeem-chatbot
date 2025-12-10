"""Health check routes."""
from fastapi import APIRouter, HTTPException
from data.handler import data_handler
from data.db import get_database_session
from models.booking import BookingTicket

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "ok", "service": "bluedeem-chatbot"}


@router.get("/health/data")
async def health_data():
    """Check data loading status."""
    try:
        doctors = data_handler.get_doctors()
        branches = data_handler.get_branches()
        services = data_handler.get_services()
        
        return {
            "status": "ok",
            "doctors_count": len(doctors),
            "branches_count": len(branches),
            "services_count": len(services)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data loading error: {str(e)}")


@router.get("/health/db")
async def health_db():
    """Check database connection."""
    try:
        db = get_database_session()
        # Try a simple query
        count = db.query(BookingTicket).count()
        return {
            "status": "ok",
            "database": "connected",
            "bookings_count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

