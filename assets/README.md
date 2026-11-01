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
