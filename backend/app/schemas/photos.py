from pydantic import BaseModel, ConfigDict, HttpUrl


class FoodPhotoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_url: HttpUrl
    photographer_name: str
    photographer_profile_url: HttpUrl
    attribution_url: HttpUrl
