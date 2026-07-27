from pydantic import BaseModel, Field


class GuessIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PublicConfig(BaseModel):
    mapillary_client_token: str
    map_style_url: str
    map_attribution: str
    rounds_per_game: int = 5
