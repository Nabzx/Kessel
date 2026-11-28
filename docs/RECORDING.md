# Recording and review handover

The default site is a concept visualisation. The numerical tools and recordings
are separate synthetic evidence. Keep source labels visible when recording or
editing. A successful conventional cycle does not establish learned planning.
The hybrid forecast includes explicitly known kinematics, events and accounting.

## Prepared routes

The [review page](phase-11/acceptance-review/index.html) supplies the retained
60-second core and 90-second technical storyboards, dated native footage,
matched-size stills and known failures. These are existing captures and timed
stills, not a newly completed browser recording. The main route is welcome,
descent, environment, surface, mine comparison, learning and proposed retrofit.
The technical route adds complete source-specific cycles and forecast limits.

For a new native walkthrough recording, use Chrome on the target M1 MacBook Pro.
Record the core route at 1440x900 with sparse narration following the storyboard.
Retain the browser/GPU identity, source commit and unedited capture. Separately
review 1365x768 and 1280x800 for clipping, machinery framing and control overlap.
Capture source switching, complete successful delivery and genuine failed cases
without cutting away their end states. Do not label the proposed kit as validated
hardware or authored savings as measured results.

The maintainer previously kept #351/#385 open and prohibited disruptive tab
automation. This preparation does not launch a browser, change tabs or start a
server. Real background/foreground behaviour and scene-backed readability still
require a deliberate manual session for #274. Do not replace that missing review
with synthetic visibility events or infer acceptance from an automated check.

## Offline numerical film

An additional film can be generated entirely from retained simulator states and
saved hybrid predictions. It renders the complete nominal evaluation cycle at
10 fps with next-state ground truth above its 0.1-second forecast, plus load and
delivery figures. It makes no simulator, model-training, browser or service calls.
It is an optional technical insert, not a replacement for the main walkthrough.

    PYTHONPATH=training training/.venv/bin/python scripts/render-forecast-film.py --output .local/forecast-film-v1

Requires the optional local matplotlib and ffmpeg tools. Uses the Agg renderer,
one encoding thread, at most 300 frames, 90 seconds and 16 MiB. Output must be a
new child of this repo's ignored `.local` directory. The film manifest pins the
evidence report and output hashes; the terminal still makes its ending reviewable.

## Acceptance record

For an agreed manual capture session, use the existing local server. If none is
running, the reviewer can deliberately run this from the repository root:

    python3 -m http.server 8091 --bind 127.0.0.1

Open `http://127.0.0.1:8091/` in the chosen Chrome window. Use 100% zoom and a
1440x900 content area, close DevTools and silence notifications. Load assets once,
then reset the route. Press Shift-Command-5, choose Record Selected Portion and
select the browser content. Under Options choose `.local/manual-recording` as
the destination, a five-second timer, no microphone for a silent insert and no
mouse-click indicators. Click Record and park the pointer.

| Target time | Capture |
| --- | --- |
| 0–5 s | Welcome and Kessel identity |
| 5–12 s | Descent and Underground selection |
| 12–20 s | Surface arrival and cutaway reveal |
| 20–44 s | Chosen complete reference cycle, including terminal delivery |
| 44–50 s | Learning/forecast source and its stated limitation |
| 50–58 s | Proposed retrofit kit and ending |

This is an editing target, not a newly verified unedited route duration. Capture
slower passages separately and retain complete success/failure endings. Trim the
application insert to at most 58 seconds without changing numerical outcomes.
Use the menu-bar Stop control. Check the saved file for readable source labels,
delivery and uncropped controls. Keep its original resolution and unedited copy.
Apple's [recorder instructions](https://support.apple.com/guide/mac-help/take-a-screenshot-or-screen-recording-mh26782/mac)
describe the available options. Stop only a server started for this session with
Control-C; leave existing services alone. No capture command is run by this work.

Record the actual reviewer, date, source commit, viewport, browser/GPU and specific
remaining defects in the issue. Keep visual judgement distinct from numerical
gates and targeted accessibility checks. #276 requires the complete real
walkthrough capture and explicit acceptance before release can be complete.

The retained [numerical film](phase-11/forecast-film/synthetic-forecast-comparison.mp4)
and [terminal still](phase-11/forecast-film/terminal-frame.png) are independently
checked by `python3 scripts/verify-forecast-film.py`, including encoded frame count
and duration. They remain separate from the uncompleted native browser capture.
