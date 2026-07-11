from pydantic import BaseModel

class InfoResponse(BaseModel):
    app_name: str
    version: str
    environment: str
