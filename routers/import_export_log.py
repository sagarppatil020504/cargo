from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import StreamingResponse
import csv
import io
import datetime
from typing import Optional
import sqlite3 

db_path = "api.db"

def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
router = APIRouter()

@router.post("/import/items")
async def import_items(file: UploadFile = File(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    reader = csv.DictReader(io.StringIO((await file.read()).decode()))

    items_imported = 0
    errors = []

    for row_num, row in enumerate(reader, start=1):
        try:
            cursor.execute('''
                INSERT INTO items (itemId, name, width, depth, height, priority, expiryDate, usageLimit, preferredZone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['itemId'], row['name'], float(row['width']), float(row['depth']), float(row['height']),
                int(row['priority']), row['expiryDate'], int(row['usageLimit']), row['preferredZone']
            ))
            items_imported += 1
        except Exception as e:
            errors.append({"row": row_num, "message": str(e)})

    conn.commit()
    conn.close()
    return {"success": True, "itemsImported": items_imported, "errors": errors}


@router.post("/import/containers")
async def import_containers(file: UploadFile = File(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    reader = csv.DictReader(io.StringIO((await file.read()).decode()))

    containers_imported = 0
    errors = []

    for row_num, row in enumerate(reader, start=1):
        try:
            cursor.execute('''
                INSERT INTO containers (containerId, zone, width, depth, height)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                row['containerId'], row['zone'], float(row['width']), float(row['depth']), float(row['height'])
            ))
            containers_imported += 1
        except Exception as e:
            errors.append({"row": row_num, "message": str(e)})

    conn.commit()
    conn.close()
    return {"success": True, "containersImported": containers_imported, "errors": errors}


@router.get("/export/arrangement")
async def export_arrangement():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT itemId, containerId, 
               startW, startD, startH, endW, endD, endH 
        FROM placements
    """)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Item ID", "Container ID", "Coordinates (W1,D1,H1)", "Coordinates (W2,D2,H2)"])

    for row in cursor.fetchall():
        writer.writerow([
            row['itemId'],
            row['containerId'],
            f"({row['startW']},{row['startD']},{row['startH']})",
            f"({row['endW']},{row['endD']},{row['endH']})"
        ])

    output.seek(0)
    conn.close()

    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=arrangement.csv"})


@router.get("/logs")
async def get_logs(
    startDate: str = Query(...),
    endDate: str = Query(...),
    itemId: Optional[str] = None,
    userId: Optional[str] = None,
    actionType: Optional[str] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM logs WHERE timestamp BETWEEN ? AND ?"
    params = [startDate, endDate]

    if itemId:
        query += " AND itemId = ?"
        params.append(itemId)
    if userId:
        query += " AND userId = ?"
        params.append(userId)
    if actionType:
        query += " AND actionType = ?"
        params.append(actionType)

    cursor.execute(query, params)
    logs = cursor.fetchall()
    conn.close()

    result = []
    for log in logs:
        result.append({
            "timestamp": log["timestamp"],
            "userId": log["userId"],
            "actionType": log["actionType"],
            "itemId": log["itemId"],
            "details": {
                "fromContainer": log["fromContainer"],
                "toContainer": log["toContainer"],
                "reason": log["reason"]
            }
        })

    return {"logs": result}
