from fastapi import FastAPI
from routers import placement_api, waste_management, import_export_log, time_sim, Item_retrival

app = FastAPI()

# Register routers
app.include_router(placement_api.router, prefix="/api", tags=["Placement"])
app.include_router(Item_retrival.router, prefix="/api", tags=["Item Retrieval"])
app.include_router(waste_management.router, prefix="/api/waste", tags=["Waste Management"])
app.include_router(import_export_log.router, prefix="/api", tags=["Logs"])
app.include_router(time_sim.router, prefix="/api/simulate", tags=["Simulation"])
