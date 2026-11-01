#!/usr/bin/env python3
"""Fetch global tin and tantalum occurrences from the USGS MRDS service.

The service is a historical catalogue, not a current operating-mine list.
Run this script when intentionally refreshing data/mineral-deposits.json.
It uses only the Python standard library.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SERVICE = (
    "https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/"
    "Mineral_Resources_Data_System_MRDS_Compact_Version/FeatureServer/0/query"
)
WHERE = "CODE_LIST LIKE '% SN%' OR CODE_LIST LIKE '% TA%'"
OUT_FIELDS = "OBJECTID,DEP_ID,SITE_NAME,DEV_STAT,URL,CODE_LIST,Grade"
PAGE_SIZE = 2000
OUTPUT = Path(__file__).with_name("mineral-deposits.json")


def query_service(params):
    url = f"{SERVICE}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "Kessel concept visualisation data refresh"})
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"MRDS service error: {payload['error']}")
    return payload


def fetch_features():
    count_result = query_service({"where": WHERE, "returnCountOnly": "true", "f": "json"})
    expected_count = count_result["count"]
    features = []
    for offset in range(0, expected_count, PAGE_SIZE):
        page = query_service({
            "where": WHERE,
            "outFields": OUT_FIELDS,
            "returnGeometry": "true",
            "outSR": "4326",
            "orderByFields": "OBJECTID ASC",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": "json",
        })
        features.extend(page.get("features", []))
    if len(features) < expected_count:
        raise RuntimeError(f"Expected {expected_count} MRDS records, received {len(features)}")
    return expected_count, features


def normalise_marker(feature):
    attributes = feature.get("attributes", {})
    geometry = feature.get("geometry") or {}
    longitude = geometry.get("x")
    latitude = geometry.get("y")
    if longitude is None or latitude is None:
        return None
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        return None

    codes = set((attributes.get("CODE_LIST") or "").upper().split())
    commodities = []
    if "SN" in codes:
        commodities.append("tin")
    if "TA" in codes:
        commodities.append("tantalum")
    if not commodities:
        return None

    deposit_id = str(attributes.get("DEP_ID") or "").strip()
    if not deposit_id:
        return None
    return {
        "id": deposit_id,
        "name": (attributes.get("SITE_NAME") or "").strip() or "Unnamed occurrence",
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "commodities": commodities,
        "grade": (attributes.get("Grade") or "").strip() or None,
        "record_url": (attributes.get("URL") or "").strip()
        or f"https://mrdata.usgs.gov/mrds/show-mrds.php?dep_id={deposit_id}",
    }


def main():
    service_count, features = fetch_features()
    markers = [marker for feature in features if (marker := normalise_marker(feature))]
    markers.sort(key=lambda marker: marker["id"])
    result = {
        "meta": {
            "source": "USGS Mineral Resources Data System Compact Version",
            "source_url": "https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Mineral_Resources_Data_System_MRDS_Compact_Version/FeatureServer/0",
            "record_url": "https://mrdata.usgs.gov/mrds/",
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "service_records": service_count,
            "marker_records": len(markers),
            "commodity_counts": {
                "tin": sum("tin" in marker["commodities"] for marker in markers),
                "tantalum": sum("tantalum" in marker["commodities"] for marker in markers),
            },
            "query": WHERE,
            "caveat": "Historical occurrences, not a current operating-mine inventory. USGS reports that systematic MRDS updates ceased in 2011 and operational attributes are out of date.",
        },
        "markers": markers,
    }
    OUTPUT.write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(markers)} markers from {service_count} matching service records to {OUTPUT}")


if __name__ == "__main__":
    main()
