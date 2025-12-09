"""Receipt validation for Apple IAP and Google Play.

This module provides classes for validating in-app purchase receipts
from Apple and Google, mapping product IDs to tariff IDs, and extracting
purchase information.
"""

import os
from datetime import datetime
from typing import ClassVar, Dict, Optional

import requests


class IapValidator:
    """Validates receipts from Apple IAP and Google Play."""

    # Apple constants
    APPLE_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
    APPLE_PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"

    @staticmethod
    def validate_apple_receipt(receipt: str, bundle_id: str) -> Optional[Dict]:
        """Validate an Apple IAP receipt.

        Args:
            receipt: Base64-encoded receipt data from the client
            bundle_id: Bundle ID of the app (e.g., "com.example.vpn")

        Returns:
            Dict with keys: transaction_id, product_id, purchase_date, expiry_date, is_valid
            None if validation fails

        """
        url = os.getenv("APPLE_RECEIPT_URL", IapValidator.APPLE_SANDBOX_URL)

        payload = {
            "receipt-data": receipt,
            "password": os.getenv("APPLE_APP_SECRET", ""),
            "exclude-old-transactions": False,
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != 0:
                return None  # Receipt invalid

            # Extract latest transaction
            receipt_info = data.get("latest_receipt_info") or data.get("receipt", {}).get(
                "in_app", []
            )

            if not receipt_info:
                return None

            latest = receipt_info[-1] if isinstance(receipt_info, list) else receipt_info

            purchase_date_ms = int(latest.get("purchase_date_ms", 0))
            expires_date_ms = int(latest.get("expires_date_ms", 0))

            return {
                "transaction_id": latest.get("transaction_id"),
                "product_id": latest.get("product_id"),
                "purchase_date": datetime.fromtimestamp(purchase_date_ms / 1000),
                "expiry_date": (
                    datetime.fromtimestamp(expires_date_ms / 1000) if expires_date_ms else None
                ),
                "is_valid": True,
            }
        except Exception as e:
            print(f"Apple receipt validation error: {e}")
            return None

    @staticmethod
    def validate_google_receipt(package_name: str, product_id: str, token: str) -> Optional[Dict]:
        """Validate a Google Play receipt.

        Args:
            package_name: Package name of the app
            product_id: Product ID from the purchase
            token: Purchase token from the client

        Returns:
            Dict with purchase information or None if validation fails

        Note:
            Requires Google Play service account credentials in environment
            or as a JSON file.

        """
        # Implement Google Play API validation
        # https://developers.google.com/android-publisher/api-ref/rest/v3/purchases.products/get
        # Requires: oauth2 service account credentials

        # Placeholder for now
        return None


class ProductIdToTariffMapper:
    """Maps product IDs to tariff IDs and provides tariff information."""

    # Mapping of product IDs to tariff IDs
    # This should ideally come from the database, but for now we use a static mapping
    MAPPING: ClassVar = {
        "com.example.vpn.monthly": 1,  # 30 дней
        "com.example.vpn.annual": 2,  # 365 дней
        "com.example.vpn.lifetime": 3,  # Lifetime
    }

    # Duration in days for each tariff
    DURATION_MAPPING: ClassVar = {
        1: 30,  # Monthly
        2: 365,  # Annual
        3: 36500,  # Lifetime (~100 years)
    }

    @staticmethod
    def get_tariff_id(product_id: str) -> Optional[int]:
        """Get tariff ID from product ID.

        Args:
            product_id: Product ID from IAP purchase

        Returns:
            Tariff ID or None if product_id is not recognized

        """
        return ProductIdToTariffMapper.MAPPING.get(product_id)

    @staticmethod
    def get_duration_days(tariff_id: int) -> int:
        """Get subscription duration in days for a tariff.

        Args:
            tariff_id: Tariff ID from database

        Returns:
            Duration in days

        """
        return ProductIdToTariffMapper.DURATION_MAPPING.get(tariff_id, 0)

    @staticmethod
    def get_product_ids() -> list:
        """Get all supported product IDs.

        Returns:
            List of product IDs

        """
        return list(ProductIdToTariffMapper.MAPPING.keys())
