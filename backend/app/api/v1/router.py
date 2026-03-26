from fastapi import APIRouter

from app.api.v1.endpoints import auth, episodes, export, generation, stories, styles

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Endpoint routers added in later workstreams:
router.include_router(stories.router, prefix="/stories", tags=["stories"])
router.include_router(episodes.router, prefix="/episodes", tags=["episodes"])
# router.include_router(scenes.router, prefix="/scenes", tags=["scenes"])
router.include_router(styles.router, prefix="/styles", tags=["styles"])
router.include_router(generation.router, tags=["generation"])
router.include_router(export.router, tags=["export"])
