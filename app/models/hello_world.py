from app.models.base_model import BaseModel


class HelloWorld(BaseModel):
    __abstract__ = True

    hello: bool = True
    world: str = "earth"

