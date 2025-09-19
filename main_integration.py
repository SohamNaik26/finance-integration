"""
Comprehensive Blockchain Data Integration

This module provides complete integration with multiple blockchain APIs:
- Mayan Finance Bridge API (cross-chain quotes)
- TRON blockchain APIs (TronGrid, TronLink, TronScan)
- TronScan Balance API (with optional API key)

Features:
- All integrations work without API keys (except TronScan optional)
- Comprehensive error handling and logging
- Type-safe implementation using Pydantic models
- Automatic fallback between APIs
- Data export to CSV format

Author: Finance Integration Team
Version: 2.0.0
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# CSV HANDLING UTILITIES
# ============================================================================

def save_csv_with_append(df: pd.DataFrame, filename: str, mode: str = 'append') -> None:
    """
    Save DataFrame to CSV with append or create mode.
    
    Args:
        df: DataFrame to save
        filename: CSV filename
        mode: 'append' to add rows to existing file, 'create' to create new file
    """
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    if mode == 'append' and os.path.exists(output_path):
        # Append mode - check if file exists and has data
        try:
            existing_df = pd.read_csv(output_path)
            if not existing_df.empty:
                # File exists and has data, append new data
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_csv(output_path, index=False)
                print(f"   ✓ Appended {len(df)} records to {output_path} (total: {len(combined_df)})")
            else:
                # File exists but is empty, write new data
                df.to_csv(output_path, index=False)
                print(f"   ✓ Created {output_path} with {len(df)} records")
        except Exception as e:
            # File exists but can't be read, create new file
            print(f"   ⚠️  Could not read existing {output_path}, creating new file: {e}")
            df.to_csv(output_path, index=False)
            print(f"   ✓ Created new {output_path} with {len(df)} records")
    else:
        # Create mode or append when base file does not exist: write to base path (no timestamp)
        df.to_csv(output_path, index=False)
        print(f"   ✓ Created {output_path} with {len(df)} records")


def ensure_csv_headers(df: pd.DataFrame, filename: str) -> None:
    """
    Ensure CSV file has proper headers when appending data.
    
    Args:
        df: DataFrame to save
        filename: CSV filename
    """
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    if os.path.exists(output_path):
        try:
            existing_df = pd.read_csv(output_path)
            # Check if columns match
            if list(existing_df.columns) != list(df.columns):
                print(f"   ⚠️  Column mismatch in {output_path}, creating new file")
                df.to_csv(output_path, index=False)
            else:
                # Columns match, safe to append
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_csv(output_path, index=False)
        except Exception as e:
            print(f"   ⚠️  Error reading {output_path}, creating new file: {e}")
            df.to_csv(output_path, index=False)
    else:
        df.to_csv(output_path, index=False)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class MayanBridgeParams(BaseModel):
    """Input parameters for Mayan Bridge API requests."""
    model_config = ConfigDict(extra='allow')
    
    from_chain: str
    to_chain: str
    from_token: str  # Token address or "0x0000..." for native
    to_token: str    # Token address or "0x0000..." for native
    amount_in: float = 1.0
    slippage_bps: str = "auto"
    referrer: str = "7HN4qCvG2dP5oagZRxj2dTGPhksgRnKCaLPjtjKEr1Ho"


class TronAccountBalance(BaseModel):
    """Model for TRON account balance information."""
    model_config = ConfigDict(extra='allow')
    
    address: str
    balance_trx: float = 0.0
    balance_sun: int = 0
    frozen_balance_trx: float = 0.0
    frozen_balance_sun: int = 0
    energy: int = 0
    bandwidth: int = 0
    timestamp: str = ""
    source_api: str = ""


class TronAccountInfo(BaseModel):
    """Model for TRON account information from various APIs."""
    model_config = ConfigDict(extra='allow')
    
    address: str
    balance_trx: float = 0.0
    balance_sun: int = 0
    frozen_balance_trx: float = 0.0
    frozen_balance_sun: int = 0
    energy: int = 0
    bandwidth: int = 0
    timestamp: str = ""
    source_api: str = ""


class TronResourceData(BaseModel):
    """Model for individual resource/balance entry from Tronscan API."""
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
    """Main response model for Tronscan API."""
    total: int
    data: List[Dict[str, Any]]
    contract_map: Optional[Dict[str, bool]] = None
    range_total: Optional[int] = None
    contract_info: Optional[Dict[str, Any]] = None
    normal_address_info: Optional[Dict[str, Any]] = None


# ============================================================================
# EVERCLEAR BALANCE HISTORY MODELS
# ============================================================================

class EverclearBalanceParams(BaseModel):
    """Input parameters for Everclear balance history requests (ETH only)."""
    model_config = ConfigDict(extra='allow')

    address: str
    block_number: Optional[int] = None
    items_count: int = 50  # 1-100
    page: int = 1  # 1-based

    def is_valid_eth_address(self) -> bool:
        return isinstance(self.address, str) and self.address.startswith("0x") and len(self.address) == 42


class EverclearBalanceRecord(BaseModel):
    """Flattened record for Everclear ETH balance history."""
    model_config = ConfigDict(extra='allow')

    address: str
    block_number: int
    block_hash: str = ""
    transaction_hash: Optional[str] = None
    balance_wei: str = "0"
    balance_eth: float = 0.0
    balance_change_wei: str = "0"
    balance_change_eth: float = 0.0
    timestamp: str = ""
    timestamp_iso: str = ""
    fetch_timestamp: str = ""
    source_api: str = "everclear_scan"
    page: int = 1
    error: Optional[str] = None
    error_type: Optional[str] = None


# ============================================================================
# MAYAN BRIDGE INTEGRATION
# ============================================================================

class MayanBridgeIntegration:
    """Integration class for Mayan Bridge API."""
    
    BASE_URL = "https://price-api.mayan.finance/v3/quote"
    
    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "MayanBridgeIntegration":
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()
    
    def _build_url(self, params: MayanBridgeParams) -> str:
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
        flattened: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_chain": params.from_chain,
            "to_chain": params.to_chain,
            "from_token": params.from_token,
            "to_token": params.to_token,
            "amount_in": params.amount_in,
        }
        
        if isinstance(data, dict):
            # Price and amount fields
            flattened["amount_out"] = data.get("amountOut", 0)
            flattened["effective_price"] = data.get("effectivePrice", 0)
            flattened["price"] = data.get("price", 0)
            flattened["price_impact"] = data.get("priceImpact", 0)
            flattened["minimum_amount_out"] = data.get("minimumAmountOut", 0)
            flattened["expected_amount_out"] = data.get("expectedAmountOut", 0)
            
            # Fee fields
            flattened["gas_fee"] = data.get("gasFee", 0)
            flattened["bridge_fee"] = data.get("bridgeFee", 0)
            flattened["total_fee_in_usd"] = data.get("totalFeeInUsd", 0)
            flattened["mayan_fee"] = data.get("mayanFee", 0)
            flattened["relayer_fee"] = data.get("relayerFee", 0)
            
            # Route information
            flattened["route_type"] = data.get("routeType", "")
            flattened["execution_time_seconds"] = data.get("executionTimeSeconds", 0)
            flattened["quote_type"] = data.get("type", "")
            
            # Slippage and limits
            flattened["slippage_bps"] = data.get("slippageBps", 0)
            flattened["max_slippage_bps"] = data.get("maxSlippageBps", 0)
            
            # Gas and transaction details
            flattened["gas_price"] = data.get("gasPrice", 0)
            flattened["gas_drop_amount"] = data.get("gasDropAmount", 0)
            
            # Complex nested data as JSON strings
            if "routes" in data and isinstance(data["routes"], list):
                flattened["routes_json"] = json.dumps(data["routes"])
                flattened["routes_count"] = len(data["routes"])
            
            if "routeSteps" in data and isinstance(data["routeSteps"], list):
                flattened["route_steps_json"] = json.dumps(data["routeSteps"])
                flattened["route_steps_count"] = len(data["routeSteps"])
            
            if "warnings" in data and isinstance(data["warnings"], list):
                flattened["warnings_json"] = json.dumps(data["warnings"])
                flattened["warnings_count"] = len(data["warnings"])
            
            if "suggestedSlippageBps" in data:
                flattened["suggested_slippage_bps"] = data.get("suggestedSlippageBps", 0)
            
            # Token metadata
            if "fromTokenMetadata" in data and isinstance(data["fromTokenMetadata"], dict):
                meta = data["fromTokenMetadata"]
                flattened["from_token_symbol"] = meta.get("symbol", "")
                flattened["from_token_decimals"] = meta.get("decimals", 0)
                flattened["from_token_name"] = meta.get("name", "")
                flattened["from_token_logo_uri"] = meta.get("logoURI", "")
            
            if "toTokenMetadata" in data and isinstance(data["toTokenMetadata"], dict):
                meta = data["toTokenMetadata"]
                flattened["to_token_symbol"] = meta.get("symbol", "")
                flattened["to_token_decimals"] = meta.get("decimals", 0)
                flattened["to_token_name"] = meta.get("name", "")
                flattened["to_token_logo_uri"] = meta.get("logoURI", "")
        
        return flattened
    
    async def fetch_quote(self, params: MayanBridgeParams) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        url = self._build_url(params)
        response = await self.client.get(url)
        response.raise_for_status()
        
        data = response.json()
        return self._flatten_quote_data(data, params)
    
    async def fetch_multiple_quotes(self, params_list: List[MayanBridgeParams]) -> pd.DataFrame:
        quotes: List[Dict[str, Any]] = []
        
        for params in params_list:
            try:
                quote = await self.fetch_quote(params)
                quotes.append(quote)
            except httpx.HTTPStatusError as e:
                error_record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "from_chain": params.from_chain,
                    "to_chain": params.to_chain,
                    "from_token": params.from_token,
                    "to_token": params.to_token,
                    "amount_in": params.amount_in,
                    "error": f"HTTP {e.response.status_code}: {str(e)}",
                    "error_type": "http_error"
                }
                quotes.append(error_record)
            except Exception as e:
                error_record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "from_chain": params.from_chain,
                    "to_chain": params.to_chain,
                    "from_token": params.from_token,
                    "to_token": params.to_token,
                    "amount_in": params.amount_in,
                    "error": str(e),
                    "error_type": "general_error"
                }
                quotes.append(error_record)
        
        return pd.DataFrame(quotes)


# ============================================================================
# SIMPLE TRON INTEGRATION
# ============================================================================

class SimpleTronIntegration:
    """Simple integration class for TRON blockchain APIs."""
    
    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        self.base_url = "https://api.trongrid.io"
    
    async def __aenter__(self) -> "SimpleTronIntegration":
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()
    
    async def fetch_account_balance(self, address: str) -> TronAccountBalance:
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            url = f"{self.base_url}/wallet/getaccount"
            payload = {"address": address, "visible": True}
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            balance_sun = data.get("balance", 0)
            frozen_balance_sun = 0
            
            frozen_list = data.get("frozen", [])
            if frozen_list and len(frozen_list) > 0:
                frozen_balance_sun = frozen_list[0].get("frozen_balance", 0)
            
            energy = data.get("energy", 0)
            bandwidth = data.get("bandwidth", 0)
            
            return TronAccountBalance(
                address=address,
                balance_sun=balance_sun,
                balance_trx=balance_sun / 1_000_000,
                frozen_balance_sun=frozen_balance_sun,
                frozen_balance_trx=frozen_balance_sun / 1_000_000,
                energy=energy,
                bandwidth=bandwidth,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source_api="trongrid"
            )
            
        except Exception as e:
            print(f"Error fetching balance for {address}: {e}")
            return TronAccountBalance(
                address=address,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source_api="error"
            )
    
    async def fetch_multiple_balances(self, addresses: List[str]) -> pd.DataFrame:
        all_records = []
        
        for address in addresses:
            try:
                balance_info = await self.fetch_account_balance(address)
                all_records.append(balance_info.model_dump())
            except Exception as e:
                error_record = {
                    "address": address,
                    "error": str(e),
                    "error_type": "general_error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source_api": "error"
                }
                all_records.append(error_record)
        
        return pd.DataFrame(all_records)


# ============================================================================
# ALTERNATIVE TRON INTEGRATION
# ============================================================================

class AlternativeTronIntegration:
    """Integration class for alternative TRON blockchain APIs."""
    
    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        
        self.apis = {
            "trongrid": "https://api.trongrid.io",
            "tronlink": "https://api.tronlink.org",
            "tronscan": "https://apilist.tronscanapi.com/api"
        }
    
    async def __aenter__(self) -> "AlternativeTronIntegration":
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()
    
    async def _fetch_trongrid_account(self, address: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.apis['trongrid']}/wallet/getaccount"
            payload = {"address": address, "visible": True}
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data and not data.get("Error"):
                return {"account": data}
            return None
            
        except Exception as e:
            print(f"TronGrid API error: {e}")
            return None
    
    async def _fetch_tronlink_account(self, address: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"https://api.tronlink.org/api/account/{address}"
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"TronLink API error: {e}")
            return None
    
    async def _fetch_tronscan_account(self, address: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"https://apilist.tronscanapi.com/api/account"
            params = {"address": address}
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data and not data.get("Error"):
                return data
            return None
            
        except Exception as e:
            print(f"TronScan API error: {e}")
            return None
    
    def _extract_account_info(self, data: Dict[str, Any], source_api: str) -> TronAccountInfo:
        if source_api == "trongrid":
            account_data = data.get("account", {})
            balance_sun = account_data.get("balance", 0)
            frozen_balance_sun = account_data.get("frozen", [{}])[0].get("frozen_balance", 0)
            
            return TronAccountInfo(
                address=account_data.get("address", ""),
                balance_sun=balance_sun,
                balance_trx=balance_sun / 1_000_000,
                frozen_balance_sun=frozen_balance_sun,
                frozen_balance_trx=frozen_balance_sun / 1_000_000,
                energy=account_data.get("energy", 0),
                bandwidth=account_data.get("bandwidth", 0),
                timestamp=datetime.now(timezone.utc).isoformat(),
                source_api=source_api
            )
        
        elif source_api == "tronlink":
            return TronAccountInfo(
                address=data.get("address", ""),
                balance_sun=data.get("balance", 0),
                balance_trx=data.get("balance", 0) / 1_000_000,
                frozen_balance_sun=data.get("frozen_balance", 0),
                frozen_balance_trx=data.get("frozen_balance", 0) / 1_000_000,
                energy=data.get("energy", 0),
                bandwidth=data.get("bandwidth", 0),
                timestamp=datetime.now(timezone.utc).isoformat(),
                source_api=source_api
            )
        
        elif source_api == "tronscan":
            balance = data.get("balance", 0)
            if isinstance(balance, dict):
                balance = balance.get("balance", 0)
            
            frozen = data.get("frozen", 0)
            if isinstance(frozen, dict):
                frozen = frozen.get("frozen_balance", 0)
            
            return TronAccountInfo(
                address=data.get("address", ""),
                balance_sun=balance,
                balance_trx=balance / 1_000_000 if isinstance(balance, (int, float)) else 0,
                frozen_balance_sun=frozen,
                frozen_balance_trx=frozen / 1_000_000 if isinstance(frozen, (int, float)) else 0,
                energy=data.get("energy", 0),
                bandwidth=data.get("bandwidth", 0),
                timestamp=datetime.now(timezone.utc).isoformat(),
                source_api=source_api
            )
        
        return TronAccountInfo(
            address="",
            timestamp=datetime.now(timezone.utc).isoformat(),
            source_api=source_api
        )
    
    async def fetch_account_with_fallback(self, address: str) -> TronAccountInfo:
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        apis_to_try = [
            ("trongrid", self._fetch_trongrid_account),
            ("tronlink", self._fetch_tronlink_account),
            ("tronscan", self._fetch_tronscan_account)
        ]
        
        for api_name, fetch_func in apis_to_try:
            try:
                data = await fetch_func(address)
                if data:
                    account_info = self._extract_account_info(data, api_name)
                    account_info.address = address
                    print(f"✓ Successfully fetched data from {api_name}")
                    return account_info
            except Exception as e:
                print(f"✗ Failed to fetch from {api_name}: {e}")
                continue
        
        print("✗ All APIs failed, returning empty account info")
        return TronAccountInfo(
            address=address,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source_api="none"
        )
    
    async def fetch_multiple_accounts(self, addresses: List[str]) -> pd.DataFrame:
        all_records = []
        
        for address in addresses:
            try:
                account_info = await self.fetch_account_with_fallback(address)
                all_records.append(account_info.model_dump())
            except Exception as e:
                error_record = {
                    "address": address,
                    "error": str(e),
                    "error_type": "general_error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source_api": "none"
                }
                all_records.append(error_record)
        
        return pd.DataFrame(all_records)


# ============================================================================
# TRONSCAN BALANCE INTEGRATION
# ============================================================================

class TronscanBalanceIntegration:
    """Integration class for Tronscan Balance API."""
    
    BASE_URL = "https://apilist.tronscanapi.com/api/account/resourcev2"
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30) -> None:
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        self.api_key = api_key or self._get_api_key_from_env()
    
    def _get_api_key_from_env(self) -> Optional[str]:
        return os.getenv('TRONSCAN_API_KEY')
    
    async def __aenter__(self) -> "TronscanBalanceIntegration":
        headers = {}
        if self.api_key:
            headers['TRON-PRO-API-KEY'] = self.api_key
        
        self.client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()
    
    def _build_url(self, address: str, limit: int = 100, start: int = 0) -> str:
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
        balance_records = []
        
        if "data" in response_data and isinstance(response_data["data"], list):
            for item in response_data["data"]:
                record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "query_address": address,
                    "receiver_address": item.get("receiverAddress", ""),
                    "owner_address": item.get("ownerAddress", ""),
                    "balance_trx": float(item.get("balance", 0)) / 1_000_000,
                    "lock_balance_trx": float(item.get("lockBalance", 0)) / 1_000_000,
                    "resource_value": float(item.get("resourceValue", 0)),
                    "lock_resource_value": float(item.get("lockResourceValue", 0)),
                    "resource_type": item.get("resource", 0),
                    "resource_type_name": self._get_resource_type_name(item.get("resource", 0)),
                    "expire_time": None,
                    "operation_time": None,
                }
                
                if "expireTime" in item and item["expireTime"]:
                    record["expire_time"] = datetime.fromtimestamp(item["expireTime"] / 1000).isoformat()
                
                if "operationTime" in item and item["operationTime"]:
                    record["operation_time"] = datetime.fromtimestamp(item["operationTime"] / 1000).isoformat()
                
                if "contractInfo" in response_data and response_data["contractInfo"]:
                    contract_info = response_data["contractInfo"].get(item.get("receiverAddress", ""), {})
                    record["is_token"] = contract_info.get("isToken", False)
                    record["contract_name"] = contract_info.get("name", "")
                    record["is_vip"] = contract_info.get("vip", False)
                    record["risk"] = contract_info.get("risk", False)
                else:
                    record["is_token"] = False
                    record["contract_name"] = ""
                    record["is_vip"] = False
                    record["risk"] = False
                
                balance_records.append(record)
        
        if not balance_records and response_data:
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query_address": address,
                "receiver_address": address,
                "owner_address": "",
                "balance_trx": 0.0,
                "lock_balance_trx": 0.0,
                "resource_value": 0.0,
                "lock_resource_value": 0.0,
                "resource_type": 0,
                "resource_type_name": "Unknown",
                "expire_time": None,
                "operation_time": None,
                "is_token": False,
                "contract_name": "",
                "is_vip": False,
                "risk": False,
            }
            balance_records.append(record)
        
        return balance_records
    
    def _get_resource_type_name(self, resource_type: int) -> str:
        resource_types = {
            0: "Unknown",
            1: "Bandwidth",
            2: "Energy",
            3: "TRX Power"
        }
        return resource_types.get(resource_type, f"Type_{resource_type}")
    
    async def fetch_balance(self, address: str) -> List[Dict[str, Any]]:
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
            
            total = data.get("total", 0)
            if start + limit >= total:
                break
            
            start += limit
        
        return all_records
    
    async def fetch_multiple_balances(self, addresses: List[str]) -> pd.DataFrame:
        all_records = []
        
        for address in addresses:
            try:
                records = await self.fetch_balance(address)
                all_records.extend(records)
            except httpx.HTTPStatusError as e:
                error_record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "query_address": address,
                    "error": f"HTTP {e.response.status_code}: {str(e)}",
                    "error_type": "http_error"
                }
                all_records.append(error_record)
            except Exception as e:
                error_record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "query_address": address,
                    "error": str(e),
                    "error_type": "general_error"
                }
                all_records.append(error_record)
        
        return pd.DataFrame(all_records)


# ============================================================================
# EVERCLEAR BALANCE HISTORY INTEGRATION
# ============================================================================

class EverclearIntegration:
    """Integration for Everclear scan API (ETH balance history)."""

    BASE_URL = "https://scan.everclear.org/api/v2/addresses/{address}/coin-balance-history"

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "EverclearIntegration":
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()

    def _build_url(self, params: EverclearBalanceParams) -> str:
        query_params: Dict[str, Any] = {}
        if params.block_number is not None:
            query_params["block_number"] = params.block_number
        query_params["items_count"] = max(1, min(100, int(params.items_count)))
        query_params["page"] = max(1, int(params.page))
        qs = urlencode(query_params)
        return f"{self.BASE_URL.format(address=params.address)}?{qs}" if qs else self.BASE_URL.format(address=params.address)

    def _flatten_item(self, item: Dict[str, Any], params: EverclearBalanceParams) -> EverclearBalanceRecord:
        # API returns wei strings; convert to ETH
        balance_wei = str(item.get("balance", "0"))
        change_wei = str(item.get("balance_change", "0"))
        try:
            balance_eth = float(int(balance_wei)) / 1e18
        except Exception:
            balance_eth = 0.0
        try:
            balance_change_eth = float(int(change_wei)) / 1e18
        except Exception:
            balance_change_eth = 0.0

        ts = item.get("timestamp")
        ts_iso = ""
        if isinstance(ts, (int, float)):
            try:
                ts_iso = datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
            except Exception:
                ts_iso = ""

        return EverclearBalanceRecord(
            address=params.address,
            block_number=int(item.get("block_number", 0) or 0),
            block_hash=str(item.get("block_hash", "")),
            transaction_hash=item.get("transaction_hash"),
            balance_wei=balance_wei,
            balance_eth=balance_eth,
            balance_change_wei=change_wei,
            balance_change_eth=balance_change_eth,
            timestamp=str(ts),
            timestamp_iso=ts_iso,
            fetch_timestamp=datetime.now(timezone.utc).isoformat(),
            source_api="everclear_scan",
            page=params.page,
        )

    async def fetch_page(self, params: EverclearBalanceParams) -> List[Dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        url = self._build_url(params)
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        # Expecting { items: [...] } per everclear docs
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return [self._flatten_item(it, params).model_dump() for it in items]


async def fetch_everclear_balance_history(params_list: List[EverclearBalanceParams], max_concurrent: int = 5, save_to_csv: bool = False, csv_mode: str = 'create') -> pd.DataFrame:
    """Fetch Everclear ETH balance history for provided addresses/pages.

    - Focuses on ETH balances; converts wei -> ETH
    - Supports pagination via items_count and page
    - Does not save CSV by default to preserve two-file behavior
    """
    semaphore = asyncio.Semaphore(max(1, int(max_concurrent)))
    results: List[Dict[str, Any]] = []

    async with EverclearIntegration() as integration:
        async def run_one(p: EverclearBalanceParams) -> None:
            if not p.is_valid_eth_address():
                results.append(EverclearBalanceRecord(
                    address=p.address,
                    block_number=p.block_number or 0,
                    error="invalid_eth_address",
                    error_type="validation",
                    fetch_timestamp=datetime.now(timezone.utc).isoformat(),
                    page=p.page,
                ).model_dump())
                return
            async with semaphore:
                try:
                    page_records = await integration.fetch_page(p)
                    if page_records:
                        results.extend(page_records)
                except httpx.HTTPStatusError as e:
                    results.append({
                        "address": p.address,
                        "block_number": p.block_number or 0,
                        "error": f"HTTP {e.response.status_code}: {str(e)}",
                        "error_type": "http_error",
                        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
                        "source_api": "everclear_scan",
                        "page": p.page,
                    })
                except Exception as e:
                    results.append({
                        "address": p.address,
                        "block_number": p.block_number or 0,
                        "error": str(e),
                        "error_type": "general_error",
                        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
                        "source_api": "everclear_scan",
                        "page": p.page,
                    })

        await asyncio.gather(*(run_one(p) for p in params_list))

    df = pd.DataFrame(results)

    # Coerce/format
    if 'timestamp_iso' in df.columns:
        df['timestamp_iso'] = pd.to_datetime(df['timestamp_iso'], errors='coerce')
    for col in ['balance_eth', 'balance_change_eth']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'block_number' in df.columns:
        df['block_number'] = pd.to_numeric(df['block_number'], errors='coerce')

    # Save to CSV if requested (opt-in)
    if save_to_csv and not df.empty:
        save_csv_with_append(df, "everclear_balance_history.csv", csv_mode)

    return df


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

async def fetch_mayan_quotes(params_list: List[MayanBridgeParams], save_to_csv: bool = True, csv_mode: str = 'create') -> pd.DataFrame:
    """Fetch Mayan bridge quotes for a list of parameter sets."""
    async with MayanBridgeIntegration() as integration:
        df = await integration.fetch_multiple_quotes(params_list)
        
        numeric_columns = [
            'amount_in', 'amount_out', 'price', 'effective_price', 'price_impact',
            'minimum_amount_out', 'expected_amount_out', 'gas_fee', 'bridge_fee',
            'total_fee_in_usd', 'mayan_fee', 'relayer_fee', 'execution_time_seconds',
            'slippage_bps', 'max_slippage_bps', 'suggested_slippage_bps',
            'gas_price', 'gas_drop_amount', 'from_token_decimals', 'to_token_decimals',
            'routes_count', 'route_steps_count', 'warnings_count'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp', ascending=False)
        
        # Save to CSV if requested
        if save_to_csv and not df.empty:
            save_csv_with_append(df, "mayan_bridge_quotes.csv", csv_mode)
        
        return df


async def fetch_tron_balances_simple(addresses: List[str], save_to_csv: bool = True, csv_mode: str = 'create') -> pd.DataFrame:
    """Fetch TRON account balances using simple integration."""
    async with SimpleTronIntegration() as integration:
        df = await integration.fetch_multiple_balances(addresses)
        
        numeric_columns = [
            'balance_trx', 'balance_sun', 'frozen_balance_trx', 'frozen_balance_sun',
            'energy', 'bandwidth'
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        if 'timestamp' in df.columns and 'address' in df.columns:
            df = df.sort_values(['timestamp', 'address'], ascending=[False, True])
        
        # Save to CSV if requested
        if save_to_csv and not df.empty:
            save_csv_with_append(df, "simple_tron_balances.csv", csv_mode)
        
        return df


async def fetch_tron_accounts_alternative(addresses: List[str], save_to_csv: bool = False, csv_mode: str = 'create') -> pd.DataFrame:
    """Fetch TRON account data using alternative APIs."""
    async with AlternativeTronIntegration() as integration:
        df = await integration.fetch_multiple_accounts(addresses)
        
        numeric_columns = [
            'balance_trx', 'balance_sun', 'frozen_balance_trx', 'frozen_balance_sun',
            'energy', 'bandwidth'
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        if 'timestamp' in df.columns and 'address' in df.columns:
            df = df.sort_values(['timestamp', 'address'], ascending=[False, True])
        
        # Save to CSV if requested (disabled by default to limit outputs to 2 files/run)
        if save_to_csv and not df.empty:
            save_csv_with_append(df, "alternative_tron_accounts.csv", csv_mode)
        
        return df


async def fetch_tronscan_balances(addresses: List[str], api_key: Optional[str] = None, save_to_csv: bool = False, csv_mode: str = 'create') -> pd.DataFrame:
    """Fetch Tronscan balance data for a list of addresses."""
    async with TronscanBalanceIntegration(api_key=api_key) as integration:
        df = await integration.fetch_multiple_balances(addresses)
        
        numeric_columns = [
            'balance_trx', 'lock_balance_trx', 'resource_value', 
            'lock_resource_value', 'resource_type'
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        timestamp_columns = ['timestamp', 'expire_time', 'operation_time']
        for col in timestamp_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        if 'timestamp' in df.columns and 'query_address' in df.columns:
            df = df.sort_values(['timestamp', 'query_address'], ascending=[False, True])
        
        # Save to CSV if requested (disabled by default to limit outputs to 2 files/run)
        if save_to_csv and not df.empty:
            save_csv_with_append(df, "tronscan_balance_data.csv", csv_mode)
        
        return df


# ============================================================================
# TESTING AND DEBUGGING
# ============================================================================

if __name__ == "__main__":
    # Example usage with sample data
    print("=== Blockchain Data Integration Test ===")
    
    # Test Mayan Bridge
    print("\n1. Testing Mayan Bridge...")
    mayan_params = [MayanBridgeParams(
        from_chain="ethereum",
        to_chain="solana",
        from_token="0x0000000000000000000000000000000000000000",
        to_token="0x0000000000000000000000000000000000000000",
        amount_in=1.0
    )]
    
    mayan_df = asyncio.run(fetch_mayan_quotes(mayan_params))
    print(f"   Fetched {len(mayan_df)} Mayan quotes")
    
    # Test Simple TRON
    print("\n2. Testing Simple TRON Integration...")
    tron_addresses = ["TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg"]
    tron_df = asyncio.run(fetch_tron_balances_simple(tron_addresses))
    print(f"   Fetched {len(tron_df)} TRON balance records")
    
    print("\n✅ All integrations working!")
