from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class OperationalDataProvider(ABC):
    """
    Abstract interface defining the boundary for future operational data feeds
    (e.g., Authorized Indian Railways BDMS, TMS, or COA feeds when formally integrated).

    DO NOT implement fake or mock adapters claiming to be BDMS/TMS/COA.
    """

    @abstractmethod
    async def get_maintenance_requests(
        self,
        division: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Retrieve maintenance possession requisitions from operational authority."""
        raise NotImplementedError

    @abstractmethod
    async def get_block_requests(
        self,
        corridor_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Retrieve traffic and power block demands across departments."""
        raise NotImplementedError

    @abstractmethod
    async def get_block_history(
        self,
        section_id: str,
        lookback_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical granted and executed blocks for performance tracking."""
        raise NotImplementedError

    @abstractmethod
    async def get_operational_train_movements(
        self,
        section_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> List[Dict[str, Any]]:
        """Retrieve real-time or dispatch telemetry for train movements in the section."""
        raise NotImplementedError
