"""Tests for provider balance lookups (admin page)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.billing import (
    PROVIDER_CATALOG,
    get_vendor_balances,
)


def _resp(json_obj, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_obj
    r.raise_for_status = MagicMock()
    return r


class TestVendorBalances:
    @patch("app.services.billing.httpx.get")
    @patch("app.services.billing.settings")
    def test_stability_success(self, mock_settings, mock_get):
        mock_settings.STABILITY_API_KEY = "k"
        mock_settings.TOPVIEW_API_KEY = ""
        mock_settings.TOPVIEW_UID = ""
        mock_settings.WAVESPEED_API_KEY = ""
        mock_get.return_value = _resp({"credits": 922.4})

        balances = get_vendor_balances()
        assert balances["stability"] == {
            "available": True, "balance": 922.4, "unit": "credits", "error": None,
        }

    @patch("app.services.billing.httpx.get")
    @patch("app.services.billing.settings")
    def test_wavespeed_nested_balance_usd(self, mock_settings, mock_get):
        mock_settings.STABILITY_API_KEY = ""
        mock_settings.TOPVIEW_API_KEY = ""
        mock_settings.TOPVIEW_UID = ""
        mock_settings.WAVESPEED_API_KEY = "k"
        mock_get.return_value = _resp({"data": {"balance": 12.5}})

        balances = get_vendor_balances()
        assert balances["wavespeed"]["balance"] == 12.5
        assert balances["wavespeed"]["unit"] == "USD"

    @patch("app.services.billing.settings")
    def test_missing_key_reports_unavailable(self, mock_settings):
        mock_settings.STABILITY_API_KEY = ""
        mock_settings.TOPVIEW_API_KEY = ""
        mock_settings.TOPVIEW_UID = ""
        mock_settings.WAVESPEED_API_KEY = ""
        balances = get_vendor_balances()
        assert balances["stability"]["available"] is False
        assert "STABILITY_API_KEY" in balances["stability"]["error"]

    @patch("app.services.billing.settings")
    def test_google_has_no_balance_api(self, mock_settings):
        mock_settings.STABILITY_API_KEY = ""
        mock_settings.TOPVIEW_API_KEY = ""
        mock_settings.TOPVIEW_UID = ""
        mock_settings.WAVESPEED_API_KEY = ""
        balances = get_vendor_balances()
        assert balances["google"]["available"] is False
        assert "Cloud Console" in balances["google"]["error"]


class TestProviderCatalog:
    def test_every_image_provider_is_catalogued(self):
        from app.services.image.providers import IMAGE_PROVIDERS

        missing = [k for k in IMAGE_PROVIDERS if k not in PROVIDER_CATALOG]
        assert missing == [], f"Uncatalogued image providers: {missing}"
