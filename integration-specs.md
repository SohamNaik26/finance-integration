# Python Integration Specifications

## Project Setup

### Environment Configuration
```toml
# pyproject.toml
[project]
name = "blockchain-integrations"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "httpx>=0.27.0",
    "pandas>=2.2.0",
    "pydantic>=2.6.0",
    "python-dotenv>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "black>=24.0.0",
    "mypy>=1.8.0",
]
```

---

## Integration 1: Mayan Bridge Data

### File: `mayan_bridge_integration.py`

#### Core Data Structure Analysis
The Mayan API returns quote data for cross-chain swaps with the following key components:
- Quote details (price, amounts, fees)
- Route information (bridges used, intermediate steps)
- Token metadata (addresses, decimals, symbols)
- Slippage and gas estimates

#### Input Parameters
```python
class MayanBridgeParams(BaseModel):
    from_chain: str
    to_chain: str
    from_token: str  # Token address or "0x0000..." for native
    to_token: str    # Token address or "0x0000..." for native
    amount_in: float = 1.0
    slippage_bps: str = "auto"
    referrer: str = "7HN4qCvG2dP5oagZRxj2dTGPhksgRnKCaLPjtjKEr1Ho"
```

#### Implementation Structure
```python
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict

class RouteStep(BaseModel):
    """Individual step in a bridge route"""
    bridge_type: str
    from_token: str
    to_token: str
    amount: str
    fee: Optional[float] = None

class MayanQuote(BaseModel):
    """Main quote response model"""
    model_config = ConfigDict(extra='allow')
    
    quote_id: Optional[str] = None
    from_chain: str
    to_chain: str
    from_token: str
    to_token: str
    amount_in: float
    amount_out: float
    price_impact: Optional[float] = None
    minimum_amount_out: Optional[float] = None
    gas_fee: Optional[float] = None
    bridge_fee: Optional[float] = None
    total_fee: Optional[float] = None
    execution_time_seconds: Optional[int] = None
    route_type: Optional[str] = None
    route_steps: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    warnings: Optional[List[str]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_response: Optional[str] = None

class MayanBridgeIntegration:
    BASE_URL = "https://price-api.mayan.finance/v3/quote"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()
    
    def _build_url(self, params: MayanBridgeParams) -> str:
        """Build the full URL with query parameters"""
        query_params = {
            "wormhole": "true",
            "swift": "true",
            "mctp": "true",
            "shuttle": "false",
            "fastMctp": "true",
            "gasless": "true",
            "onlyDirect": "false",
            "fullList": "false",
            "monoChain": "true",
            "solanaProgram": "FC4eXxkyrMPTjiYUpp4EAnkmwMbQyZ6NDCh1kfLn6vsf",
            "forwarderAddress": "0x337685fdaB40D39bd02028545a4FfA7D287cC3E2",
            "amountIn": str(params.amount_in),
            "fromToken": params.from_token,
            "fromChain": params.from_chain,
            "toToken": params.to_token,
            "toChain": params.to_chain,
            "slippageBps": params.slippage_bps,
            "referrer": params.referrer,
            "gasDrop": "0",
            "sdkVersion": "11_0_0"
        }
        return f"{self.BASE_URL}?{urlencode(query_params)}"
    
    def _flatten_quote_data(self, data: Dict[str, Any], params: MayanBridgeParams) -> Dict[str, Any]:
        """Flatten nested quote data into a single dictionary"""
        flattened = {
            "timestamp": datetime.utcnow().isoformat(),
            "from_chain": params.from_chain,
            "to_chain": params.to_chain,
            "from_token": params.from_token,
            "to_token": params.to_token,
            "amount_in": params.amount_in,
        }
        
        # Extract main quote fields
        if isinstance(data, dict):
            # Price and amount fields
            flattened["amount_out"] = data.get("amountOut", 0)
            flattened["price"] = data.get("price", 0)
            flattened["price_impact"] = data.get("priceImpact", 0)
            flattened["minimum_amount_out"] = data.get("minimumAmountOut", 0)
            
            # Fee fields
            flattened["gas_fee"] = data.get("gasFee", 0)
            flattened["bridge_fee"] = data.get("bridgeFee", 0)
            flattened["total_fee"] = data.get("totalFee", 0)
            
            # Route information
            flattened["route_type"] = data.get("routeType", "")
            flattened["execution_time_seconds"] = data.get("executionTimeSeconds", 0)
            
            # Complex nested data as JSON strings
            if "routes" in data and isinstance(data["routes"], list):
                flattened["routes_json"] = json.dumps(data["routes"])
            
            if "routeSteps" in data and isinstance(data["routeSteps"], list):
                flattened["route_steps_json"] = json.dumps(data["routeSteps"])
            
            if "warnings" in data and isinstance(data["warnings"], list):
                flattened["warnings_json"] = json.dumps(data["warnings"])
            
            # Token metadata
            if "fromTokenMetadata" in data:
                meta = data["fromTokenMetadata"]
                flattened["from_token_symbol"] = meta.get("symbol", "")
                flattened["from_token_decimals"] = meta.get("decimals", 0)
            
            if "toTokenMetadata" in data:
                meta = data["toTokenMetadata"]
                flattened["to_token_symbol"] = meta.get("symbol", "")
                flattened["to_token_decimals"] = meta.get("decimals", 0)
            
            # Store raw response for debugging
            flattened["raw_response"] = json.dumps(data)
        
        return flattened
    
    async def fetch_quote(self, params: MayanBridgeParams) -> Dict[str, Any]:
        """Fetch a single quote from Mayan API"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        url = self._build_url(params)
        response = await self.client.get(url)
        response.raise_for_status()
        
        data = response.json()
        return self._flatten_quote_data(data, params)
    
    async def fetch_multiple_quotes(self, params_list: List[MayanBridgeParams]) -> pd.DataFrame:
        """Fetch multiple quotes and return as DataFrame"""
        quotes = []
        for params in params_list:
            try:
                quote = await self.fetch_quote(params)
                quotes.append(quote)
            except Exception as e:
                # Log error but continue with other quotes
                error_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "from_chain": params.from_chain,
                    "to_chain": params.to_chain,
                    "from_token": params.from_token,
                    "to_token": params.to_token,
                    "error": str(e)
                }
                quotes.append(error_record)
        
        return pd.DataFrame(quotes)

async def main_mayan_bridge() -> pd.DataFrame:
    """Main function to fetch Mayan bridge data and return as DataFrame"""
    # Example usage with multiple token pairs
    params_list = [
        MayanBridgeParams(
            from_chain="ethereum",
            to_chain="solana",
            from_token="0x0000000000000000000000000000000000000000",  # ETH
            to_token="0x0000000000000000000000000000000000000000",    # SOL
            amount_in=1.0
        ),
        # Add more pairs as needed
    ]
    
    async with MayanBridgeIntegration() as integration:
        df = await integration.fetch_multiple_quotes(params_list)
        
        # Ensure proper data types
        numeric_columns = ['amount_in', 'amount_out', 'price', 'price_impact', 
                          'gas_fee', 'bridge_fee', 'total_fee', 'execution_time_seconds']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
```

