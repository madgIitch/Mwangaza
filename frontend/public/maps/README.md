# IGAD administrative boundary assets

These local GeoJSON files provide a neutral ADM1 reference layer for Region Explorer. They do not contain drought observations and must not be coloured as assessed unless the API supplies a matching unit-level score.

- Source: [geoBoundaries gbOpen](https://www.geoboundaries.org/)
- API: `https://www.geoboundaries.org/api/current/gbOpen/{ISO3}/ADM1/`
- Pinned source revision: `wmgeolab/geoBoundaries@9469f09`
- Files: simplified ADM1 boundaries for DJI, ERI, ETH, KEN, SDN, SOM, SSD and UGA
- Processing: coordinates rounded and rings simplified with `frontend/scripts/simplify-boundary.mjs`; administrative names, ISO codes and boundary IDs retained

Licensing and source-year metadata vary by country and are published by the geoBoundaries API. The application attribution deliberately identifies geoBoundaries rather than implying that these shapes originate from Google Earth Engine or IGAD.
