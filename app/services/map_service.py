from app.core.config import settings


def is_mapbox_configured() -> bool:
    return bool(settings.MAPBOX_TOKEN)


def get_mapbox_config():
    if not is_mapbox_configured():
        return None

    return {
        "token": settings.MAPBOX_TOKEN,
        "style": settings.MAPBOX_STYLE_URL or "mapbox://styles/mapbox/satellite-v9",
    }
