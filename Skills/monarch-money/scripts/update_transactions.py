#!/usr/bin/env python3
"""Update specific transactions with correct categories and merchant names."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from monarchmoney import MonarchMoney

# Transaction updates to make
UPDATES = [
    {
        "id": "228363413608231991",
        "merchant": "YouTube Premium",
        "category_id": "225122791379203427",  # Subscription
        "description": "YouTube Premium → Subscription"
    },
    {
        "id": "228363413608231992", 
        "merchant": "Airbnb",
        "category_id": "162777981853398774",  # Travel & Vacation
        "description": "Klarna (Airbnb) → Travel & Vacation"
    },
    {
        "id": "228363413608232002",
        "merchant": "Ground News",
        "category_id": "225122791379203427",  # Subscription
        "description": "Google Ground News → Subscription"
    },
    {
        "id": "228445219597612533",
        "merchant": "Target",
        "category_id": "225123032227674020",  # Baby formula
        "description": "Target → Baby formula (baby stuff)"
    },
]

async def main():
    mm = MonarchMoney()
    
    email = os.getenv("MONARCH_EMAIL")
    password = os.getenv("MONARCH_PASSWORD")
    mfa_secret = os.getenv("MONARCH_MFA_SECRET")
    
    print("Logging in to Monarch Money...")
    await mm.login(email, password, mfa_secret_key=mfa_secret)
    print("✓ Logged in\n")
    
    for update in UPDATES:
        print(f"Updating: {update['description']}")
        try:
            # Update category
            result = await mm.update_transaction(
                transaction_id=update["id"],
                category_id=update["category_id"]
            )
            print(f"  ✓ Category updated")
            
            # Update merchant name - try if supported
            try:
                await mm.update_transaction(
                    transaction_id=update["id"],
                    merchant_name=update["merchant"]
                )
                print(f"  ✓ Merchant renamed to '{update['merchant']}'")
            except Exception as e:
                print(f"  ⚠ Merchant rename not supported: {e}")
                
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        print()
    
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
