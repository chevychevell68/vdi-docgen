import os, io, time, base64, zipfile, yaml, requests
from flask import Flask, render_template, request, send_file, abort
from jinja2 import Environment, FileSystemLoader, StrictUndefined
app = Flask(__name__); app.secret_key=os.getenv("SECRET_KEY","dev")
GITHUB_TOKEN=os.getenv("GITHUB_TOKEN"); OWNER=os.getenv("GITHUB_OWNER"); REPO=os.getenv("GITHUB_REPO"); MAIN=os.getenv("GITHUB_MAIN","main")
API="https://api.github.com"
DOC_TPL=[("sow.md.j2","SOW.md"),("loe.md.j2","LOE.md"),("wbs.md.j2","WBS.md"),("hld.md.j2","HLD.md"),("lld.md.j2","LLD.md"),("atp.md.j2","ATP.md"),("asbuilt.md.j2","AsBuilt.md")]
def env(): return Environment(loader=FileSystemLoader("templates/docs"), undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
def render_md(data): 
    e=env(); out={}
    for t,o in DOC_TPL: out[o]=e.get_template(t).render(**data)
    return out
def hdr(): 
    if not GITHUB_TOKEN: raise RuntimeError("GITHUB_TOKEN not set")
    return {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept":"application/vnd.github+json"}
def main_sha():
    r=requests.get(f"{API}/repos/{OWNER}/{REPO}/git/ref/heads/{MAIN}", headers=hdr()); r.raise_for_status(); return r.json()["object"]["sha"]
def mk_branch(slug):
    sha=main_sha(); br=f"build/{slug}"
    r=requests.get(f"{API}/repos/{OWNER}/{REPO}/git/ref/heads/{br}", headers=hdr())
    if r.status_code==200: br=f"{br}-{int(time.time())}"
    r=requests.post(f"{API}/repos/{OWNER}/{REPO}/git/refs", headers=hdr(), json={"ref":f"refs/heads/{br}","sha":sha}); r.raise_for_status(); return br
def put_file(branch,path,bytes_,msg):
    url=f"{API}/repos/{OWNER}/{REPO}/contents/{path}"
    r=requests.put(url, headers=hdr(), json={"message":msg,"branch":branch,"content":base64.b64encode(bytes_).decode()})
    r.raise_for_status()
@app.get("/") 
def home(): return render_template("home.html")
@app.get("/presales")
def pre_get(): return render_template("forms/presales.html")
@app.post("/presales")
def pre_post():
    f=lambda n,d="":request.form.get(n,d).strip(); y=lambda n:request.form.get(n,"no").lower() in ("yes","true","on","1")
    slug=f("client_slug") or f("project_name").lower().replace(" ","-") or "client"
    data={"project":{"name":f("project_name"),"client_slug":slug},"platform":{"deployment_model":f("deployment_model","on_prem")}, "core":{"dns":[s.strip() for s in f("dns").split(",") if s.strip()]}, "topology":{"pods":[{"name":"Pod 1","site":f("pod1_site","DC1"),"region":f("pod1_region","Central US"),"vcenter":f("pod1_vcenter"),"uag":{"count":int(f("pod1_uag_count","2") or 2),"internet_facing":y("pod1_uag_internet")}}]}}
    files=render_md(data); mem=io.BytesIO(); 
    with zipfile.ZipFile(mem,"w") as z:
        z.writestr("intake.presales.yaml", yaml.safe_dump(data, sort_keys=False))
        for n,c in files.items(): z.writestr(f"output/{slug}/{n}", c)
    mem.seek(0)
    if request.form.get("push_to_github")=="on":
        br=mk_branch(slug)
        for n,c in files.items(): put_file(br, f"output/{slug}/{n}", c.encode(), f"add {n}")
        put_file(br, f"output/{slug}/intake.presales.yaml", yaml.safe_dump(data, sort_keys=False).encode(), "add intake")
        return f"Pushed to {br}. Get DOCX later at /docx/{slug}."
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name="presales-output.zip")
@app.get("/predeploy")
def pd_get(): return render_template("forms/predeploy.html")
@app.post("/predeploy")
def pd_post():
    f=lambda n,d="":request.form.get(n,d).strip(); slug=f("client_slug") or "client"
    data={"project":{"name":f("project_name",slug),"client_slug":slug}, "core":{"dns":[s.strip() for s in f("dns").split(",") if s.strip()], "ntp":[s.strip() for s in f("ntp").split(",") if s.strip()]}, "access":{"uag":{"pod1":{"vip_fqdn":f("pod1_uag_vip"),"cert_cn":f("pod1_uag_cert")}}, "load_balancer":f("lb_vendor")}, "images":{"os":[s.strip() for s in f("image_os").split(",") if s.strip()], "count":int(f("image_count","1") or 1)}}
    files=render_md(data); mem=io.BytesIO(); 
    with zipfile.ZipFile(mem,"w") as z:
        z.writestr("intake.predeploy.yaml", yaml.safe_dump(data, sort_keys=False))
        for n,c in files.items(): z.writestr(f"output/{slug}/{n}", c)
    mem.seek(0)
    if request.form.get("push_to_github")=="on":
        br=mk_branch(slug)
        for n,c in files.items(): put_file(br, f"output/{slug}/{n}", c.encode(), f"add {n}")
        put_file(br, f"output/{slug}/intake.predeploy.yaml", yaml.safe_dump(data, sort_keys=False).encode(), "add intake")
        return f"Pushed to {br}. Get DOCX later at /docx/{slug}."
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name="predeploy-output.zip")
@app.get("/docx/<slug>")
def docx(slug):
    try:
        r=requests.get(f"{API}/repos/{OWNER}/{REPO}/actions/artifacts", headers=hdr()); r.raise_for_status()
        arts=r.json().get("artifacts",[])
        for a in arts:
            if a.get("expired"): continue
            if "docx" in a.get("name",""):
                dl=requests.get(a["archive_download_url"], headers=hdr()); dl.raise_for_status()
                return send_file(io.BytesIO(dl.content), mimetype="application/zip", as_attachment=True, download_name=f"{a['name']}.zip")
        return "No artifact yet. Check repo output-docx/."
    except Exception as e:
        return f"Error: {e}", 400
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")), debug=True)