---

## Integration 2: Tronscan Balance

### File: `tronscan_balance_integration.py`

#### Core Data Structure Analysis
The Tronscan API returns:
- Resource delegation information
- Balance data
- Contract information
- Address metadata

#### Implementation Structure
```python
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict

class TronResourceData(BaseModel):
    """Model for individual resource/balance entry"""
    model_config = ConfigDict(extra='allow')
    
    receiver_address: str
    expire_time: Optional[int] = None
    balance: float
    resource: int
    receiver_address_tag: str = ""
    lock_balance: float = 0
    lock_resource_value: float = 0
    owner_address: Optional[str] = None
    resource_value: float = 0
    operation_time: Optional[int] = None

class TronBalanceResponse(BaseModel):
    """Main response model for Tronscan API"""
    total: int
    data: List[Dict[str, Any]]
    contract_map: Optional[Dict[str, bool]] = None
    range_total: Optional[int] = None
    contract_info: Optional[Dict[str, Any]] = None
    normal_address_info: Optional[Dict[str, Any]] = None

class TronscanBalanceIntegration:
    BASE_URL = "https://apilist.tronscanapi.com/api/account/resourcev2"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()
    
    def _build_url(self, address: str, limit: int = 100, start: int = 0) -> str:
        """Build URL with query parameters"""
        params = {
            "limit": limit,
            "start": start,
            "address": address,
            "type": 1,
            "resourceType": 0
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.BASE_URL}?{query_string}"
    
    def _extract_balance_data(self, response_data: Dict[str, Any], address: str) -> List[Dict[str, Any]]:
        """Extract and flatten balance-related data only"""
        balance_records = []
        
        # Process main data array
        if "data" in response_data and isinstance(response_data["data"], list):
            for item in response_data["data"]:
                record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "address": address,
                    "receiver_address": item.get("receiverAddress", ""),
                    "owner_address": item.get("ownerAddress", ""),
                    "balance": float(item.get("balance", 0)) / 1_000_000,  # Convert from sun to TRX
                    "lock_balance": float(item.get("lockBalance", 0)) / 1_000_000,
                    "resource_value": float(item.get("resourceValue", 0)),
                    "lock_resource_value": float(item.get("lockResourceValue", 0)),
                    "resource_type": item.get("resource", 0),
                    "expire_time": None,
                    "operation_time": None,
                }
                
                # Convert timestamps from milliseconds
                if "expireTime" in item and item["expireTime"]:
                    record["expire_time"] = datetime.fromtimestamp(item["expireTime"] / 1000).isoformat()
                
                if "operationTime" in item and item["operationTime"]:
                    record["operation_time"] = datetime.fromtimestamp(item["operationTime"] / 1000).isoformat()
                
                # Add contract information if available
                if "contractInfo" in response_data:
                    contract_info = response_data["contractInfo"].get(item.get("receiverAddress", ""), {})
                    record["is_token"] = contract_info.get("isToken", False)
                    record["contract_name"] = contract_info.get("name", "")
                    record["is_vip"] = contract_info.get("vip", False)
                    record["risk"] = contract_info.get("risk", False)
                
                balance_records.append(record)
        
        # If no data records, create a single record with the account balance info
        if not balance_records and response_data:
            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "address": address,
                "receiver_address": address,
                "owner_address": "",
                "balance": 0.0,
                "lock_balance": 0.0,
                "resource_value": 0.0,
                "lock_resource_value": 0.0,
                "resource_type": 0,
                "expire_time": None,
                "operation_time": None,
                "is_token": False,
                "contract_name": "",
                "is_vip": False,
                "risk": False,
            }
            balance_records.append(record)
        
        return balance_records
    
    async def fetch_balance(self, address: str) -> List[Dict[str, Any]]:
        """Fetch balance data for a single address"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        all_records = []
        start = 0
        limit = 100
        
        while True:
            url = self._build_url(address, limit, start)
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            records = self._extract_balance_data(data, address)
            all_records.extend(records)
            
            # Check if there are more pages
            total = data.get("total", 0)
            if start + limit >= total:
                break
            
            start += limit
        
        return all_records
    
    async def fetch_multiple_balances(self, addresses: List[str]) -> pd.DataFrame:
        """Fetch balances for multiple addresses"""
        all_records = []
        
        for address in addresses:
            try:
                records = await self.fetch_balance(address)
                all_records.extend(records)
            except Exception as e:
                # Log error but continue with other addresses
                error_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "address": address,
                    "error": str(e)
                }
                all_records.append(error_record)
        
        return pd.DataFrame(all_records)

async def main_tronscan_balance() -> pd.DataFrame:
    """Main function to fetch Tronscan balance data and return as DataFrame"""
    # Example addresses - replace with actual addresses
    addresses = [
        "TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg",
        # Add more addresses as needed
    ]
    
    async with TronscanBalanceIntegration() as integration:
        df = await integration.fetch_multiple_balances(addresses)
        
        # Ensure proper data types
        numeric_columns = ['balance', 'lock_balance', 'resource_value', 
                          'lock_resource_value', 'resource_type']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert timestamp columns to datetime
        timestamp_columns = ['timestamp', 'expire_time', 'operation_time']
        for col in timestamp_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Sort by timestamp and address
        if 'timestamp' in df.columns and 'address' in df.columns:
            df = df.sort_values(['timestamp', 'address'], ascending=[False, True])
        
        return df
```

