from fastapi import FastAPI, HTTPException ,APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import sqlite3
import uuid

router = APIRouter()

# --- Database Setup ---
DB_NAME = "api.db"

def create_tables():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            itemId TEXT PRIMARY KEY,
            name TEXT,
            width REAL,
            depth REAL,
            height REAL,
            priority INTEGER,
            expiryDate TEXT,
            usageLimit INTEGER,
            preferredZone TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS containers (
            containerId TEXT PRIMARY KEY,
            zone TEXT,
            width REAL,
            depth REAL,
            height REAL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS placements (
            itemId TEXT,
            containerId TEXT,
            startWidth REAL,
            startDepth REAL,
            startHeight REAL,
            endWidth REAL,
            endDepth REAL,
            endHeight REAL
        )
        """)

create_tables()

# --- Models ---
class Coordinates(BaseModel):
    width: float
    depth: float
    height: float

class Position(BaseModel):
    startCoordinates: Coordinates
    endCoordinates: Coordinates

class Placement(BaseModel):
    itemId: str
    containerId: str
    position: Position

class Rearrangement(BaseModel):
    step: int
    action: str  # "move", "remove", "place"
    itemId: str
    fromContainer: Optional[str]
    fromPosition: Optional[Position]
    toContainer: Optional[str]
    toPosition: Optional[Position]

class Item(BaseModel):
    itemId: str
    name: str
    width: float
    depth: float
    height: float
    priority: int
    expiryDate: str
    usageLimit: int
    preferredZone: str

class Container(BaseModel):
    containerId: str
    zone: str
    width: float
    depth: float
    height: float

class PlacementRequest(BaseModel):
    items: List[Item]
    containers: List[Container]

class PlacementResponse(BaseModel):
    success: bool
    placements: List[Placement]
    rearrangements: List[Rearrangement]

# --- Helper Functions ---
def save_item_to_db(item: Item):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        INSERT OR REPLACE INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item.itemId, item.name, item.width, item.depth, item.height,
              item.priority, item.expiryDate, item.usageLimit, item.preferredZone))

def save_container_to_db(container: Container):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        INSERT OR REPLACE INTO containers VALUES (?, ?, ?, ?, ?)
        """, (container.containerId, container.zone, container.width,
              container.depth, container.height))
class SpaceAllotmentHolder:
    def __init__(self, item_id: str, start: Coordinates, end: Coordinates):
        self.occupied_spaces: List[dict] = []
        self.item_id = item_id
        self.start = start
        self.end = end

    def volume(self):
        return (
            (self.end.width - self.start.width) *
            (self.end.depth - self.start.depth) *
            (self.end.height - self.start.height)
        )

    def __repr__(self):
        return f"<Allotment {self.item_id}: ({self.start}) → ({self.end})>"

    def is_space_free(self, start: Coordinates, item: Item) -> bool:
        for entry in self.occupied_spaces:
            s = entry['start']
            e = entry['end']
            # Check for overlap
            if not (
                start.width + item.width <= s.width or
                start.width >= e.width or
                start.depth + item.depth <= s.depth or
                start.depth >= e.depth or
                start.height + item.height <= s.height or
                start.height >= e.height
            ):
                return False
        return True

    def add_space(self, item_id: str, start: Coordinates, item: Item):
        end = Coordinates(
            width=start.width + item.width,
            depth=start.depth + item.depth,
            height=start.height + item.height,
        )
        self.occupied_spaces.append({
            'itemId': item_id,
            'start': start,
            'end': end,
        })

    def place_item_with_check(self, container, item: Item) -> Optional[Coordinates]:
        max_w, max_d, max_h = container.width, container.depth, container.height

        for w in range(0, int(max_w - item.width) + 1):
            for d in range(0, int(max_d - item.depth) + 1):
                for h in range(0, int(max_h - item.height) + 1):
                    start = Coordinates(width=w, depth=d, height=h)
                    if self.is_space_free(start, item):
                        self.add_space(item.itemId, start, item)
                        return start
        return None

