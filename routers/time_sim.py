from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3

router = APIRouter()

# Database setup
db_path = "api.db"

def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Pydantic models
class SimItem(BaseModel):
    itemId: Optional[str] = None
    name: Optional[str] = None

class TimeSimRequest(BaseModel):
    numOfDays: Optional[int] = None
    toTimestamp: Optional[str] = None
    itemsToBeUsedPerDay: List[SimItem]

class UsedItemResponse(BaseModel):
    itemId: str
    name: str
    remainingUses: int

class ItemInfo(BaseModel):
    itemId: str
    name: str

class TimeSimResponse(BaseModel):
    success: bool
    newDate: str
    changes: dict

# Initialize table if needed
def initialize_time_simulation_table():
    with get_db_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS time_simulation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sim_date TEXT,
            itemId TEXT,
            itemName TEXT,
            remainingUses INTEGER,
            expired INTEGER DEFAULT 0,
            depleted INTEGER DEFAULT 0
        )
        """)
        conn.commit()

@router.post("/simulate/day", response_model=TimeSimResponse)
def simulate_day(request: TimeSimRequest):
    initialize_time_simulation_table()
    current_date = datetime.now()

    if request.toTimestamp:
        try:
            target_date = datetime.fromisoformat(request.toTimestamp)
            num_days = (target_date - current_date).days
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid timestamp format")
    elif request.numOfDays is not None:
        num_days = request.numOfDays
    else:
        raise HTTPException(status_code=400, detail="Either numOfDays or toTimestamp must be provided")

    used_items = []
    expired_items = []
    depleted_items = []

    with get_db_connection() as conn:
        for _ in range(num_days):
            sim_date = current_date.strftime("%Y-%m-%d")
            for item in request.itemsToBeUsedPerDay:
                cur = conn.cursor()
                if item.itemId:
                    cur.execute("SELECT usageLimit, expiryDate FROM items WHERE itemId = ?", (item.itemId,))
                elif item.name:
                    cur.execute("SELECT usageLimit, expiryDate, itemId FROM items WHERE name = ?", (item.name,))
                row = cur.fetchone()
                if not row:
                    continue
                usage_limit = row["usageLimit"]
                expiry_date = datetime.fromisoformat(row["expiryDate"])
                item_id = item.itemId if item.itemId else row["itemId"]

                new_usage = usage_limit - 1
                depleted = new_usage <= 0
                expired = current_date.date() >= expiry_date.date()

                conn.execute("""
                    UPDATE items SET usageLimit = ? WHERE itemId = ?
                """, (new_usage, item_id))

                conn.execute("""
                    INSERT INTO time_simulation (sim_date, itemId, itemName, remainingUses, expired, depleted)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    sim_date,
                    item_id,
                    item.name,
                    new_usage,
                    int(expired),
                    int(depleted)
                ))

                used_items.append({"itemId": item_id, "name": item.name, "remainingUses": new_usage})
                if expired:
                    expired_items.append({"itemId": item_id, "name": item.name})
                if depleted:
                    depleted_items.append({"itemId": item_id, "name": item.name})

            current_date += timedelta(days=1)

    return {
        "success": True,
        "newDate": current_date.isoformat(),
        "changes": {
            "itemsUsed": used_items,
            "itemsExpired": expired_items,
            "itemsDepletedToday": depleted_items
        }
    }
