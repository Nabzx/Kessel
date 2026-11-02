# Cinematic design plan

## Tokens

- Space: #030506
- Carbon: #14191b
- Off-white: #eeece5
- Mineral amber: #d5ac6c
- Baseline red: #e66f60
- Trained green: #8fcaa5

Environment lighting adds restrained ice, sand, orbital, underground and abyss
hues. The base interface remains black and off-white. Space Grotesk carries
navigation and prose; JetBrains Mono is reserved for actual numerical data.
The custom vector wordmark has cut geometry rather than tracked default text.

## Layout

Welcome is centred: Earth, wordmark, start. Selection places the active
carousel on the left and a slightly larger rotating globe on the right. The
surface scene is full canvas, with one concise location/action panel. The
mine is a substantial rock cutaway on the left with six measures on the right.
The training viewer is a technical local simulation with observation geometry,
policy/action state, a small reward curve and accelerated checkpoint replay.
The page then scrolls into a training-to-onboard pipeline and exploded kit.

No corner brackets, fake terminal logs, decorative card grid, headline
highlight word or paragraphs over the opening Earth. Controls have one clear
purpose. The memorable element is the continuous geographic/cutaway journey.

## Story timing

Welcome 6 s; carousel 8 s; descent 7 s; surface 6 s; portal/cutaway reveal 4 s;
baseline mine 10 s; model glimpse 4 s; trained comparison 10 s; scroll hand-off
5 s. Total 60 s. These are presenter pacing cues, not forced auto-advance.

## Brief review

The Phase 9 left-hand headline and disconnected map window are replaced by the
approved centred opener and continuous scene. The old thin floating network is
replaced by rock mass and exposed working corridors. The mine remains overhead.
The learning explanation has its own optional technical space. Product copy
uses short labels; pricing and manual overrides are excluded. Review actual
browser captures at the welcome, carousel, cutaway, trained and learning stages.

## Maintainer review

The maintainer reviewed the working localhost experience and described the
direction as excellent. Requested corrections: fix the inverted Earth and
geographic labels, and smooth the trained-site transition with a more refined
technical treatment. These corrections are included in the final pass.

Earth bitmap resizing must preserve the default TextureLoader orientation:
Three.js ignores Texture.flipY for ImageBitmap, so the bitmap itself needs
imageOrientation: flipY. See the official
[ImageBitmapLoader documentation](https://threejs.org/docs/pages/ImageBitmapLoader.html).

The comparison uses a continuous scan across the rock mass, restrained floor
sampling, eased machine/route opacity, and a soft operations-panel hand-off.
There is no abrupt whole-mine wireframe toggle. The lighting for the kit is
prepared once as a local CubeUV asset.