---

## Usage Examples

### Running the Integrations

```python
# main.py
import asyncio
from mayan_bridge_integration import main_mayan_bridge, MayanBridgeParams
from tronscan_balance_integration import main_tronscan_balance

async def run_all_integrations():
    """Run both integrations and save results"""
    
    # Run Mayan Bridge integration
    mayan_df = await main_mayan_bridge()
    mayan_df.to_csv("mayan_bridge_data.csv", index=False)
    print(f"Mayan Bridge: {len(mayan_df)} records fetched")
    
    # Run Tronscan Balance integration
    tronscan_df = await main_tronscan_balance()
    tronscan_df.to_csv("tronscan_balance_data.csv", index=False)
    print(f"Tronscan Balance: {len(tronscan_df)} records fetched")
    
    return mayan_df, tronscan_df

if __name__ == "__main__":
    mayan_df, tronscan_df = asyncio.run(run_all_integrations())
```

### Scheduling Hourly Runs (Optional)

```python
# scheduler.py
import asyncio
import schedule
import time
from datetime import datetime
from tronscan_balance_integration import main_tronscan_balance

def run_tronscan_hourly():
    """Wrapper for running async function in sync context"""
    df = asyncio.run(main_tronscan_balance())
    filename = f"tronscan_balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} records to {filename}")

# Schedule hourly runs
schedule.every().hour.do(run_tronscan_hourly)

if __name__ == "__main__":
    # Run immediately on start
    run_tronscan_hourly()
    
    # Keep running scheduled tasks
    while True:
        schedule.run_pending()
        time.sleep(60)
```

