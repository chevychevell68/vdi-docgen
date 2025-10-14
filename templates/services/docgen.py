
import subprocess, shutil, pathlib, datetime, zipfile
from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATE_DIR = pathlib.Path("doc_templates")

def _env():
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

def render_markdown(template_name: str, ctx: dict) -> str:
    md = _env().get_template(template_name).render(ctx=ctx, now=datetime.date.today())
    return md

def _write_tmp(md_text: str, outdir: pathlib.Path, base: str) -> pathlib.Path:
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / f"{base}.md"
    p.write_text(md_text, encoding="utf-8")
    return p

def _pandoc_exists() -> bool:
    return shutil.which("pandoc") is not None

def render_docx(template_name: str, ctx: dict, outdir: pathlib.Path, docx_name: str, reference_docx: str | None = None) -> pathlib.Path:
    md_text = render_markdown(template_name, ctx)
    md_path = _write_tmp(md_text, outdir, docx_name.replace(".docx", ""))
    docx_path = outdir / docx_name

    if _pandoc_exists():
        cmd = ["pandoc", str(md_path), "-o", str(docx_path)]
        if reference_docx:
            cmd += ["--reference-doc", reference_docx]
        subprocess.run(cmd, check=True)
        return docx_path

    # Fallback minimal DOCX if Pandoc not present
    from docx import Document
    doc = Document()
    for line in md_text.splitlines():
        doc.add_paragraph(line)
    doc.save(docx_path)
    return docx_path

def zip_files(paths: list, zip_path: pathlib.Path) -> pathlib.Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            p = pathlib.Path(p)
            if p.exists():
                zf.write(p, arcname=p.name)
    return zip_path
