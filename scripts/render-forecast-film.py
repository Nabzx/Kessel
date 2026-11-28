"""Render a complete saved synthetic forecast comparison without a browser."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]


def render(output):
    output = output.resolve(); allowed = (ROOT/".local").resolve()
    if not output.is_relative_to(allowed) or output == allowed:
        raise ValueError("film output must be a new child of repo-local .local")
    if not shutil.which("ffmpeg"): raise RuntimeError("ffmpeg is required")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter
    from matplotlib.patches import Polygon, Rectangle
    import numpy as np
    from kessel_training.kinematics import footprints

    directory = ROOT/"docs/phase-11/structured-dynamics-evidence"
    inventory = json.loads((directory/"files.json").read_text())
    for name,digest in inventory.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest: raise ValueError("changed evidence: "+name)
    report = json.loads((directory/"report.json").read_text())
    episode, = [e for e in report["datasets"]["evaluation"]["episodes"] if e["family"] == "nominal"]
    with np.load(directory/"evaluation.npz",allow_pickle=False) as data: truth = data["next_state"][episode["start"]:episode["stop"]]
    with np.load(directory/"predictions-structured.npz",allow_pickle=False) as data: predicted = data["next_state"][episode["start"]:episode["stop"]]
    if len(truth) > 300 or len(truth) != len(predicted): raise ValueError("film exceeds 300-frame cap")
    output.mkdir(parents=True,exist_ok=False); started = time.monotonic()
    fig,axes = plt.subplots(2,1,figsize=(12,6.8),dpi=100,layout="constrained")
    fig.get_layout_engine().set(rect=(0,.045,1,.955))
    fig.suptitle("Recorded synthetic cycle | conventional planner + fitted linear feedback",fontsize=15)
    fig.set_facecolor("#f4f1e9"); images = []; vehicles = []; labels = []
    for ax,title,state in zip(axes,("Frozen simulator: next state","Hybrid world model: 0.1 s forecast"),(truth[0],predicted[0])):
        ax.set_title(title,loc="left",fontsize=13); ax.set(xlim=(-11,18),ylim=(-5,5),xlabel="metres",ylabel="metres")
        ax.set_aspect("equal"); ax.set_facecolor("#e7e2d6")
        ox,oy = state[79:81]
        images.append(ax.imshow(state[15:79].reshape(8,8).T,origin="lower",extent=(ox,ox+4,oy,oy+4),vmin=0,vmax=1.5,cmap="cividis"))
        ax.add_patch(Rectangle(state[88:90]-state[90:92],2*state[90],2*state[91],fill=False,edgecolor="#7058a3",linewidth=2))
        polygons = [Polygon(p,closed=True,facecolor=c,edgecolor="#26231d",linewidth=1) for p,c in zip(footprints(state[None,:3],state[None,4:7])[0],("#b7782b","#cf974e","#edc988"))]
        for polygon in polygons: ax.add_patch(polygon)
        vehicles.append(polygons); labels.append(ax.text(.01,.94,"",transform=ax.transAxes,fontsize=11,va="top",bbox={"facecolor":"white","alpha":.9,"edgecolor":"none"}))
    fig.text(.5,.012,"Saved predictions on recorded actions. Explicit kinematic/event/accounting priors. Not field validation.",ha="center",fontsize=10)
    writer = FFMpegWriter(fps=10,codec="libx264",bitrate=1600,extra_args=["-threads","1","-pix_fmt","yuv420p","-movflags","+faststart"])
    film = output/"synthetic-forecast-comparison.mp4"
    with writer.saving(fig,str(film),100):
        for i,(actual,forecast) in enumerate(zip(truth,predicted)):
            if time.monotonic()-started > 90: raise TimeoutError("film rendering exceeded 90 seconds")
            for state,image,polygons,label in zip((actual,forecast),images,vehicles,labels):
                image.set_data(state[15:79].reshape(8,8).T)
                for polygon,points in zip(polygons,footprints(state[None,:3],state[None,4:7])[0]): polygon.set_xy(points)
                label.set_text(f"{state[10]:4.1f} s   |   carried {state[7]:,.0f} kg   |   delivered {state[8]:,.0f} kg")
            writer.grab_frame()
            if i == len(truth)-1: fig.savefig(output/"terminal-frame.png",dpi=100)
    plt.close(fig)
    if film.stat().st_size > 16*1024**2: raise ValueError("film exceeds 16 MiB")
    manifest = {"kind":"recorded-synthetic-hybrid-forecast-film-v1","evidence_report_sha256":hashlib.sha256((directory/"report.json").read_bytes()).hexdigest(),
                "renderer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"matplotlib_version":matplotlib.__version__,
                "episode":episode,"frames":len(truth),"fps":10,"duration_s":len(truth)/10,"render_wall_s":time.monotonic()-started,
                "source":"recorded synthetic comparison, not a new browser walkthrough capture","manual_visual_acceptance":"open","publication":"not_performed",
                "files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}}
    (output/"film.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"output":str(output.relative_to(ROOT)),"frames":len(truth),"duration_s":manifest["duration_s"],"render_wall_s":manifest["render_wall_s"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output",required=True,type=Path)
    render(parser.parse_args().output)