# Track used space per container
class SpaceTracker:
    def __init__(self, container: Container):
        self.container = container
        self.allotments: List[SpaceAllotmentHolder] = []
        self.cursor = Coordinates(width=0, depth=0, height=0)
        self.dynamic_checker = SpaceAllotmentHolder(item_id="init", start=self.cursor, end=self.cursor)

    def can_fit(self, item: Item) -> bool:
        return (
            item.width <= self.container.width and
            item.depth <= self.container.depth and
            item.height <= self.container.height
        )

    def place_item(self, item: Item) -> Optional[Position]:
        if not self.can_fit(item):
            return None

        # First placement attempt using cursor
        start = Coordinates(
            width=self.cursor.width,
            depth=self.cursor.depth,
            height=self.cursor.height
        )
        end = Coordinates(
            width=start.width + item.width,
            depth=start.depth + item.depth,
            height=start.height + item.height
        )

        if (end.width > self.container.width or
            end.depth > self.container.depth or
            end.height > self.container.height):
            # Try dynamic space check instead
            checked_pos = self.dynamic_checker.place_item_with_check(self.container, item)
            if checked_pos:
                return Position(
                    startCoordinates=checked_pos,
                    endCoordinates=Coordinates(
                        width=checked_pos.width + item.width,
                        depth=checked_pos.depth + item.depth,
                        height=checked_pos.height + item.height
                    )
                )
            return None

        # Update both logs and cursor
        allotment = SpaceAllotmentHolder(item.itemId, start, end)
        self.allotments.append(allotment)
        self.dynamic_checker.add_space(item.itemId, start, item)
        self.cursor.height += item.height  # simple stacking

        return Position(startCoordinates=start, endCoordinates=end)

    def total_used_volume(self):
        return sum(a.volume() for a in self.allotments)

    def utilization_percentage(self):
        total_container_volume = (
            self.container.width * self.container.depth * self.container.height
        )
        return (self.total_used_volume() / total_container_volume) * 100
    
# --- API Endpoints ---
@router.post("/placement", response_model=PlacementResponse)
def place_items(request: PlacementRequest):
    placements = []
    rearrangements = []

    for item in request.items:
        save_item_to_db(item)
    for container in request.containers:
        save_container_to_db(container)
    
    space_trackers = {c.containerId: SpaceTracker(c) for c in request.containers}

    step = 1
    for item in request.items:
        matched = False
        for container in request.containers:
            if item.preferredZone == container.zone:
                tracker = space_trackers[container.containerId]
                pos = tracker.place_item(item)
                if pos:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("""
                        INSERT INTO placements VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            item.itemId, container.containerId,
                            pos.startCoordinates.width, pos.startCoordinates.depth, pos.startCoordinates.height,
                            pos.endCoordinates.width, pos.endCoordinates.depth, pos.endCoordinates.height
                        ))
                    placements.append(Placement(
                        itemId=item.itemId,
                        containerId=container.containerId,
                        position=pos
                    ))
                    rearrangements.append(Rearrangement(
                        step=step,
                        action="place",
                        itemId=item.itemId,
                        fromContainer=None,
                        fromPosition=None,
                        toContainer=container.containerId,
                        toPosition=pos
                    ))
                    step += 1
                    matched = True
                    break
        if not matched:
            continue

    return PlacementResponse(
        success=True,
        placements=placements,
        rearrangements=rearrangements
    )

# --- CRUD ROUTES ---
@router.get("/items", response_model=List[Item])
def get_items():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT * FROM items")
        return [Item(
            itemId=row[0], name=row[1], width=row[2], depth=row[3], height=row[4],
            priority=row[5], expiryDate=row[6], usageLimit=row[7], preferredZone=row[8]
        ) for row in cursor.fetchall()]

@router.post("/add-container", response_model=List[Container])
def add_container(container: Container):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # Optional: check if container already exists
        cursor.execute("SELECT * FROM containers WHERE containerId = ?", (container.containerId,))
        existing = cursor.fetchone()
        if existing:
            return {"success": False, "message": "Container already exists."}
        
        # Insert into DB
        cursor.execute("""
            INSERT INTO containers (containerId, zone, width, depth, height)
            VALUES (?, ?, ?, ?, ?)
        """, (container.containerId, container.zone, container.width, container.depth, container.height))
        
        conn.commit()

    return {"success": True, "message": "Container added successfully."}

@router.get("/containers", response_model=List[Container])
def get_containers():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT * FROM containers")
        return [Container(
            containerId=row[0], zone=row[1], width=row[2], depth=row[3], height=row[4]
        ) for row in cursor.fetchall()]

@router.get("/placements", response_model=List[Placement])
def get_placements():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT * FROM placements")
        return [
            Placement(
                itemId=row[0],
                containerId=row[1],
                position=Position(
                    startCoordinates=Coordinates(width=row[2], depth=row[3], height=row[4]),
                    endCoordinates=Coordinates(width=row[5], depth=row[6], height=row[7])
                )
            ) for row in cursor.fetchall()
        ]

@router.put("/items/{item_id}")
def update_item(item_id: str, item: Item):
    item.itemId = item_id
    save_item_to_db(item)
    return {"message": "Item updated."}

@router.put("/containers/{container_id}")
def update_container(container_id: str, container: Container):
    container.containerId = container_id
    save_container_to_db(container)
    return {"message": "Container updated."}

@router.delete("/items/{item_id}")
def delete_item(item_id: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM items WHERE itemId = ?", (item_id,))
    return {"message": "Item deleted."}

@router.delete("/containers/{container_id}")
def delete_container(container_id: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM containers WHERE containerId = ?", (container_id,))
    return {"message": "Container deleted."}
