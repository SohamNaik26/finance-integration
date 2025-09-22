"""
Tronscan Balance Data Integration

This module provides async integration with the Tronscan API to fetch
balance and resource delegation data. It includes pagination support,
data flattening, and comprehensive error handling.

Author: Blockchain Integration Team
Version: 1.0.0
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict


class TronResourceData(BaseModel):
    """
    Model for individual resource/balance entry from Tronscan API.
    
    Attributes:
        receiver_address (str): Address receiving the resource delegation
        expire_time (Optional[int]): Expiration timestamp in milliseconds
        balance (float): Balance amount in TRX
        resource (int): Resource type identifier
        receiver_address_tag (str): Tag for the receiver address
        lock_balance (float): Locked balance amount
        lock_resource_value (float): Locked resource value
        owner_address (Optional[str]): Address of the resource owner
        resource_value (float): Current resource value
        operation_time (Optional[int]): Operation timestamp in milliseconds
    """
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
    """
    Main response model for Tronscan API balance endpoint.
    
    Attributes:
        total (int): Total number of records available
        data (List[Dict[str, Any]]): List of balance/resource records
        contract_map (Optional[Dict[str, bool]]): Contract information mapping
        range_total (Optional[int]): Range total for pagination
        contract_info (Optional[Dict[str, Any]]): Detailed contract information
        normal_address_info (Optional[Dict[str, Any]]): Normal address metadata
    """
    total: int
    data: List[Dict[str, Any]]
    contract_map: Optional[Dict[str, bool]] = None
    range_total: Optional[int] = None
    contract_info: Optional[Dict[str, Any]] = None
    normal_address_info: Optional[Dict[str, Any]] = None


class TronscanBalanceIntegration:
    """
    Integration class for Tronscan Balance API.
    
    This class handles async HTTP requests to the Tronscan API,
    processes paginated responses, and extracts balance-related data
    with proper unit conversions (sun to TRX).
    
    Attributes:
        BASE_URL (str): Base URL for Tronscan API
        timeout (int): HTTP request timeout in seconds
        client (Optional[httpx.AsyncClient]): Async HTTP client instance
    """
    
    BASE_URL = "https://apilist.tronscanapi.com/api/account/resourcev2"
    API_KEY = "43424ea5-d13e-4b7a-9d11-b627fc3ad261"
    
    def __init__(self, timeout: int = 30) -> None:
        """
        Initialize the Tronscan Balance integration.
        
        Args:
            timeout (int): HTTP request timeout in seconds, defaults to 30
        """
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "TronscanBalanceIntegration":
        """
        Async context manager entry.
        
        Returns:
            TronscanBalanceIntegration: Self instance with initialized HTTP client
        """
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """
        Async context manager exit. Closes HTTP client connection.
        
        Args:
            *args: Exception information (if any)
        """
        if self.client:
            await self.client.aclose()
    
    def _build_url(self, address: str, limit: int = 100, start: int = 0) -> str:
        """
        Build URL with query parameters for the Tronscan API.
        
        Args:
            address (str): TRON address to query
            limit (int): Number of records per page, defaults to 100
            start (int): Starting offset for pagination, defaults to 0
            
        Returns:
            str: Complete URL with encoded query parameters
        """
        params = {
            "limit": limit,
            "start": start,
            "address": address,
            "type": 1,
            "resourceType": 0
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.BASE_URL}?{query_string}"
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for Tronscan API requests.
        
        Returns:
            Dict[str, str]: Headers including API key
        """
        return {
            "TRON-PRO-API-KEY": self.API_KEY,
            "Content-Type": "application/json"
        }
    
    def _get_resource_type_name(self, resource_type: int) -> str:
        """
        Convert resource type integer to human-readable name.
        
        Args:
            resource_type (int): Numeric resource type identifier
            
        Returns:
            str: Human-readable resource type name
        """
        resource_types = {
            0: "BANDWIDTH",
            1: "ENERGY",
            2: "TRON_POWER"
        }
        return resource_types.get(resource_type, f"UNKNOWN_{resource_type}")
    
    def _extract_balance_data(self, response_data: Dict[str, Any], query_address: str) -> List[Dict[str, Any]]:
        """
        Extract and flatten balance-related data from API response.
        
        This method processes the complex nested response structure and
        extracts only balance-relevant information. It converts sun units
        to TRX and handles timestamp conversions.
        
        Args:
            response_data (Dict[str, Any]): Raw API response data
            query_address (str): Original address that was queried
            
        Returns:
            List[Dict[str, Any]]: List of flattened balance records
        """
        balance_records = []
        
        # Process main data array
        if "data" in response_data and isinstance(response_data["data"], list):
            for item in response_data["data"]:
                record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_address": query_address,
                    "receiver_address": item.get("receiverAddress", ""),
                    "owner_address": item.get("ownerAddress", ""),
                    "balance_trx": float(item.get("balance", 0)) / 1_000_000,  # Convert sun to TRX
                    "lock_balance_trx": float(item.get("lockBalance", 0)) / 1_000_000,
                    "resource_value": float(item.get("resourceValue", 0)),
                    "lock_resource_value": float(item.get("lockResourceValue", 0)),
                    "resource_type": item.get("resource", 0),
                    "resource_type_name": self._get_resource_type_name(item.get("resource", 0)),
                    "expire_time": None,
                    "operation_time": None,
                    "receiver_address_tag": item.get("receiverAddressTag", ""),
                }
                
                # Convert timestamps from milliseconds to ISO format
                if "expireTime" in item and item["expireTime"]:
                    try:
                        record["expire_time"] = datetime.fromtimestamp(
                            item["expireTime"] / 1000
                        ).isoformat()
                    except (ValueError, TypeError):
                        record["expire_time"] = None
                
                if "operationTime" in item and item["operationTime"]:
                    try:
                        record["operation_time"] = datetime.fromtimestamp(
                            item["operationTime"] / 1000
                        ).isoformat()
                    except (ValueError, TypeError):
                        record["operation_time"] = None
                
                # Add contract information if available
                if "contractInfo" in response_data and response_data["contractInfo"]:
                    receiver_addr = item.get("receiverAddress", "")
                    contract_info = response_data["contractInfo"].get(receiver_addr, {})
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
        
        # If no data records found, create a single record with basic info
        if not balance_records and response_data:
            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "query_address": query_address,
                "receiver_address": query_address,
                "owner_address": "",
                "balance_trx": 0.0,
                "lock_balance_trx": 0.0,
                "resource_value": 0.0,
                "lock_resource_value": 0.0,
                "resource_type": 0,
                "resource_type_name": "BANDWIDTH",
                "expire_time": None,
                "operation_time": None,
                "receiver_address_tag": "",
                "is_token": False,
                "contract_name": "",
                "is_vip": False,
                "risk": False,
            }
            balance_records.append(record)
        
        return balance_records
    
    async def fetch_balance(self, address: str) -> List[Dict[str, Any]]:
        """
        Fetch balance data for a single TRON address with pagination support.
        
        This method handles automatic pagination to retrieve all available
        balance records for the specified address.
        
        Args:
            address (str): TRON address to query (e.g., "TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg")
            
        Returns:
            List[Dict[str, Any]]: List of all balance records for the address
            
        Raises:
            RuntimeError: If HTTP client is not initialized
            httpx.HTTPStatusError: If API request fails
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        all_records = []
        start = 0
        limit = 100
        
        while True:
            url = self._build_url(address, limit, start)
            headers = self._get_headers()
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            records = self._extract_balance_data(data, address)
            all_records.extend(records)
            
            # Check if there are more pages to fetch
            total = data.get("total", 0)
            if start + limit >= total or len(records) == 0:
                break
            
            start += limit
        
        return all_records
    
    async def fetch_multiple_balances(self, addresses: List[str]) -> pd.DataFrame:
        """
        Fetch balances for multiple TRON addresses.
        
        This method processes multiple addresses and handles individual
        failures gracefully. Failed requests are logged in the DataFrame
        with error information.
        
        Args:
            addresses (List[str]): List of TRON addresses to query
            
        Returns:
            pd.DataFrame: DataFrame containing all balance data and any errors
        """
        all_records = []
        
        for address in addresses:
            try:
                records = await self.fetch_balance(address)
                all_records.extend(records)
            except httpx.HTTPStatusError as e:
                # Log HTTP errors with detailed information
                error_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_address": address,
                    "error": f"HTTP {e.response.status_code}: {str(e)}",
                    "error_type": "http_error"
                }
                all_records.append(error_record)
            except Exception as e:
                # Log other errors
                error_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_address": address,
                    "error": str(e),
                    "error_type": "general_error"
                }
                all_records.append(error_record)
        
        return pd.DataFrame(all_records)


async def fetch_tronscan_balance_data(addresses: List[str]) -> pd.DataFrame:
    """
    Main function to fetch Tronscan balance data and return as DataFrame.
    
    This is the primary entry point for fetching balance data from Tronscan.
    It handles the async context management and data type conversion.
    
    Args:
        addresses (List[str]): List of TRON addresses to query
        
    Returns:
        pd.DataFrame: DataFrame containing flattened balance data with proper types
        
    Example:
        >>> addresses = [
        ...     "TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg",
        ...     "TN3W4H6rK2ce4vX9YnFQHwKENnHjoxb3m9"
        ... ]
        >>> df = await fetch_tronscan_balance_data(addresses)
        >>> print(f"Fetched {len(df)} balance records")
    """
    async with TronscanBalanceIntegration() as integration:
        df = await integration.fetch_multiple_balances(addresses)
        
        # Ensure proper data types for numeric columns
        numeric_columns = [
            'balance_trx', 'lock_balance_trx', 'resource_value',
            'lock_resource_value', 'resource_type'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert timestamp columns to datetime
        timestamp_columns = ['timestamp', 'expire_time', 'operation_time']
        for col in timestamp_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Sort by timestamp and address (most recent first)
        if 'timestamp' in df.columns and 'query_address' in df.columns:
            df = df.sort_values(['timestamp', 'query_address'], ascending=[False, True])
        
        return df


# Example usage and testing
if __name__ == "__main__":
    async def main():
        """Example usage of the Tronscan Balance integration."""
        # Example addresses - modify as needed
        addresses = [
            "TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg",  # Example TRON address
            "TN3W4H6rK2ce4vX9YnFQHwKENnHjoxb3m9",  # Another example address
        ]
        
        # Fetch data
        df = await fetch_tronscan_balance_data(addresses)
        
        # Display results
        print(f"Fetched {len(df)} balance records")
        print("\nDataFrame Info:")
        print(df.info())
        print("\nFirst few rows:")
        print(df.head())
        
        # Save to CSV for inspection
        df.to_csv("tronscan_balance_data.csv", index=False)
        print("\nData saved to tronscan_balance_data.csv")
        
        return df
    
    # Run the example
    asyncio.run(main())