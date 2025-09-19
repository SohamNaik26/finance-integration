### Everclear API Integration - Execution Guide for Cursor

## Overview
This guide provides step-by-step execution instructions and Cursor prompts to integrate the Everclear scan API into your existing blockchain finance integration project.

Target: Add ETH balance history fetching from `https://scan.everclear.org/api/v2/addresses/{address}/coin-balance-history`.

Repository: [finance-integration](https://github.com/SohamNaik26/finance-integration)

## Prerequisites
- Current project is working (confirmed by recent outputs)
- Cursor AI IDE is set up
- Project files: `main_integration.py`, `example_usage.py`, `requirements.txt`

---

## Step 1: Analyze Current Project Structure

### Cursor Prompt 1
```text
Analyze my current main_integration.py file. I want to add a new integration for Everclear blockchain explorer API. 

Current integrations:
- Mayan Finance (cross-chain quotes)  
- TRON balances (multiple variations)

I need to add:
- Everclear balance history API: https://scan.everclear.org/api/v2/addresses/{address}/coin-balance-history
- Parameters: address, block_number (optional), items_count (1-100), page (for pagination)
- Focus only on ETH balance data
- Follow the same pattern as existing integrations

Show me where to add the new Pydantic models and functions, maintaining consistency with the current codebase structure.
```

---

## Step 2: Add Data Models

### Cursor Prompt 2
```text
Add new Pydantic models for Everclear integration to main_integration.py:

1. Input model: EverclearBalanceParams
   - address: str (required)
   - block_number: Optional[int] 
   - items_count: int (default=50, range 1-100)
   - page: Optional[int] (default=1, min=1)

2. Output model: EverclearBalanceRecord  
   - address: str
   - block_number: int
   - block_hash: str
   - transaction_hash: Optional[str]
   - balance_wei: str
   - balance_eth: float (convert from wei)
   - balance_change_wei: str  
   - balance_change_eth: float
   - timestamp: str
   - timestamp_iso: str
   - fetch_timestamp: str
   - source_api: str = "everclear_scan"
   - page: int
   - error: Optional[str] = None
   - error_type: Optional[str] = None

Follow the exact same pattern as MayanBridgeParams/MayanQuoteRecord and TronBalanceParams/TronBalanceRecord.
```

---

## Step 3: Implement Core Function

### Cursor Prompt 3
```text
Create the main async function `fetch_everclear_balance_history` in main_integration.py:

Requirements:
- Follow the same pattern as `fetch_mayan_quotes` and `fetch_tron_balances_simple`
- URL: https://scan.everclear.org/api/v2/addresses/{address}/coin-balance-history
- Support pagination with query parameters: block_number, items_count, page
- Handle API responses (items array)
- Convert Wei to ETH (divide by 1e18)
- Include error handling with try/catch blocks
- Add the same concurrent request limiting (max_concurrent parameter)
- Save to CSV functionality (save_to_csv parameter)
- Default CSV filename: "everclear_balance_history.csv"
- Same logging style with ✓ and ❌ symbols

Use the existing session management and error handling patterns from other functions.
```

---

## Step 4: Update CSV Output Logic

### Cursor Prompt 4
```text
Update the CSV handling for Everclear integration:

1. Add to the main CSV output functions to maintain the "exactly 2 CSV files per run" requirement
2. Since this is a new third integration, modify the logic to either:
   - Replace one of the existing default CSVs, OR  
   - Add it as an optional third CSV that can be enabled

3. Update the `output/` directory creation and file management
4. Follow the same pattern as mayan_bridge_quotes.csv and simple_tron_balances.csv

Maintain compatibility with existing CSV recreation behavior (no append, recreate on each run).
```

---

## Step 5: Add to Example Usage

### Cursor Prompt 5
```text
Update example_usage.py to include Everclear integration:

1. Add test addresses for Everclear (use the address from my example: 0xEFfAB7cCEBF63FbEFB4884964b12259d4374FaAa)
2. Add a few more sample addresses for testing
3. Include in the "Run Examples" option (choice 2)
4. Add to the summary statistics output
5. Add appropriate success/failure logging with the same format:
   ```
   🔍 Fetching Everclear Balance History...
      ✓ Created /path/to/output/everclear_balance_history.csv with X records
      ✓ Fetched X balance history records  
      ✓ Columns: X fields
      ✓ Sample address: 0xEFf...
      ✓ Balance: X.X ETH
      ✓ Data saved to everclear_balance_history.csv
   ```

Keep the same CLI menu structure (1-4 options).
```

---

## Step 6: Test Integration

### Cursor Prompt 6
```text
Help me add proper error handling and testing for the Everclear integration:

1. Add validation for Ethereum addresses (0x prefix, 42 characters)
2. Add rate limiting considerations (what's appropriate for scan.everclear.org?)
3. Add timeout handling for the requests
4. Test with the example address: 0xEFfAB7cCEBF63FbEFB4884964b12259d4374FaAa
5. Add pagination testing (fetch multiple pages if needed)

Include appropriate logging for debugging and maintain consistency with existing error handling patterns.
```

---

## Step 7: Documentation Update

### Cursor Prompt 7
```text
Update the project documentation to include Everclear integration:

1. Update the high-level overview comment at the top of main_integration.py
2. Add Everclear to the "Key features" section  
3. Update the data flow documentation
4. Add example usage patterns
5. Update the CSV output documentation to reflect the new integration
6. Add any API rate limiting or usage notes for Everclear

Maintain the same documentation style and format as existing integrations.
```

---

## Step 8: Final Testing & Validation

### Cursor Prompt 8
```text
Help me create a comprehensive test for the Everclear integration:

1. Create test parameters with:
   - Valid Ethereum addresses
   - Different block numbers
   - Different page sizes (10, 50, 100)
   - Pagination testing (multiple pages)

2. Validate the output:
   - CSV structure matches expected fields
   - Wei to ETH conversion is correct
   - Timestamps are properly formatted  
   - Error handling works for invalid addresses

3. Integration test with existing functions:
   - All three integrations run successfully
   - CSV files are created properly
   - No conflicts with existing functionality

Provide a test script or add to the "Run API Tests" option in example_usage.py.
```

---

## Expected Execution Flow
```text
🚀 Blockchain Data Integration Suite
==================================================
1. Run API Tests
2. Run Examples  
3. Run Both
4. Demonstrate CSV Updates
==================================================

=== Blockchain Data Integrations Example ===

🌉 Fetching Mayan Bridge Quotes...
   ✓ Created /path/to/output/mayan_bridge_quotes.csv with 2 records

🔗 Fetching TRON Account Balances (Simple Integration)...  
   ✓ Created /path/to/output/simple_tron_balances.csv with 2 records

🔍 Fetching Everclear Balance History...
   ✓ Created /path/to/output/everclear_balance_history.csv with X records
   ✓ Fetched X balance history records
   ✓ Sample address: 0xEFfAB7cCEBF63FbEFB4884964b12259d4374FaAa
   ✓ Balance: XXX.XX ETH
   
✅ Summary:
   - Mayan quotes: 2
   - TRON balances: 2  
   - Everclear balance history: X
```

---

## Notes for Cursor Usage
- Copy-paste each prompt individually into Cursor
- Wait for completion before moving to the next step
- Review the generated code before proceeding
- Test each step incrementally
- Maintain your existing working functionality

---

## Helpful Links
- Project repository: [finance-integration](https://github.com/SohamNaik26/finance-integration)
- Everclear balance history endpoint: `https://scan.everclear.org/api/v2/addresses/{address}/coin-balance-history`