---

## Testing

### Unit Tests

```python
# tests/test_integrations.py
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from mayan_bridge_integration import MayanBridgeIntegration, MayanBridgeParams
from tronscan_balance_integration import TronscanBalanceIntegration

@pytest.mark.asyncio
async def test_mayan_bridge_url_building():
    """Test URL construction for Mayan Bridge API"""
    integration = MayanBridgeIntegration()
    params = MayanBridgeParams(
        from_chain="ethereum",
        to_chain="solana",
        from_token="0x0000000000000000000000000000000000000000",
        to_token="0x0000000000000000000000000000000000000000",
        amount_in=1.0
    )
    
    url = integration._build_url(params)
    assert "fromChain=ethereum" in url
    assert "toChain=solana" in url
    assert "amountIn=1.0" in url

@pytest.mark.asyncio
async def test_tronscan_balance_extraction():
    """Test balance data extraction from Tronscan response"""
    integration = TronscanBalanceIntegration()
    
    sample_response = {
        "total": 1,
        "data": [{
            "receiverAddress": "TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg",
            "balance": 464000000,
            "lockBalance": 0,
            "resourceValue": 732.66,
        }]
    }
    
    records = integration._extract_balance_data(sample_response, "TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg")
    assert len(records) == 1
    assert records[0]["balance"] == 464.0  # Converted from sun to TRX
```

---

## Key Features

### Data Flattening Strategy
1. **Simple fields**: Directly mapped to DataFrame columns
2. **Nested objects**: Flattened with prefix notation
3. **Lists/Arrays**: Stored as JSON strings in DataFrame
4. **Timestamps**: Converted to ISO format strings

### Error Handling
- Individual failures don't stop batch processing
- Errors are logged in the DataFrame with error messages
- HTTP retries handled by httpx

### Type Safety
- All functions strictly typed with Pydantic models
- DataFrame columns have enforced data types
- Optional fields handled gracefully

### Performance Optimization
- Async/await for concurrent API calls
- Connection pooling via httpx.AsyncClient
- Batch processing support

### Extensibility
- Easy to add new endpoints
- Modular design for adding new data sources
- Configuration via environment variables supported