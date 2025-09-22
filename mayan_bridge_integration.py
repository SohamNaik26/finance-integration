"""
Mayan Bridge Data Integration

This module provides async integration with the Mayan Finance API to fetch
cross-chain bridge quotes. It includes data flattening, error handling,
and type safety using Pydantic models.

Author: Blockchain Integration Team
Version: 1.0.0
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict


class MayanBridgeParams(BaseModel):
    """
    Input parameters for Mayan Bridge API requests.
    
    Attributes:
        from_chain (str): Source blockchain (e.g., "ethereum", "solana")
        to_chain (str): Destination blockchain (e.g., "ethereum", "solana")
        from_token (str): Source token address or "0x0000..." for native token
        to_token (str): Destination token address or "0x0000..." for native token
        amount_in (float): Amount to swap, defaults to 1.0
        slippage_bps (str): Slippage tolerance in basis points, defaults to "auto"
        referrer (str): Referrer address for fee sharing
    """
    from_chain: str
    to_chain: str
    from_token: str
    to_token: str
    amount_in: float = 1.0
    slippage_bps: str = "auto"
    referrer: str = "7HN4qCvG2dP5oagZRxj2dTGPhksgRnKCaLPjtjKEr1Ho"


class MayanBridgeIntegration:
    """
    Integration class for Mayan Bridge API.
    
    This class handles async HTTP requests to the Mayan Finance API,
    processes responses, and flattens complex nested data structures
    for easy DataFrame consumption.
    
    Attributes:
        BASE_URL (str): Base URL for Mayan Finance API
        timeout (int): HTTP request timeout in seconds
        client (Optional[httpx.AsyncClient]): Async HTTP client instance
    """
    
    BASE_URL = "https://price-api.mayan.finance/v3/quote"
    
    def __init__(self, timeout: int = 30) -> None:
        """
        Initialize the Mayan Bridge integration.
        
        Args:
            timeout (int): HTTP request timeout in seconds, defaults to 30
        """
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "MayanBridgeIntegration":
        """
        Async context manager entry.
        
        Returns:
            MayanBridgeIntegration: Self instance with initialized HTTP client
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
    
    def _build_url(self, params: MayanBridgeParams) -> str:
        """
        Build the complete API URL with query parameters.
        
        Args:
            params (MayanBridgeParams): Request parameters
            
        Returns:
            str: Complete URL with encoded query parameters
        """
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
        """
        Flatten nested API response data into a single dictionary.
        
        This method extracts key information from the complex nested JSON
        response and creates a flat structure suitable for DataFrame storage.
        Complex nested objects are stored as JSON strings.
        
        Args:
            data (Dict[str, Any]): Raw API response data
            params (MayanBridgeParams): Original request parameters
            
        Returns:
            Dict[str, Any]: Flattened data dictionary
        """
        flattened: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
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
            flattened["suggested_slippage_bps"] = data.get("suggestedSlippageBps", 0)
            
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
        """
        Fetch a single quote from the Mayan API.
        
        Args:
            params (MayanBridgeParams): Request parameters for the quote
            
        Returns:
            Dict[str, Any]: Flattened quote data
            
        Raises:
            RuntimeError: If HTTP client is not initialized
            httpx.HTTPStatusError: If API request fails
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        url = self._build_url(params)
        response = await self.client.get(url)
        response.raise_for_status()
        
        data = response.json()
        return self._flatten_quote_data(data, params)
    
    async def fetch_multiple_quotes(self, params_list: List[MayanBridgeParams]) -> pd.DataFrame:
        """
        Fetch multiple quotes and return as a pandas DataFrame.
        
        This method processes multiple quote requests concurrently and handles
        individual failures gracefully. Failed requests are logged in the
        DataFrame with error information.
        
        Args:
            params_list (List[MayanBridgeParams]): List of quote parameters
            
        Returns:
            pd.DataFrame: DataFrame containing all quote data and any errors
        """
        quotes: List[Dict[str, Any]] = []
        
        for params in params_list:
            try:
                quote = await self.fetch_quote(params)
                quotes.append(quote)
            except httpx.HTTPStatusError as e:
                # Log HTTP errors with detailed information
                error_record = {
                    "timestamp": datetime.utcnow().isoformat(),
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
                # Log other errors
                error_record = {
                    "timestamp": datetime.utcnow().isoformat(),
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


async def fetch_mayan_bridge_data(params_list: List[MayanBridgeParams]) -> pd.DataFrame:
    """
    Main function to fetch Mayan bridge data and return as DataFrame.
    
    This is the primary entry point for fetching bridge quote data.
    It handles the async context management and data type conversion.
    
    Args:
        params_list (List[MayanBridgeParams]): List of quote parameters to fetch
        
    Returns:
        pd.DataFrame: DataFrame containing flattened quote data with proper types
        
    Example:
        >>> params = [
        ...     MayanBridgeParams(
        ...         from_chain="ethereum",
        ...         to_chain="solana",
        ...         from_token="0x0000000000000000000000000000000000000000",
        ...         to_token="0x0000000000000000000000000000000000000000",
        ...         amount_in=1.0
        ...     )
        ... ]
        >>> df = await fetch_mayan_bridge_data(params)
        >>> print(f"Fetched {len(df)} quotes")
    """
    async with MayanBridgeIntegration() as integration:
        df = await integration.fetch_multiple_quotes(params_list)
        
        # Ensure proper data types for numeric columns
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
        
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by timestamp (most recent first)
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp', ascending=False)
        
        return df


# Example usage and testing
if __name__ == "__main__":
    async def main():
        """Example usage of the Mayan Bridge integration."""
        # Example parameters - modify as needed
        params_list = [
            MayanBridgeParams(
                from_chain="ethereum",
                to_chain="solana",
                from_token="0x0000000000000000000000000000000000000000",  # ETH native
                to_token="0x0000000000000000000000000000000000000000",    # SOL native
                amount_in=1.0
            ),
            # Example: USDC from Ethereum to Solana
            MayanBridgeParams(
                from_chain="ethereum",
                to_chain="solana",
                from_token="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC on Ethereum
                to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",   # USDC on Solana
                amount_in=100.0
            ),
        ]
        
        # Fetch data
        df = await fetch_mayan_bridge_data(params_list)
        
        # Display results
        print(f"Fetched {len(df)} quotes")
        print("\nDataFrame Info:")
        print(df.info())
        print("\nFirst few rows:")
        print(df.head())
        
        # Save to CSV for inspection
        df.to_csv("mayan_bridge_quotes.csv", index=False)
        print("\nData saved to mayan_bridge_quotes.csv")
        
        return df
    
    # Run the example
    asyncio.run(main())