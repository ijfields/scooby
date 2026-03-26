from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

# Endpoint routers will be included here in later workstreams:
# from app.api.v1.endpoints import auth, stories, episodes, scenes, styles, generation, export
# router.include_router(auth.router, prefix="/auth", tags=["auth"])
# router.include_router(stories.router, prefix="/stories", tags=["stories"])
# router.include_router(episodes.router, prefix="/episodes", tags=["episodes"])
# router.include_router(scenes.router, prefix="/scenes", tags=["scenes"])
# router.include_router(styles.router, prefix="/styles", tags=["styles"])
# router.include_router(generation.router, prefix="/generation", tags=["generation"])
# router.include_router(export.router, prefix="/export", tags=["export"])
