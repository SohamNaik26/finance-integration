# 🔑 API Key Setup Guide

This guide explains how to obtain and configure API keys for the blockchain data integrations.

## 📋 API Requirements Summary

| Service           | API Key Required | Free Tier | Rate Limits |
| ----------------- | ---------------- | --------- | ----------- |
| **Mayan Finance** | ❌ No            | ✅ Yes    | Unknown     |
| **Tronscan**      | ✅ Yes           | ✅ Yes    | Unknown     |

---

## 🌉 Mayan Finance API

### ✅ **No API Key Required**

- **Status**: Free to use without authentication
- **Access**: Direct API calls work immediately
- **Rate Limits**: Unknown, but generally permissive
- **Documentation**: [Mayan Finance](https://mayan.finance/)

### Usage

```python
from mayan_bridge_integration import fetch_mayan_quotes, MayanBridgeParams

# Works without any API key
params = [MayanBridgeParams(
    from_chain="ethereum",
    to_chain="solana",
    from_token="0x0000000000000000000000000000000000000000",
    to_token="0x0000000000000000000000000000000000000000",
    amount_in=1.0
)]

df = await fetch_mayan_quotes(params)
```

---

## 🔍 Tronscan API

### ✅ **API Key Required**

- **Status**: Free but requires registration
- **Access**: Must obtain API key from Tronscan
- **Rate Limits**: Unknown, but reasonable for normal use
- **Documentation**: [Tronscan API Docs](https://docs.tronscan.org/)

### Step 1: Get Your API Key

1. **Visit Tronscan**

   - Go to [https://tronscan.org/](https://tronscan.org/)
   - Create an account or log in

2. **Navigate to API Keys**

   - After logging in, go to the API Keys section
   - Look for "API Keys" or "Developer" section in your account

3. **Generate New API Key**

   - Click "Add" or "Create New API Key"
   - Provide a name for your application (e.g., "Finance Integration")
   - Configure security settings if desired
   - Copy the generated API key

4. **Secure Your API Key**
   - Store it securely (never commit to version control)
   - Use environment variables for production

### Step 2: Configure API Key

#### Option A: Environment Variable (Recommended)

```bash
# Set environment variable
export TRONSCAN_API_KEY="your_api_key_here"

# Or add to .env file
echo "TRONSCAN_API_KEY=your_api_key_here" >> .env
```

#### Option B: Direct Parameter

```python
from tronscan_balance_integration import fetch_tronscan_balances

addresses = ["TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg"]
df = await fetch_tronscan_balances(addresses, api_key="your_api_key_here")
```

### Step 3: Test Your Setup

```python
import asyncio
from tronscan_balance_integration import fetch_tronscan_balances

async def test_tronscan():
    addresses = ["TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg"]

    try:
        df = await fetch_tronscan_balances(addresses)
        if 'error' in df.columns and df['error'].notna().any():
            print("❌ API key not working or invalid")
            print("Error:", df[df['error'].notna()]['error'].iloc[0])
        else:
            print("✅ API key working correctly!")
            print(f"Fetched {len(df)} records")
    except Exception as e:
        print(f"❌ Error: {e}")

# Run test
asyncio.run(test_tronscan())
```

---

## 🛠️ Complete Setup Example

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file:

```bash
# .env file
TRONSCAN_API_KEY=your_tronscan_api_key_here
```

### 3. Load Environment Variables

```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file

# Now your integrations will automatically use the API key
```

### 4. Run Both Integrations

```python
import asyncio
from mayan_bridge_integration import fetch_mayan_quotes, MayanBridgeParams
from tronscan_balance_integration import fetch_tronscan_balances

async def run_all_integrations():
    # Mayan Bridge (no API key needed)
    mayan_params = [MayanBridgeParams(
        from_chain="ethereum",
        to_chain="solana",
        from_token="0x0000000000000000000000000000000000000000",
        to_token="0x0000000000000000000000000000000000000000",
        amount_in=1.0
    )]
    mayan_df = await fetch_mayan_quotes(mayan_params)
    print(f"Mayan: {len(mayan_df)} records")

    # Tronscan (API key required)
    tron_addresses = ["TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg"]
    tron_df = await fetch_tronscan_balances(tron_addresses)
    print(f"Tronscan: {len(tron_df)} records")

asyncio.run(run_all_integrations())
```

---

## 🔒 Security Best Practices

### 1. **Never Commit API Keys**

```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
```

### 2. **Use Environment Variables**

```python
import os
api_key = os.getenv('TRONSCAN_API_KEY')
if not api_key:
    raise ValueError("TRONSCAN_API_KEY environment variable not set")
```

### 3. **Rotate Keys Regularly**

- Regenerate API keys periodically
- Monitor usage for anomalies
- Revoke unused keys

### 4. **Rate Limiting**

```python
import asyncio
import time

async def rate_limited_request():
    # Add delays between requests if needed
    await asyncio.sleep(0.1)  # 100ms delay
    # Make your API call
```

---

## 🚨 Troubleshooting

### Common Issues

#### 1. **Tronscan 401 Unauthorized**

```
Error: HTTP 401: Client error '401 Unauthorized'
```

**Solution**:

- Check if API key is set correctly
- Verify API key is valid and active
- Ensure API key has proper permissions

#### 2. **Environment Variable Not Found**

```
Error: TRONSCAN_API_KEY environment variable not set
```

**Solution**:

- Set the environment variable: `export TRONSCAN_API_KEY="your_key"`
- Or pass API key directly to the function

#### 3. **Rate Limiting**

```
Error: HTTP 429: Too Many Requests
```

**Solution**:

- Add delays between requests
- Implement exponential backoff
- Check rate limits in API documentation

### Testing Your Setup

Run this test script to verify everything works:

```python
#!/usr/bin/env python3
"""
API Key Test Script
Run this to verify your API keys are working correctly.
"""

import asyncio
import os
from mayan_bridge_integration import fetch_mayan_quotes, MayanBridgeParams
from tronscan_balance_integration import fetch_tronscan_balances

async def test_apis():
    print("🔍 Testing API Integrations...\n")

    # Test Mayan Finance (no API key needed)
    print("1. Testing Mayan Finance API...")
    try:
        mayan_params = [MayanBridgeParams(
            from_chain="ethereum",
            to_chain="solana",
            from_token="0x0000000000000000000000000000000000000000",
            to_token="0x0000000000000000000000000000000000000000",
            amount_in=1.0
        )]
        mayan_df = await fetch_mayan_quotes(mayan_params)
        print("   ✅ Mayan Finance API working")
    except Exception as e:
        print(f"   ❌ Mayan Finance API error: {e}")

    # Test Tronscan (API key required)
    print("\n2. Testing Tronscan API...")
    api_key = os.getenv('TRONSCAN_API_KEY')
    if not api_key:
        print("   ⚠️  TRONSCAN_API_KEY not set - skipping test")
        print("   💡 Set it with: export TRONSCAN_API_KEY='your_key'")
    else:
        try:
            tron_addresses = ["TAcJ8gRyo16rpk9qzefMUi3FL7WDjBTMrg"]
            tron_df = await fetch_tronscan_balances(tron_addresses)
            if 'error' in tron_df.columns and tron_df['error'].notna().any():
                print("   ❌ Tronscan API key invalid or expired")
                print(f"   Error: {tron_df[df['error'].notna()]['error'].iloc[0]}")
            else:
                print("   ✅ Tronscan API working")
        except Exception as e:
            print(f"   ❌ Tronscan API error: {e}")

    print("\n🎉 API testing complete!")

if __name__ == "__main__":
    asyncio.run(test_apis())
```

---

## 📞 Support

- **Mayan Finance**: [https://mayan.finance/](https://mayan.finance/)
- **Tronscan**: [https://tronscan.org/](https://tronscan.org/)
- **Tronscan API Docs**: [https://docs.tronscan.org/](https://docs.tronscan.org/)

For issues with this integration code, check the error messages and ensure your API keys are correctly configured.
