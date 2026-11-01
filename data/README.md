# Public mineral deposit markers

`mineral-deposits.json` is generated from the U.S. Geological Survey's global
Mineral Resources Data System (MRDS) Compact Version feature service. The
generator queries the documented `CODE_LIST` field for the tin (`SN`) and
tantalum (`TA`) commodity codes, pages through the matching records, keeps
valid WGS84 coordinates, and emits a compact file for the globe.

Refresh the committed snapshot deliberately with:

```sh
python3 data/generate_deposit_markers.py
```

The service's matching-record count, generated marker count, retrieval time,
and per-commodity counts are recorded in the JSON metadata. Coordinates are
rounded to four decimal places for display. Each point retains its MRDS record
link.

MRDS is a historical mineral occurrence catalogue, not an inventory of
currently operating mines. USGS says that systematic updates ceased in 2011
and operational fields are out of date. The globe labels these as historical
deposit markers. The Rutongo marker is a separate target from the mine
location in `mission.json`; it does not show a concession boundary. No public
boundary was found in the research for #140.

Sources: [USGS MRDS](https://mrdata.usgs.gov/mrds/) and the
[MRDS Compact Version feature service](https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Mineral_Resources_Data_System_MRDS_Compact_Version/FeatureServer/0).
