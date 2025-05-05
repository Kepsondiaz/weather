from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")  # Crée un serveur FastMCP pour l'application météo

# Constants
NWS_API_BASE = "https://api.weather.gov"  # URL de base de l'API météo nationale américaine
USER_AGENT = "weather-app/1.0"  # Identifiant de l'application


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Fait une requête à l'API NWS avec gestion des erreurs."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Formate une alerte météo en texte lisible."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@mcp.tool()  # Déclare une fonction comme outil MCP
async def get_alerts(state: str) -> str:
    """Récupère les alertes météo pour un état américain.

    Args:
        state: Code à deux lettres de l'état US (ex: CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()  # Déclare une fonction comme outil MCP
async def get_forecast(latitude: float, longitude: float) -> str:
    """Récupère les prévisions météo pour une localisation.

    Args:
        latitude: Latitude de la localisation
        longitude: Longitude de la localisation
    """
    # D'abord obtenir le point de la grille de prévision
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Obtient l'URL des prévisions depuis la réponse des points
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Formate les périodes en prévisions lisibles
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Montre seulement les 5 prochaines périodes
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


if __name__ == "__main__":
    # Initialise et démarre le serveur
    mcp.run(transport='stdio')