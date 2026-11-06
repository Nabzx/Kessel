# Earth imagery

`earth-blue-marble-july.jpg` is NASA's July Blue Marble: Next Generation
global base map (5,400 x 2,700 pixels, 8 km per pixel). Source:
[NASA Earth Observatory](https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/)
and [original JPEG](https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-base/july/world.200407.3x5400x2700.jpg).

The image is used as the diffuse texture for the opening Earth. NASA imagery
is not endorsed as a Kessel product. NASA's media use guidance is at
[NASA media usage guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/).

`earth-black-marble-2016.jpg` is NASA's 2016 global grayscale Black Marble
night-lights composite at 3,600 x 1,800 pixels. It is a historical composite,
not a live view. Source: [NASA Earth at Night maps](https://science.nasa.gov/earth/earth-observatory/earth-at-night/maps/).

`earth-clouds.jpg` is NASA's Blue Marble cloud map at 2,048 x 1,024 pixels.
It is a static composite. Source: [NASA Blue Marble clouds](https://visibleearth.nasa.gov/view.php?id=57747)
and [original JPEG](https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57747/cloud_combined_2048.jpg).

The three globe textures total 2,812,832 bytes (2.68 MiB) on disk. The first
view also downloads the small HTML, CSS, and JavaScript files. The Three.js
library is served separately by the existing CDN import map.

## Rutongo surface tile

`rutongo/satellite-2026-08-14.webp` is a 1,024 x 1,024 true-colour crop of
Sentinel-2B L2A scene `S2B_35MRU_20260814_0_L2A`, acquired on 14 August 2026.
The STAC scene reports 0.004031 cloud fraction. It was reprojected to UTM 35S
(EPSG:32735), cropped to 4,096 x 4,096 metres around the Rutongo target, and
resampled from the scene's 10 m visual asset. `rutongo/elevation-30m-4km.png`
is the corresponding 256 x 256 height field, resampled from the Copernicus
GLO-30 DSM tile `Copernicus_DSM_COG_10_S02_00_E030_00_DEM`. The encoded range
maps linearly to 1,468.55-1,897.49 m above sea level for the Three.js terrain
mesh. The DSM includes buildings, vegetation, and other surface features; it
is not a bare-earth terrain model.

The portal, service access road, sheds, and stockpile drawn over the crop are
scripted illustrative props. [Trinity Metals](https://trinity-metals.com/en/projects/rutongo-mine)
identifies Rutongo as six underground mines, but the public sources reviewed do not provide an as-built
surface plan or verified portal coordinate. The map layer metadata exposed by
the Rwanda government does not establish a redistributable portal dataset.
The scene labels this layout as illustrative.

The image and height field are derived crops and are loaded after the visitor
selects Underground. Combined size: 157,798 bytes before HTTP compression.
Regenerate them with `python3 data/build_rutongo_surface.py` after installing
Rasterio, NumPy, and Pillow in the local Python environment.
The Sentinel source is [Earth Search STAC](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_35MRU_20260814_0_L2A)
and the [public COG archive](https://registry.opendata.aws/sentinel-2-l2a-cogs/).
The elevation source is the [Copernicus DEM public COG archive](https://registry.opendata.aws/copernicus-dem/).
The respective licences permit redistribution with attribution. On-screen
credit: “Contains modified Copernicus Sentinel data 2026” and “produced using
Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space
GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all
rights reserved.” The official [Sentinel data notice](https://cds.climate.copernicus.eu/licences/ec-sentinel)
and [Copernicus DEM notice](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)
are documented there.

## Original haul truck and mine assets

`models/haul-truck.json` defines an original Kessel vehicle. Geometry, wheel tread, contact shadow, lamps,
identification plate and articulated dump bed are assembled by `js/vehicle.js`.
The original geometry is copyright Nabil Shah / Kessel under the repository
licence. It is not a manufacturer model or a Rutongo vehicle record. The
published compact-truck envelope remains the dimensional reference. Distant
vehicles use a silhouette with the same envelope; the full rig appears during
inspection. Initial-pose physical mesh bounds are checked without the shadow.

The loading scene uses the existing
[Excavator 3d Rigging asset and CC BY 4.0 credit](models/excavator/README.md).
Its geometry is normalised and its documented boom and bucket joints are
animated. The loading chamber and placement are illustrative. The
[Poly Haven material sets](textures/README.md) supply wall, mud and ore diffuse
maps, with normal maps enabled on desktop.

## Historical Phase 9 Google satellite view

The historical Phase 9 surface stage could display an embedded Google Maps satellite map of the
Rutongo area. Google renders the imagery and provider attributions in the
iframe; they remain visible and unobscured. No Google tiles, screenshots or
map imagery are bundled as a terrain texture. The local Copernicus model is
independently selectable. The map requires an internet connection; open the
mission with `?offline=1` to use only the local assets.

[Google's map sharing and embedding instructions](https://support.google.com/maps/answer/7101463).

## Local rendering dependencies

Three.js 0.160.0, RoundedBoxGeometry, GLTFLoader and BufferGeometryUtils are
served from `vendor/`, retaining the
[Three.js MIT licence](vendor/THREE-LICENSE.txt). They were downloaded from
the matching version on unpkg. The vendored files are unchanged.

Latin subsets of Space Grotesk and JetBrains Mono are served from `fonts/`.
They were fetched through Google Fonts on 1 November 2026. Their OFL notices
are retained as `fonts/SPACE-GROTESK-OFL.txt` and
`fonts/JETBRAINS-MONO-OFL.txt`. Font and library transfers are reported
separately from Kessel mission assets in the verification report.

## Phase 10 original assets

`brand/kessel-wordmark.svg` is an original Kessel wordmark by Nabil Shah.
`models/kessel-loader.json` defines the original articulated training loader,
built by `js/loader-stage.js`. It uses the public compact
[Sandvik LH203 envelope](https://www.mining.sandvik/en/products/equipment/loaders/lh203-underground-lhd/)
as a reference, not manufacturer geometry or branding. Original loader,
surface props, cutaway, learning visualisations, studio reflection map and
proposed kit geometry are copyright Nabil Shah / Kessel under the repository
licence. No extra third-party geometry or texture is introduced in Phase 10.

The current surface uses local NASA/Copernicus geographic context and authored
foreground detail in one Three.js renderer. No Google imagery is bundled or
embedded by the current experience. Retained Poly Haven material sets and the
CC BY 4.0 excavator remain credited above and in the in-app Sources dialog.

`lighting/kit-studio.bin` is original Kessel studio illumination baked from
six procedural canvas faces into a 384 x 512 RGBA half-float CubeUV texture.
This keeps reflection prefiltering out of the live presentation. It contains
no third-party environment imagery.

## Phase 11 visual materials and orbital geometry

`materials/manifest.json` identifies the cleared Poly Haven Rock Face 03
(Dario Barresi and Rico Cilliers) and Dark Rock 02 (Amal Kumar) derivatives.
`materials/surface-manifest.json` identifies Aerial Grass Rock (Rob Tuytel).
All are [CC0](https://polyhaven.com/license). Diffuse maps are sRGB; OpenGL
normal, AO and roughness maps are linear. Fine maps are bounded at 512 px;
colour maps remain 1K. Each manifest retains source/derivative hashes, transfer
sizes, physical repeat scale and the preparation command. Source rock JPEGs
remain in the isolated look-development directory. The grass sources come
from the recorded official download URLs and are processed outside the site.

`models/iss/iss.glb` is a simplified derivative of the
[NASA ISS model](https://science.nasa.gov/resource/international-space-station-3d-model/),
credited to NASA / Visualization Technology Applications and Development
(VTAD). The [NASA media guidance](https://www.nasa.gov/nasa-brand-center/images-and-media/)
applies. No endorsement is implied. All source textures and markings are
removed. The derivative is a decorative silhouette, not an accurate scale or
orbital catalogue. The adjacent manifest records the source hash, 6,068
triangles, 100,116-byte derivative and conversion. Run `scripts/prepare-orbit.mjs`
with isolated glTF Transform 4.4.0 tooling and the original source GLB.
The existing excavator source and rig remain unchanged.

The site uses original, capped synthetic rock geometry and original ventilation,
yard props and proposed kit details. These are illustrative geometry under the
repository licence, not a reconstruction or scan of Rutongo's workings.
