"""Prepare locally served reference previews from individually cleared source photos.

Usage: python scripts/prepare-environment-previews.py <download directory>
Requires isolated Pillow 13.0.0. No remote requests or image generation.
"""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image, ImageOps
ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
 dict(id='glacier',source='glacier.jpg',page='https://science.nasa.gov/photojournal/retreat-of-greenlands-jakobshavn-isbrae-glacier/',url='https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia26/pia26117/PIA26117.jpg',credit='NASA/USGS',subject='Jakobshavn Isbrae, Greenland; Landsat 8, 2022',notice='NASA/USGS government imagery; individual record credits NASA/USGS. NASA media guidance applies; no endorsement.',focal=[.5,.5]),
 dict(id='desert',source='desert-original.jpg',page='https://science.nasa.gov/earth/earth-observatory/dunes-of-the-grand-erg-oriental-87798/',url='https://assets.science.nasa.gov/content/dam/science/esd/eo/images/imagerecords/87000/87798/iss046e048626_lrg.jpg',credit='Earth Science and Remote Sensing Unit, NASA Johnson Space Center',subject='Grand Erg Oriental, Algeria; ISS046-E-48626',notice='NASA astronaut photography. Individual record credits NASA/JSC; acknowledge the Earth Science and Remote Sensing Unit. No endorsement.',focal=[.5,.5]),
 dict(id='space',source='space.jpg',page='https://science.nasa.gov/resource/apollo-8s-iconic-earthrise/',url='https://assets.science.nasa.gov/content/dam/science/psd/solar/2023/09/a/as08-14-2383.jpg',credit='NASA/Bill Anders',subject='Apollo 8 Earthrise; 24 December 1968',notice='NASA astronaut photograph; individual record credits NASA/Bill Anders. NASA media guidance applies; no endorsement.',focal=[.5,.8]),
 dict(id='deep-sea',source='sea.jpg',page='https://oceanexplorer.noaa.gov/multimedia/explorations-ex2405-ex2406-learning-at-sea-1605activevent/',url='https://oceanexplorer.noaa.gov/wp-content/uploads/2024/10/1605activevent-hires.jpg',credit='NOAA Ocean Exploration, 2016 Deepwater Exploration of the Marianas',subject='Active hydrothermal vent, Marianas',notice='NOAA public-domain media, no copyright exception on this individual record. Retain the specified credit. No endorsement.',focal=[.5,.5]),
 dict(id='underground',source='mine.jpg',page='https://wwwn.cdc.gov/phil/Details.aspx?pid=19314',url='https://wwwn.cdc.gov/phil/PHIL_Images/19314/19314_lores.jpg',credit='CDC/NIOSH; Chad Hutson, 2013; PHIL 19314',subject='NIOSH research coal mine, Pennsylvania, United States; not Rutongo',notice='The individual PHIL record identifies public-domain use with CDC/photographer attribution and CDC as the free source. No deployment or endorsement is implied.',focal=[.5,.55]),
]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 out=ROOT/'assets/environments';out.mkdir(exist_ok=True);records=[]
 for spec in SOURCES:
  source=Path(sys.argv[1])/spec['source'];image=ImageOps.exif_transpose(Image.open(source)).convert('RGB');original=image.size
  target=out/(spec['id']+'.webp');thumb=ImageOps.fit(image,(768,432),Image.Resampling.LANCZOS,centering=tuple(spec['focal']));thumb.save(target,format='WEBP',quality=84,method=6)
  records.append({**spec,'path':str(target.relative_to(ROOT)),'source_dimensions':original,'source_sha256':sha(source),'source_bytes':source.stat().st_size,'sha256':sha(target),'bytes':target.stat().st_size,'dimensions':[768,432],'colour_space':'srgb','operation':'EXIF orientation, rectangular 16:9 crop, Lanczos resize, WebP quality 84; no content synthesis','representative':True})
 manifest={'date':'2026-11-07','generator':'Pillow 13.0.0; scripts/prepare-environment-previews.py','scope':'Reference environment photography. Underground is a Pennsylvania research mine, not a photo of Rutongo. Not evidence of a deployment.','total_bytes':sum(r['bytes'] for r in records),'images':records}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(manifest['total_bytes'],'bytes')
if __name__=='__main__':main()
