# Blockchain Data Integrations

Python 3.13+ async integrations for Mayan Bridge and Tronscan Balance APIs with strict typing using Pydantic.

## Features

### 1. Mayan Bridge Integration
- Fetches cross-chain bridge quotes from Mayan Finance API
- Supports multiple token pairs and chains
- Flattens complex nested data structures
- Stores route information and metadata as JSON strings
- Outputs single DataFrame with all quote information

### 2. Tronscan Balance Integration  
- Fetches token balance information from Tronscan API
- Focuses on balance-related data only
- Supports pagination for large result sets
- Converts balances from sun to TRX
- Designed for hourly scheduled runs

## Installation

### Using UV Package Manager (Recommended)

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -r pyproject.toml

# Or sync the environment
uv sync
```

### Using pip

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Unix/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## requirements.txt

```
httpx>=0.27.0
pandas>=2.2.0
pydantic>=2.6.0
python-dotenv>=1.0.0
```

## Usage

### Quick Start

```python
import asyncio
from mayan_bridge_integration import main_mayan_bridge
from tronscan_balance_integration import main_tronscan_balance

# Run Mayan Bridge integration
mayan_df = asyncio.run(main_mayan_bridge())
print(f"Fetched {len(mayan_df)} Mayan quotes")

# Run Tronscan Balance integration  
tronscan_df = asyncio.run(main_tronscan_balance())
print(f"Fetched {len(tronscan_df)} balance records")
```

### Using the Main Runner

```bash
# Run both integrations
python main.py
```

### Custom Configuration

```python
import asyncio
from main import IntegrationRunner

async def run_custom():
    runner = IntegrationRunner(output_dir="my_data")
    
    # Custom Mayan configuration
    mayan_config = {
        "token_pairs": [
            {
                "from_chain": "ethereum",
                "to_chain": "solana", 
                "from_token": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC
                "to_token": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "amount_in": 1000.0
            }
        ],
        "save_csv": True
    }
    
    # Custom Tronscan configuration
    tronscan_config = {
        "addresses": [
            "TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg",
            "TN3W4H6rK2ce4vX9YnFQHwKENnHjoxb3m9"
        ],
        "save_csv": True
    }
    
    mayan_df, tronscan_df = await runner.run_all_integrations(
        mayan_config=mayan_config,
        tronscan_config=tronscan_config
    )
    
    return mayan_df, tronscan_df

# Run
mayan_df, tronscan_df = asyncio.run(run_custom())
```

## Scheduling Hourly Runs

### Using cron (Unix/Linux/macOS)

```bash
# Edit crontab
crontab -e

# Add hourly job
0 * * * * /path/to/python /path/to/tronscan_balance_integration.py
```

### Using Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "Daily" and repeat every 1 hour
4. Set action to run Python script

### Using Python Scheduler

```python
import schedule
import time
import asyncio
from tronscan_balance_integration import main_tronscan_balance

def run_hourly():
    df = asyncio.run(main_tronscan_balance())
    df.to_csv(f"balance_{datetime.now():%Y%m%d_%H%M%S}.csv")

schedule.every().hour.do(run_hourly)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Data Output

### Mayan Bridge DataFrame Columns
- `timestamp`: Request timestamp
- `from_chain`, `to_chain`: Source and destination chains
- `from_token`, `to_token`: Token addresses
- `amount_in`, `amount_out`: Input and output amounts
- `price`, `effective_price`, `price_impact`: Pricing information
- `gas_fee`, `bridge_fee`, `total_fee_in_usd`: Fee breakdown
- `routes_json`: Complex route data as JSON string
- `from_token_symbol`, `to_token_symbol`: Token symbols
- And more...

### Tronscan Balance DataFrame Columns
- `timestamp`: Request timestamp
- `query_address`: Address queried
- `receiver_address`, `owner_address`: Address details
- `balance_trx`, `lock_balance_trx`: Balance in TRX
- `resource_value`, `lock_resource_value`: Resource information
- `resource_type_name`: Human-readable resource type
- `is_token`, `contract_name`: Contract information
- And more...

## Type Safety

All functions use strict typing with Pydantic models:

```python
from pydantic import BaseModel

class MayanBridgeParams(BaseModel):
    from_chain: str
    to_chain: str
    from_token: str
    to_token: str
    amount_in: float = 1.0
    slippage_bps: str = "auto"
```

## Error Handling

- Individual API failures don't stop batch processing
- Errors are logged in the DataFrame with error messages
- HTTP retries handled automatically by httpx
- Partial results preserved on failure

## Development

### Running Tests

```bash
# Using pytest
pytest tests/

# With coverage
pytest --cov=. --cov-report=html
```

### Code Formatting

```bash
# Format with black
black .

# Lint with ruff
ruff check .

# Type check with mypy
mypy .
```

## Project Structure

```
blockchain-integrations/
├── mayan_bridge_integration.py    # Mayan Bridge API integration
├── tronscan_balance_integration.py # Tronscan Balance API integration
├── main.py                        # Main runner coordinating both
├── pyproject.toml                 # UV/pip configuration
├── requirements.txt               # Alternative pip requirements
├── README.md                      # This file
├── data/                         # Output directory for CSV files
└── tests/                        # Unit tests
    ├── test_mayan_integration.py
    └── test_tronscan_integration.py
```

## API Endpoints

- **Mayan Bridge**: `https://price-api.mayan.finance/v3/quote`
- **Tronscan Balance**: `https://apilist.tronscanapi.com/api/account/resourcev2`

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run formatting and linting
5. Submit a pull request

## Support

For issues or questions, please open an issue on GitHub.