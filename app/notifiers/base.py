from abc import ABC, abstractmethod
from app.domain.models import MediaInfo

class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, media: MediaInfo):
        pass
