from fastapi import FastAPI, HTTPException ,APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sqlite3

router = APIRouter()

DB_NAME = "api.db"

# --- Database Setup ---
def create_tables():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS waste_items (
            itemId TEXT,
            name TEXT,
            reason TEXT,
            containerId TEXT,
            startWidth REAL,
            startDepth REAL,
            startHeight REAL,
            endWidth REAL,
            endDepth REAL,
            endHeight REAL
        )''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS return_manifest (
            undockingContainerId TEXT,
            undockingDate TEXT,
            itemId TEXT,
            name TEXT,
            reason TEXT,
            totalVolume REAL,
            totalWeight REAL
        )''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS undocking_logs (
            undockingContainerId TEXT,
            timestamp TEXT,
            itemsRemoved INTEGER
        )''')

create_tables()

# --- Models ---
class Coordinates(BaseModel):
    width: float
    depth: float
    height: float

class Position(BaseModel):
    startCoordinates: Coordinates
    endCoordinates: Coordinates

class WasteItem(BaseModel):
    itemId: str
    name: str
    reason: str
    containerId: str
    position: Position

class ReturnRequest(BaseModel):
    undockingContainerId: str
    undockingDate: str
    maxWeight: float

class ReturnStep(BaseModel):
    step: int
    itemId: str
    itemName: str
    fromContainer: str
    toContainer: str

class RetrievalStep(BaseModel):
    step: int
    action: str
    itemId: str
    itemName: str

class ReturnManifestItem(BaseModel):
    itemId: str
    name: str
    reason: str

class ReturnManifest(BaseModel):
    undockingContainerId: str
    undockingDate: str
    returnItems: List[ReturnManifestItem]
    totalVolume: float
    totalWeight: float

class ReturnPlanResponse(BaseModel):
    success: bool
    returnPlan: List[ReturnStep]
    retrievalSteps: List[RetrievalStep]
    returnManifest: ReturnManifest

class CompleteUndockingRequest(BaseModel):
    undockingContainerId: str
    timestamp: str

class CompleteUndockingResponse(BaseModel):
    success: bool
    itemsRemoved: int

# --- Routes ---
@router.get("/identify")
def identify_waste():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT * FROM waste_items")
        wasteItems = []
        for row in cursor.fetchall():
            wasteItems.append(WasteItem(
                itemId=row[0],
                name=row[1],
                reason=row[2],
                containerId=row[3],
                position=Position(
                    startCoordinates=Coordinates(width=row[4], depth=row[5], height=row[6]),
                    endCoordinates=Coordinates(width=row[7], depth=row[8], height=row[9])
                )
            ))
        return {"success": True, "wasteItems": wasteItems}

@router.post("/return-plan", response_model=ReturnPlanResponse)
def return_plan(request: ReturnRequest):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT * FROM waste_items WHERE containerId = ?", (request.undockingContainerId,))
        rows = cursor.fetchall()

        returnItems = []
        returnPlan = []
        retrievalSteps = []
        totalVolume = 0
        totalWeight = 0  # Placeholder since no weight info is stored

        step = 1
        for row in rows:
            itemId, name, reason, containerId, sw, sd, sh, ew, ed, eh = row
            volume = (ew - sw) * (ed - sd) * (eh - sh)
            totalVolume += volume
            returnItems.append(ReturnManifestItem(itemId=itemId, name=name, reason=reason))
            returnPlan.append(ReturnStep(
                step=step,
                itemId=itemId,
                itemName=name,
                fromContainer=containerId,
                toContainer="ReturnZone"
            ))
            retrievalSteps.append(RetrievalStep(
                step=step,
                action="remove",
                itemId=itemId,
                itemName=name
            ))
            step += 1

            conn.execute("INSERT INTO return_manifest VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (request.undockingContainerId, request.undockingDate, itemId, name, reason, volume, 0))

    return ReturnPlanResponse(
        success=True,
        returnPlan=returnPlan,
        retrievalSteps=retrievalSteps,
        returnManifest=ReturnManifest(
            undockingContainerId=request.undockingContainerId,
            undockingDate=request.undockingDate,
            returnItems=returnItems,
            totalVolume=totalVolume,
            totalWeight=0
        )
    )
@router.post("/complete-undocking", response_model=CompleteUndockingResponse)
def complete_undocking(request: CompleteUndockingRequest):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Count how many waste items are in the container
        cursor.execute(
            "SELECT COUNT(*) AS count FROM waste_items WHERE containerId = ?",
            (request.undockingContainerId,)
        )
        result = cursor.fetchone()
        items_removed = result["count"] if result else 0

        # If there are items, delete them and log the undocking
        if items_removed > 0:
            cursor.execute(
                "DELETE FROM waste_items WHERE containerId = ?",
                (request.undockingContainerId,)
            )
            cursor.execute(
                """
                INSERT INTO undocking_logs (undockingContainerId, timestamp, itemsRemoved)
                VALUES (?, ?, ?)
                """,
                (request.undockingContainerId, request.timestamp, items_removed)
            )
            conn.commit()

    return {
        "success": True,
        "itemsRemoved": items_removed,
        "containerId": request.undockingContainerId,
        "timestamp": request.timestamp
    }

# --- Additional CRUD Endpoints ---
@router.post("/add", response_model=dict)
def add_waste_item(item: WasteItem):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT INTO waste_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (item.itemId, item.name, item.reason, item.containerId,
                      item.position.startCoordinates.width,
                      item.position.startCoordinates.depth,
                      item.position.startCoordinates.height,
                      item.position.endCoordinates.width,
                      item.position.endCoordinates.depth,
                      item.position.endCoordinates.height))
    return {"message": "Waste item added."}

@router.delete("/delete/{item_id}", response_model=dict)
def delete_waste_item(item_id: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM waste_items WHERE itemId = ?", (item_id,))
    return {"message": "Waste item deleted."}

@router.get("/logs", response_model=List[dict])
def get_undocking_logs():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT * FROM undocking_logs")
        return [
            {"undockingContainerId": row[0], "timestamp": row[1], "itemsRemoved": row[2]}
            for row in cursor.fetchall()
        ]

@router.get("/manifest", response_model=List[dict])
def get_return_manifest():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT * FROM return_manifest")
        return [
            {
                "undockingContainerId": row[0],
                "undockingDate": row[1],
                "itemId": row[2],
                "name": row[3],
                "reason": row[4],
                "totalVolume": row[5],
                "totalWeight": row[6]
            }
            for row in cursor.fetchall()
        ]
