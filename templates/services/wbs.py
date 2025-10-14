
import pandas as pd
import pathlib

DEFAULT_WBS = [
    ("Prepare","Project Setup","Kickoff & logistics","Create shared channels/repo","PM"),
    ("Prepare","Access","Accounts & VPN","Secure access for engineers","PM"),
    ("Build","Horizon","Connection Servers","Build CS VMs (x{{count}})","ENG"),
    ("Build","UAG","Unified Access Gateways","Deploy UAGs (x{{count}})","ENG"),
    ("Build","TrueSSO","Enrollment Servers","Deploy Enrollment Servers (x{{count}})","ENG"),
    ("Build","App Volumes","Managers","Deploy AV Managers (x{{count}})","ENG"),
    ("Integrate","Certificates","PKI","Install server certs","ENG"),
    ("Integrate","Networking","F5/LB","VIPs, monitors, pools","NET"),
    ("Validate","Testing","Functional","Provision pool, login tests","QA"),
    ("Cutover","Go-Live","Phased rollout","Migrate users","PM"),
    ("KT","Handover","Docs & Training","Runbook & KT sessions","PM"),
]

def build_wbs(ctx: dict, outdir: pathlib.Path, fname: str) -> pathlib.Path:
    counts = ctx.get("horizon", {}).get("components", {})
    rows = []

    for phase, stream, task, desc, owner in DEFAULT_WBS:
        desc2 = desc.replace("{{count}}", str(counts.get("connection_servers", 1)))
        if "UAG" in stream:
            desc2 = desc.replace("{{count}}", str(counts.get("uag", 1)))
        if "TrueSSO" in stream:
            desc2 = desc.replace("{{count}}", str(counts.get("enrollment_servers", 1)))
        if "App Volumes" in stream:
            desc2 = desc.replace("{{count}}", str(counts.get("appvol_managers", 1)))

        rows.append({
            "Phase": phase,
            "Workstream": stream,
            "Task": task,
            "Description": desc2,
            "Owner": owner,
            "Depends On": "",
        })

    df = pd.DataFrame(rows)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / fname

    with pd.ExcelWriter(path, engine="xlsxwriter") as xw:
        df.to_excel(xw, index=False, sheet_name="WBS")
        ws = xw.sheets["WBS"]
        ws.autofilter(0, 0, df.shape[0], df.shape[1]-1)
        ws.set_column(0, 0, 14)
        ws.set_column(1, 1, 18)
        ws.set_column(2, 2, 28)
        ws.set_column(3, 3, 60)
        ws.set_column(4, 5, 14)

    return path
