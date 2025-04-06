from fastapi import FastAPI, HTTPException, Query, APIRouter
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sqlite3

router = APIRouter()

DB_NAME = "api.db"

# --- Database Setup ---
def create_usage_tables():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS item_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            itemId TEXT,
            userId TEXT,
            timestamp TEXT
        )
        """)

create_usage_tables()

# --- Models ---
class Coordinates(BaseModel):
    width: float
    depth: float
    height: float

class Position(BaseModel):
    startCoordinates: Coordinates
    endCoordinates: Coordinates

class RetrievedItem(BaseModel):
    itemId: str
    name: str
    containerId: str
    zone: str
    position: Position

class RetrievalStep(BaseModel):
    step: int
    action: str
    itemId: str
    itemName: str

class SearchResponse(BaseModel):
    success: bool
    found: bool
    item: Optional[RetrievedItem]
    retrievalSteps: Optional[List[RetrievalStep]] = []

class RetrieveRequest(BaseModel):
    itemId: str
    userId: str
    timestamp: str

class PlaceBackRequest(BaseModel):
    itemId: str
    userId: str
    timestamp: str
    containerId: str
    position: Position

# --- Routes ---
@router.get("/search", response_model=SearchResponse)
def search_item(itemId: Optional[str] = Query(None), itemName: Optional[str] = Query(None), userId: Optional[str] = None):
    if not itemId and not itemName:
        raise HTTPException(status_code=400, detail="Either itemId or itemName must be provided.")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if itemId:
            cursor.execute("SELECT i.itemId, i.name, c.containerId, c.zone, p.startWidth, p.startDepth, p.startHeight, p.endWidth, p.endDepth, p.endHeight FROM items i JOIN placements p ON i.itemId = p.itemId JOIN containers c ON p.containerId = c.containerId WHERE i.itemId = ?", (itemId,))
        else:
            cursor.execute("SELECT i.itemId, i.name, c.containerId, c.zone, p.startWidth, p.startDepth, p.startHeight, p.endWidth, p.endDepth, p.endHeight FROM items i JOIN placements p ON i.itemId = p.itemId JOIN containers c ON p.containerId = c.containerId WHERE i.name = ?", (itemName,))

        row = cursor.fetchone()
        if not row:
            return SearchResponse(success=True, found=False, item=None, retrievalSteps=[])

        item = RetrievedItem(
            itemId=row[0],
            name=row[1],
            containerId=row[2],
            zone=row[3],
            position=Position(
                startCoordinates=Coordinates(width=row[4], depth=row[5], height=row[6]),
                endCoordinates=Coordinates(width=row[7], depth=row[8], height=row[9])
            )
        )

        steps = [
            RetrievalStep(step=1, action="setAside", itemId=item.itemId, itemName=item.name),
            RetrievalStep(step=2, action="retrieve", itemId=item.itemId, itemName=item.name)
        ]

        return SearchResponse(success=True, found=True, item=item, retrievalSteps=steps)

@router.post("/retrieve")
def retrieve_item(req: RetrieveRequest):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if the item exists in the items table
        cursor.execute("SELECT * FROM items WHERE itemId = ?", (req.itemId,))
        item = cursor.fetchone()

        if not item:
            return {"success": False, "message": "Item not found."}

        # Insert usage log if item exists
        cursor.execute(
            "INSERT INTO item_usage (itemId, userId, timestamp) VALUES (?, ?, ?)",
            (req.itemId, req.userId, req.timestamp)
        )
        conn.commit()

    return {"success": True, "message": "Item retrieval logged successfully."}

@router.post("/place")
def place_item_back(req: PlaceBackRequest):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            # Remove old placement if exists
            cursor.execute("DELETE FROM placements WHERE itemId = ?", (req.itemId,))

            # Insert the new placement data
            cursor.execute("""
                INSERT INTO placements (
                    itemId, containerId,
                    startWidth, startDepth, startHeight,
                    endWidth, endDepth, endHeight
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req.itemId, req.containerId,
                req.position.startCoordinates.width,
                req.position.startCoordinates.depth,
                req.position.startCoordinates.height,
                req.position.endCoordinates.width,
                req.position.endCoordinates.depth,
                req.position.endCoordinates.height
            ))

            conn.commit()

        return {"success": True, "message": f"Item {req.itemId} placed successfully."}

    except Exception as e:
        return {"success": False, "message": f"Error placing item: {str(e)}"}