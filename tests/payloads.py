"""Verbatim TSB responses captured from the live service.

Keeping the payloads exactly as the service returned them means the suite fails
when the client stops understanding the real contract, rather than passing
against a hand written approximation.
"""

from __future__ import annotations

BASE_URL = "https://www.tsb.org.tr"

YEAR_LIST_PAYLOAD = {
    "HasError": False,
    "Message": "",
    "Result": [
        2026,
        2025,
        2024,
        2023,
        2022,
        2021,
        2020,
        2019,
        2018,
        2017,
        2016,
        2015,
        2014,
        2013,
        2012,
    ],
}

BRAND_LIST_PAYLOAD = {
    "HasError": False,
    "Message": "",
    "Result": [
        {"VehicleBrandId": 699, "Name": "ADRIA", "VehicleBrandCode": 0},
        {"VehicleBrandId": 605, "Name": "ALFA ROMEO", "VehicleBrandCode": 0},
        {"VehicleBrandId": 607, "Name": "AUDI", "VehicleBrandCode": 0},
        {"VehicleBrandId": 610, "Name": "BMW", "VehicleBrandCode": 0},
        {"VehicleBrandId": 617, "Name": "CITROEN", "VehicleBrandCode": 0},
    ],
}

MODEL_LIST_PAYLOAD = {
    "HasError": False,
    "Message": "",
    "Result": [
        {"VehicleModelId": 138934, "Name": "A3 ALLSTREET 35 TFSI 150 STRONIC FL"},
        {"VehicleModelId": 138935, "Name": "A3 SEDAN 35 TFSI 150 ADVANCED STRONIC PI FL"},
        {"VehicleModelId": 138933, "Name": "A3 SPORTBACK 35 TFSI 150 S LINE STRONIC PI FL"},
        {"VehicleModelId": 139651, "Name": "A5 AVANT 2.0 TDI QUATTRO 204 STRONIC"},
    ],
}

INSURANCE_DATA_PAYLOAD = {
    "HasError": False,
    "Message": "",
    "Result": {"VehicleBrandCode": 9, "VehicleModelCode": 1616, "Amount": 3695439},
}

MONTH_LIST_PAYLOAD = [
    {
        "MonthOrder": 1,
        "InsuranceUploads": None,
        "InsuranceDatas": None,
        "Name": "Ocak",
        "LanguageId": 1,
        "Language": None,
        "Id": 2,
    },
    {
        "MonthOrder": 2,
        "InsuranceUploads": None,
        "InsuranceDatas": None,
        "Name": "Şubat",
        "LanguageId": 1,
        "Language": None,
        "Id": 3,
    },
    {
        "MonthOrder": 3,
        "InsuranceUploads": None,
        "InsuranceDatas": None,
        "Name": "Mart",
        "LanguageId": 1,
        "Language": None,
        "Id": 4,
    },
    {
        "MonthOrder": 8,
        "InsuranceUploads": None,
        "InsuranceDatas": None,
        "Name": "Ağustos",
        "LanguageId": 1,
        "Language": None,
        "Id": 9,
    },
    {
        "MonthOrder": 10,
        "InsuranceUploads": None,
        "InsuranceDatas": None,
        "Name": "Ekim",
        "LanguageId": 1,
        "Language": None,
        "Id": 1,
    },
    {
        "MonthOrder": 12,
        "InsuranceUploads": None,
        "InsuranceDatas": None,
        "Name": "Aralık",
        "LanguageId": 1,
        "Language": None,
        "Id": 12,
    },
]

ARCHIVE_FILE_PAYLOAD = "/content/InsuranceExcelFiles/202408R4.xlsx"
