"""
Everclear Balance History Integration

This module provides integration with the Everclear API to fetch ETH balance history
for addresses. It supports pagination and focuses on ETH balance tracking over time.

Author: Blockchain Integration Team  
Version: 1.0.0
"""

import asyncio
import csv
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict


class EverclearBalanceParams(BaseModel):
    """
    Input parameters for Everclear Balance API requests.
    
    Attributes:
        address (str): Ethereum address to query (e.g., "0xEFfAB7cCEBF63FbEFB4884964b12259d4374FaAa")
        block_number (Optional[int]): Starting block number for pagination
        items_count (int): Number of records per request (default: 50, max: 50)
    """
    address: str
    block_number: Optional[int] = None
    items_count: int = 50


class EverclearBalanceItem(BaseModel):
    """
    Model for individual balance history entry from Everclear API.
    
    Attributes:
        block_number (int): Block number when balance changed
        block_timestamp (str): ISO timestamp of the block
        delta (str): Balance change amount in wei (can be negative)
        transaction_hash (str): Hash of the transaction that caused the change
        value (str): Total balance after the transaction in wei
    """
    model_config = ConfigDict(extra='allow')
    
    block_number: int
    block_timestamp: str
    delta: str
    transaction_hash: str
    value: str


class EverclearBalanceResponse(BaseModel):
    """
    Model for the complete Everclear API response.
    
    Attributes:
        items (List[Dict[str, Any]]): List of balance history records
        next_page_params (Optional[Dict[str, Any]]): Parameters for next page if available
    """
    items: List[Dict[str, Any]]
    next_page_params: Optional[Dict[str, Any]] = None


