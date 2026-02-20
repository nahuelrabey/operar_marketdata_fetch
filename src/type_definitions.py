from typing import List, Dict, Any, Optional, TypedDict, Union

# --- Type Definitions (from modules_design.md) ---

class ContractData(TypedDict):
    symbol: str
    underlying_symbol: str
    type: str
    expiration_date: str
    strike: float
    description: str

class PriceData(TypedDict):
    contract_symbol: str
    price: float
    broker_timestamp: Optional[str]
    system_timestamp: str
    volume: int

class LatestPriceData(TypedDict):
    symbol: str
    market_id: Optional[str]
    last_price: Optional[float]
    bid_price: Optional[float]
    offer_price: Optional[float]
    timestamp: Optional[str]

class OperationData(TypedDict):
    contract_symbol: str
    operation_type: str
    quantity: int
    price: float
    operation_date: str

class PositionComposition(TypedDict):
    symbol: str
    net_quantity: int

class PositionDetails(TypedDict):
    composition: List[PositionComposition]
    current_pnl: float
    pnl_curve: Dict[str, Any] # values are np.ndarray

class PositionData(TypedDict):
    id: int
    name: str
    description: str
    status: str
    created_at: str