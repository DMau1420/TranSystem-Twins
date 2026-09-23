from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class Geometry(BaseModel):
    type: str = "Point"
    coordinates: List[float] 

class GeoJson(BaseModel):
    type: str = "Feature"
    properties: Dict[str, Any] = {}
    geometry: Geometry

class PointItem(BaseModel):
    id: str
    lat: float
    lng: float
    geoJson: GeoJson
    street: Optional[str] = None
    displayName: Optional[str] = None

class PointsPayload(BaseModel):
    points: List[PointItem]