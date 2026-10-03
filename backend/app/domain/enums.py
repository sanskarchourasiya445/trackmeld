from enum import Enum


class DataClass(str, Enum):
    """Canonical data classification ensuring separation of real and artificial facts."""
    REAL = "REAL"
    DERIVED = "DERIVED"
    SYNTHETIC = "SYNTHETIC"
    ASSUMED = "ASSUMED"


class BlockType(str, Enum):
    """Types of maintenance blocks requested or granted."""
    TRAFFIC = "TRAFFIC"
    POWER = "POWER"
    TRAFFIC_AND_POWER = "TRAFFIC_AND_POWER"


class WorkDepartment(str, Enum):
    """Railway departments executing track/overhead/signalling maintenance."""
    ENGINEERING = "ENGINEERING"
    ELECTRICAL = "ELECTRICAL"
    S_AND_T = "S_AND_T"
    OPERATING = "OPERATING"
    OTHER = "OTHER"


class TaskStatus(str, Enum):
    """Lifecycle status of a maintenance work requisition."""
    REQUESTED = "REQUESTED"
    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    POSTPONED = "POSTPONED"


class StationType(str, Enum):
    """Operational hierarchy of a railway station."""
    MAJOR_TERMINAL = "MAJOR_TERMINAL"
    TERMINAL = "TERMINAL"
    JUNCTION = "JUNCTION"
    WAY_STATION = "WAY_STATION"
    UNKNOWN = "UNKNOWN"


class MovementType(str, Enum):
    """Nature of train movement at a station or section endpoint."""
    SCHEDULED_ORIGIN = "SCHEDULED_ORIGIN"
    SCHEDULED_INTERMEDIATE_STOP = "SCHEDULED_INTERMEDIATE_STOP"
    SCHEDULED_DESTINATION = "SCHEDULED_DESTINATION"
    PASS_THROUGH = "PASS_THROUGH"


class MovementBasis(str, Enum):
    """Underlying basis of the recorded movement time."""
    SCHEDULED_TIMETABLE = "SCHEDULED_TIMETABLE"
    OPERATIONAL_LOG = "OPERATIONAL_LOG"
    SYNTHETIC_PATTERN = "SYNTHETIC_PATTERN"


class RuleClass(str, Enum):
    """Authority status of a domain or scheduling rule."""
    VERIFIED_SOURCE = "VERIFIED_SOURCE"
    ASSUMPTION = "ASSUMPTION"
    DEMO_ONLY = "DEMO_ONLY"
    UNVERIFIED = "UNVERIFIED"



class SourceClass(str, Enum):
    """Hierarchical source authority classes."""
    OFFICIAL_MINISTRY = "OFFICIAL_MINISTRY"
    OFFICIAL_RAILWAY_BOARD = "OFFICIAL_RAILWAY_BOARD"
    OFFICIAL_CRIS = "OFFICIAL_CRIS"
    OFFICIAL_RDSO = "OFFICIAL_RDSO"
    OFFICIAL_ZONAL_RAILWAY = "OFFICIAL_ZONAL_RAILWAY"
    OFFICIAL_DIVISIONAL_RAILWAY = "OFFICIAL_DIVISIONAL_RAILWAY"
    OFFICIAL_GOVERNMENT = "OFFICIAL_GOVERNMENT"
    SECONDARY_REFERENCE = "SECONDARY_REFERENCE"
    UNVERIFIED = "UNVERIFIED"


class TaskType(str, Enum):
    """Operational category of maintenance activity."""
    TRACK_MAINTENANCE = "TRACK_MAINTENANCE"
    TRACK_MACHINE_WORK = "TRACK_MACHINE_WORK"
    OHE_MAINTENANCE = "OHE_MAINTENANCE"
    SIGNAL_MAINTENANCE = "SIGNAL_MAINTENANCE"
    S_AND_T_WORK = "S_AND_T_WORK"
    BRIDGE_WORK = "BRIDGE_WORK"
    CIVIL_WORK = "CIVIL_WORK"
    INSPECTION = "INSPECTION"
    OTHER = "OTHER"


class TaskPriority(str, Enum):
    """Operational urgency level of maintenance work."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class WorkOrderStatus(str, Enum):
    """Lifecycle status of a maintenance work order grouping tasks."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DEFERRED = "DEFERRED"


class ResourceType(str, Enum):
    """Functional class of maintenance resources."""
    CREW = "CREW"
    TRACK_MACHINE = "TRACK_MACHINE"
    OHE_EQUIPMENT = "OHE_EQUIPMENT"
    S_AND_T_EQUIPMENT = "S_AND_T_EQUIPMENT"
    VEHICLE = "VEHICLE"
    SPECIAL_EQUIPMENT = "SPECIAL_EQUIPMENT"
    OTHER = "OTHER"


class AvailabilityStatus(str, Enum):
    """Availability state of a resource in a given interval."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    MAINTENANCE = "MAINTENANCE"
    RESERVED = "RESERVED"


class DependencyType(str, Enum):
    """Temporal or logical sequencing relationship between tasks."""
    FINISH_TO_START = "FINISH_TO_START"


class AdjacentTrackImpact(str, Enum):
    """Provisional classification of maintenance impact on adjacent running line(s).
    
    NOTE: This is a provisional TrackMeld domain abstraction for decision support,
    not a claim of complete or official railway safety-rule coverage.
    """
    NONE = "NONE"
    CAUTION_ORDER = "CAUTION_ORDER"
    FULL_TRAFFIC_BLOCK = "FULL_TRAFFIC_BLOCK"


class TraversalResolutionStatus(str, Enum):
    """Resolution status of train traversal expansion over physical block sections.
    
    - DIRECT_SECTION: Train pass directly connects adjacent stations of a single block section.
    - EXPANDED_ROUTE: Train pass traverses multiple intermediate block sections via topological shortest path.
    - UNRESOLVED: Topological path between endpoints could not be resolved or is disconnected.
    """
    DIRECT_SECTION = "DIRECT_SECTION"
    EXPANDED_ROUTE = "EXPANDED_ROUTE"
    UNRESOLVED = "UNRESOLVED"

