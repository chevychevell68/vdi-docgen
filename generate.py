import argparse
import os
import sys
import yaml
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

    env = Environment(
        loader=FileSystemLoader(args.templates),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    if not os.path.exists(args.input):
        sys.exit(f"Input not found: {args.input}")

    with open(args.input, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    os.makedirs(args.out, exist_ok=True)

    # Render every template exactly with provided data (no inference).
    for tpl, outfile in TEMPLATES:
        template = env.get_template(tpl)
        content = template.render(**data)
        with open(os.path.join(args.out, outfile), "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Wrote {outfile}")

if __name__ == "__main__":
    main()
