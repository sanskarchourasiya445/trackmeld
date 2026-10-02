from fastapi import APIRouter
from backend.app.api.health import router as health_router
from backend.app.api.v1.stations import router as stations_router
from backend.app.api.v1.sections import router as sections_router
from backend.app.api.v1.trains import router as trains_router
from backend.app.api.v1.rules import router as rules_router
from backend.app.api.v1.corridors import router as corridors_router
from backend.app.api.v1.movements import router as movements_router
from backend.app.api.v1.scenarios import router as scenarios_router
from backend.app.api.v1.work_orders import router as work_orders_router
from backend.app.api.v1.tasks import router as tasks_router
from backend.app.api.v1.resources import router as resources_router

api_router = APIRouter()

# Core health probes (mounted at root)
api_router.include_router(health_router)

# V1 API routes
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(stations_router)
v1_router.include_router(sections_router)
v1_router.include_router(trains_router)
v1_router.include_router(rules_router)
v1_router.include_router(corridors_router)
v1_router.include_router(movements_router)
v1_router.include_router(scenarios_router)
v1_router.include_router(work_orders_router)
v1_router.include_router(tasks_router)
v1_router.include_router(resources_router)

api_router.include_router(v1_router)
