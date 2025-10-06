import argparse, os, sys, yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATES = [
    ("sow.md.j2", "SOW.md"),
    ("hld.md.j2", "HLD.md"),
    ("lld.md.j2", "LLD.md"),
    ("pdg.md.j2", "PDG.md"),
    ("asbuilt.md.j2", "AsBuilt.md"),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to intake YAML")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--templates", default="templates", help="Templates directory")
    args = ap.parse_args()

    with open(args.input, "r") as f:
        data = yaml.safe_load(f)

    os.makedirs(args.out, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(args.templates),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Simple validation
    required = [
        ("customer", "name"),
        ("engagement", "phases"),
        ("horizon", "version"),
        ("horizon", "pods"),
    ]
    for sec, key in required:
        if sec not in data or key not in data[sec] or data[sec][key] in (None, "", []):
            sys.exit(f"Missing required field: {sec}.{key}")

    for tpl, outfile in TEMPLATES:
        template = env.get_template(tpl)
        content = template.render(**data)
        with open(os.path.join(args.out, outfile), "w") as f:
            f.write(content)
        print(f"Wrote {outfile}")

if __name__ == "__main__":
    main()
