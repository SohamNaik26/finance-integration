#!/usr/bin/env python3
"""
Finance Integration Project

This is the main application file that runs both Everclear and Tronscan integrations.
It demonstrates how to use the blockchain balance tracking modules.

Author: Blockchain Integration Team
Version: 1.0.0
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

from everclear_balance_integration import fetch_everclear_balance_data, EverclearBalanceParams
from tronscan_balance_integration import fetch_tronscan_balance_data


async def run_everclear_integration():
    """Run the Everclear balance integration example."""
    print("=" * 60)
    print("EVERCLEAR BALANCE INTEGRATION")
    print("=" * 60)
    
    # Example Ethereum addresses for testing
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
    
    try:
        # Fetch data with pagination (max 5 pages per address)
        df = await fetch_everclear_balance_data(example_params, max_pages=5, save_csv=True)
        
        # Display results
        print(f"✅ Fetched balance history for {len(df)} records")
        print("\nDataFrame Info:")
        print(df.info())
        
        if len(df) > 0:
            print("\nFirst few rows:")
            print(df.head())
            
            # Display summary statistics
            print(f"\n📊 Summary:")
            print(f"Unique addresses: {df['query_address'].nunique() if 'query_address' in df.columns else 0}")
            print(f"Date range: {df['block_datetime'].min()} to {df['block_datetime'].max()}" if 'block_datetime' in df.columns else "No date data")
            print(f"Total transactions: {len(df)}")
            
            if 'balance_eth' in df.columns:
                print(f"Current ETH balance: {df['balance_eth'].iloc[0]:.6f} ETH" if len(df) > 0 else "No balance data")
                print(f"Largest incoming: {df[df['transaction_type'] == 'INCOMING']['delta_eth_abs'].max():.6f} ETH" if 'transaction_type' in df.columns else "")
                print(f"Largest outgoing: {df[df['transaction_type'] == 'OUTGOING']['delta_eth_abs'].max():.6f} ETH" if 'transaction_type' in df.columns else "")
        else:
            print("⚠️  No data returned from Everclear API")
            
    except Exception as e:
        print(f"❌ Error in Everclear integration: {str(e)}")


async def run_tronscan_integration():
    """Run the Tronscan balance integration example."""
    print("\n" + "=" * 60)
    print("TRONSCAN BALANCE INTEGRATION")
    print("=" * 60)
    
    # Example TRON addresses for testing (using well-known addresses)
    addresses = [
        "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH",  # TRON Foundation address
        "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE",  # Another well-known address
    ]
    
    try:
        # Fetch data
        df = await fetch_tronscan_balance_data(addresses)
        
        # Display results
        print(f"✅ Fetched {len(df)} balance records")
        print("\nDataFrame Info:")
        print(df.info())
        print("\nFirst few rows:")
        print(df.head())
        
        # Save to CSV for inspection
        df.to_csv("tronscan_balance_data.csv", index=False)
        print("\n💾 Data saved to tronscan_balance_data.csv")
        
        if len(df) > 0:
            print(f"\n📊 Summary:")
            print(f"Unique addresses: {df['query_address'].nunique() if 'query_address' in df.columns else 0}")
            print(f"Total records: {len(df)}")
            
            if 'balance_trx' in df.columns:
                print(f"Total TRX balance: {df['balance_trx'].sum():.6f} TRX")
                print(f"Average balance: {df['balance_trx'].mean():.6f} TRX")
        else:
            print("⚠️  No data returned from Tronscan API")
            
    except Exception as e:
        print(f"❌ Error in Tronscan integration: {str(e)}")


async def main():
    """Main function to run all integrations."""
    print("🚀 Starting Finance Integration Project")
    print("This project demonstrates blockchain balance tracking for ETH and TRX")
    print()
    
    # Run Everclear integration
    await run_everclear_integration()
    
    # Run Tronscan integration
    await run_tronscan_integration()
    
    print("\n" + "=" * 60)
    print("✅ PROJECT COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("Check the generated CSV files for detailed data:")
    print("- everclear_balance_history_*.csv")
    print("- tronscan_balance_data.csv")


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())