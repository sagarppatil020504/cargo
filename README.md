**Cargo Management System - API Documentation (Brief Overview)**

---

### 📅 Purpose
To manage the logistics of placing, retrieving, and managing items within containers for a cargo system, including waste and undocking operations.

---

### 📊 Database Tables
- **containers**: Holds container metadata (ID, zone, dimensions).
- **placements**: Stores item placements inside containers.
- **items**: Stores item metadata.
- **item_usage**: Logs when items are retrieved.
- **waste_items**: Logs waste items with reasons and positions.
- **undocking_logs**: Logs items removed during undocking events.

---

### 🔍 Endpoints Overview

#### 1. **/api/add-container** `POST`
- Adds a new container.
```json
{
  "containerId": "C-001",
  "zone": "A",
  "width": 10.0,
  "depth": 5.0,
  "height": 4.0
}
```

#### 2. **/api/place** `POST`
- Places an item in a container.
- Deletes old position if already placed.
```json
{
  "itemId": "item001",
  "containerId": "C-001",
  "position": {
    "startCoordinates": {"width": 1, "depth": 2, "height": 0},
    "endCoordinates": {"width": 3, "depth": 4, "height": 2}
  }
}
```

#### 3. **/api/retrieve** `POST`
- Logs retrieval of an item.
```json
{
  "itemId": "item001",
  "userId": "sag001",
  "timestamp": "2025-04-06T15:30:00Z"
}
```

#### 4. **/api/add-waste-item** `POST`
- Logs a waste item with its location and reason.
```json
{
  "itemId": "item001",
  "name": "BrokenBox",
  "reason": "Damaged",
  "containerId": "C-002",
  "position": {
    "startCoordinates": {"width": 0, "depth": 0, "height": 0},
    "endCoordinates": {"width": 2, "depth": 2, "height": 2}
  }
}
```

#### 5. **/api/complete-undocking** `POST`
- Clears waste items from a container and logs the removal.
```json
{
  "undockingContainerId": "C-102",
  "timestamp": "2025-04-06T14:30:00Z"
}
```
**Response:**
```json
{
  "success": true,
  "itemsRemoved": 4
}
```

#### 6. **/api/search** `GET`
- Search by itemId or itemName (userId optional).
```url
/api/search?itemId=item001&userId=002
```

---

### 🧱 Placement Logic
- Items are placed using greedy algorithm.
- If space is free, it's logged in `placements` table.
- Volumes are checked using dimensions of the container and items.

---

### 🔢 Sample Item CSV (for Postman Uploads)
```
itemId,name,width,depth,height,priority,expiryDate,usageLimit,preferredZone
item01,Box,2,2,2,1,2025-04-10,5,A
item02,Tank,3,3,3,2,2025-04-20,3,B
```

---

### 🔧 Future Enhancements
- Role-based access.
- Real-time placement simulation UI.
- Automatic placement suggestion AI.

---

### ✅ Maintained by: sagar
### ⏰ Last Updated: April 6, 2025