class EverclearBalanceIntegration:
    """
    Integration class for Everclear Balance API.
    
    This class handles API communication, pagination, data processing, and error
    handling for the Everclear ETH balance history service.
    
    Attributes:
        BASE_URL (str): Base URL for Everclear API
        timeout (int): HTTP request timeout in seconds
        client (httpx.AsyncClient): HTTP client for making requests
    """
    
    BASE_URL = "https://scan.everclear.org/api/v2/addresses"
    
    def __init__(self, timeout: int = 30) -> None:
        """
        Initialize the Everclear Balance integration.
        
        Args:
            timeout (int): HTTP request timeout in seconds (default: 30)
        """
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "EverclearBalanceIntegration":
        """
        Async context manager entry.
        
        Returns:
            EverclearBalanceIntegration: Self instance with initialized HTTP client
        """
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """
        Async context manager exit.
        
        Args:
            *args: Exception information (if any)
        """
        if self.client:
            await self.client.aclose()
    
    def _build_url(self, params: EverclearBalanceParams) -> str:
        """
        Build URL with query parameters for the Everclear API.
        
        Args:
            params (EverclearBalanceParams): Balance request parameters
            
        Returns:
            str: Complete URL with query parameters
        """
        # Build the endpoint URL
        endpoint = f"{self.BASE_URL}/{params.address}/coin-balance-history"
        
        # Build query parameters
        query_params = {
            "items_count": params.items_count
        }
        
        # Add block_number if specified (for pagination)
        if params.block_number is not None:
            query_params["block_number"] = params.block_number
        
        query_string = urlencode(query_params)
        return f"{endpoint}?{query_string}"
    
    def _wei_to_eth(self, wei_value: str) -> float:
        """
        Convert wei value to ETH.
        
        Args:
            wei_value (str): Value in wei as string
            
        Returns:
            float: Value in ETH
        """
        try:
            wei = int(wei_value)
            return wei / 1e18  # 1 ETH = 10^18 wei
        except (ValueError, TypeError):
            return 0.0
    
    def _extract_balance_data(self, response_data: Dict[str, Any], query_address: str) -> List[Dict[str, Any]]:
        """
        Extract and flatten balance history data from API response.
        
        This method processes the Everclear API response and converts wei values
        to ETH, formats timestamps, and creates standardized records.
        
        Args:
            response_data (Dict[str, Any]): Raw API response data
            query_address (str): The address that was queried
            
        Returns:
            List[Dict[str, Any]]: List of flattened balance history records
        """
        balance_records: List[Dict[str, Any]] = []
        
        # Process items array
        if "items" in response_data and isinstance(response_data["items"], list):
            for item in response_data["items"]:
                record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_address": query_address,
                    "block_number": item.get("block_number", 0),
                    "block_timestamp": item.get("block_timestamp", ""),
                    "transaction_hash": item.get("transaction_hash", ""),
                    
                    # Convert wei values to ETH
                    "balance_eth": self._wei_to_eth(item.get("value", "0")),
                    "delta_eth": self._wei_to_eth(item.get("delta", "0")),
                    
                    # Keep original wei values for reference
                    "balance_wei": item.get("value", "0"),
                    "delta_wei": item.get("delta", "0"),
                    
                    # Parse block timestamp to datetime
                    "block_datetime": None,
                }
                
                # Convert block timestamp to datetime
                if item.get("block_timestamp"):
                    try:
                        record["block_datetime"] = datetime.fromisoformat(
                            item["block_timestamp"].replace("Z", "+00:00")
                        ).isoformat()
                    except (ValueError, TypeError):
                        record["block_datetime"] = None
                
                # Determine transaction type based on delta
                delta_value = float(record["delta_eth"])
                if delta_value > 0:
                    record["transaction_type"] = "INCOMING"
                elif delta_value < 0:
                    record["transaction_type"] = "OUTGOING"
                else:
                    record["transaction_type"] = "NO_CHANGE"
                
                # Calculate absolute delta for easier analysis
                record["delta_eth_abs"] = abs(delta_value)
                
                balance_records.append(record)
        
        # Add pagination info if available
        if "next_page_params" in response_data and response_data["next_page_params"]:
            next_params = response_data["next_page_params"]
            # Add pagination info to the last record for reference
            if balance_records:
                balance_records[-1]["next_block_number"] = next_params.get("block_number")
                balance_records[-1]["next_items_count"] = next_params.get("items_count")
        
        return balance_records
    
    async def fetch_balance_history(self, params: EverclearBalanceParams, max_pages: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch balance history for a single address with automatic pagination.
        
        This method handles pagination automatically, fetching multiple pages
        of balance history up to the specified maximum.
        
        Args:
            params (EverclearBalanceParams): Balance request parameters
            max_pages (int): Maximum number of pages to fetch (default: 10)
            
        Returns:
            List[Dict[str, Any]]: List of all balance history records
            
        Raises:
            RuntimeError: If client is not initialized
            httpx.HTTPStatusError: If API request fails
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        all_records: List[Dict[str, Any]] = []
        current_params = params.model_copy()
        pages_fetched = 0
        
        while pages_fetched < max_pages:
            url = self._build_url(current_params)
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            records = self._extract_balance_data(data, params.address)
            all_records.extend(records)
            
            pages_fetched += 1
            
            # Check if there are more pages
            if "next_page_params" not in data or not data["next_page_params"]:
                break
            
            # Update parameters for next page
            next_params = data["next_page_params"]
            current_params.block_number = next_params.get("block_number")
            current_params.items_count = next_params.get("items_count", params.items_count)
        
        return all_records
    
    async def fetch_multiple_balance_histories(self, params_list: List[EverclearBalanceParams], max_pages: int = 10) -> pd.DataFrame:
        """
        Fetch balance histories for multiple addresses and return as DataFrame.
        
        This method processes multiple balance history requests and handles errors
        gracefully, ensuring that failures in individual requests don't stop the
        entire batch process.
        
        Args:
            params_list (List[EverclearBalanceParams]): List of balance request parameters
            max_pages (int): Maximum number of pages per address (default: 10)
            
        Returns:
            pd.DataFrame: DataFrame containing all balance history data with proper typing
        """
        all_records: List[Dict[str, Any]] = []
        
        for params in params_list:
            try:
                records = await self.fetch_balance_history(params, max_pages)
                all_records.extend(records)
            except httpx.HTTPStatusError as e:
                error_record = self._create_error_record(params, f"HTTP {e.response.status_code}: {str(e)}", "http_error")
                all_records.append(error_record)
            except Exception as e:
                error_record = self._create_error_record(params, str(e), "general_error")
                all_records.append(error_record)
        
        df = pd.DataFrame(all_records)
        return self._format_dataframe(df)
    
    def _create_error_record(self, params: EverclearBalanceParams, error_msg: str, error_type: str) -> Dict[str, Any]:
        """
        Create a standardized error record for failed requests.
        
        Args:
            params (EverclearBalanceParams): Original request parameters
            error_msg (str): Error message
            error_type (str): Type of error
            
        Returns:
            Dict[str, Any]: Error record dictionary
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "query_address": params.address,
            "error": error_msg,
            "error_type": error_type
        }
    
    def _format_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format DataFrame with proper data types and sorting.
        
        Args:
            df (pd.DataFrame): Raw DataFrame
            
        Returns:
            pd.DataFrame: Formatted DataFrame with proper types
        """
        if df.empty:
            return df
        
        # Define numeric columns for type conversion
        numeric_columns = [
            'block_number', 'balance_eth', 'delta_eth', 'delta_eth_abs',
            'next_block_number', 'next_items_count'
        ]
        
        # Convert numeric columns
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert timestamp columns to datetime
        timestamp_columns = ['timestamp', 'block_datetime']
        for col in timestamp_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Sort by block number (most recent first)
        if 'block_number' in df.columns:
            df = df.sort_values('block_number', ascending=False)
        
        return df
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        Save DataFrame to CSV file.
        
        Args:
            df (pd.DataFrame): DataFrame to save
            filename (str): Optional filename, auto-generated if not provided
            
        Returns:
            str: Filename of the saved CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"everclear_balance_history_{timestamp}.csv"
        
        df.to_csv(filename, index=False)
        return filename


async def fetch_everclear_balance_data(params_list: List[EverclearBalanceParams], max_pages: int = 10, save_csv: bool = True) -> pd.DataFrame:
    """
    Main function to fetch Everclear balance history data and return as DataFrame.
    
    This is the primary entry point for fetching ETH balance history from the Everclear API.
    It handles the complete workflow from parameter validation to data formatting and CSV export.
    
    Args:
        params_list (List[EverclearBalanceParams]): List of balance request parameters
        max_pages (int): Maximum number of pages per address (default: 10)
        save_csv (bool): Whether to save results to CSV file (default: True)
        
    Returns:
        pd.DataFrame: DataFrame containing flattened balance history data with proper typing
        
    Example:
        >>> params = [EverclearBalanceParams(
        ...     address="0xEFfAB7cCEBF63FbEFB4884964b12259d4374FaAa",
        ...     items_count=50
        ... )]
        >>> df = await fetch_everclear_balance_data(params)
        >>> print(f"Fetched balance history for {len(df)} records")
    """
    if not params_list:
        return pd.DataFrame()
    
    async with EverclearBalanceIntegration() as integration:
        df = await integration.fetch_multiple_balance_histories(params_list, max_pages)
        
        if save_csv and not df.empty:
            filename = integration.save_to_csv(df)
            print(f"Balance history data saved to {filename}")
        
        return df


# Update the Tronscan integration to include the API key
def update_tronscan_integration_with_api_key():
    """
    Update the existing Tronscan integration to include the API key.
    """
    api_key = "632bbbf6-ad87-4575-9b22-a7a6876f5af2"
    
    # Read the existing file
    with open("tronscan_balance_integration.py", "r") as f:
        content = f.read()
    
    # Add API key to the TronscanBalanceIntegration class
    updated_content = content.replace(
        'BASE_URL = "https://apilist.tronscanapi.com/api/account/resourcev2"',
        f'BASE_URL = "https://apilist.tronscanapi.com/api/account/resourcev2"\n    API_KEY = "{api_key}"'
    )
    
    # Update the _build_url method to include API key
    updated_content = updated_content.replace(
        'query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])',
        '''query_params["api_key"] = self.API_KEY
        query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])'''
    )
    
    # Write the updated content back
    with open("tronscan_balance_integration.py", "w") as f:
        f.write(updated_content)


# Example usage and testing
if __name__ == "__main__":
    async def main():
        """Example usage of the Everclear Balance integration."""
        # Example addresses for testing
        example_params = [
            EverclearBalanceParams(
                address="0xEFfAB7cCEBF63FbEFB4884964b12259d4374FaAa",
                items_count=50
            ),
            # Add more addresses as needed
            # EverclearBalanceParams(
            #     address="0x742d35Cc6634C0532925a3b8D4C9db96C8b8C4e6",
            #     items_count=50
            # ),
        ]
        
        # Fetch data with pagination (max 5 pages per address)
        df = await fetch_everclear_balance_data(example_params, max_pages=5, save_csv=True)
        
        # Display results
        print(f"Fetched balance history for {len(df)} records")
        print("\nDataFrame Info:")
        print(df.info())
        
        if len(df) > 0:
            print("\nFirst few rows:")
            print(df.head())
            
            # Display summary statistics
            print(f"\nSummary:")
            print(f"Unique addresses: {df['query_address'].nunique() if 'query_address' in df.columns else 0}")
            print(f"Date range: {df['block_datetime'].min()} to {df['block_datetime'].max()}" if 'block_datetime' in df.columns else "No date data")
            print(f"Total transactions: {len(df)}")
            
            if 'balance_eth' in df.columns:
                print(f"Current ETH balance: {df['balance_eth'].iloc[0]:.6f} ETH" if len(df) > 0 else "No balance data")
                print(f"Largest incoming: {df[df['transaction_type'] == 'INCOMING']['delta_eth_abs'].max():.6f} ETH" if 'transaction_type' in df.columns else "")
                print(f"Largest outgoing: {df[df['transaction_type'] == 'OUTGOING']['delta_eth_abs'].max():.6f} ETH" if 'transaction_type' in df.columns else "")
    
    # Update Tronscan integration with API key
    update_tronscan_integration_with_api_key()
    print("Updated Tronscan integration with API key")
    
    # Run the example
    asyncio.run(main())