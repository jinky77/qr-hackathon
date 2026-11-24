import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from poc.okf import Bundle


def main():
    parser = argparse.ArgumentParser(description="Valide la conformance OKF d'un bundle (frontmatter YAML + type requis).")
    parser.add_argument("bundle", nargs="?", default=os.environ.get("OKF_BUNDLE_PATH", "okf-bundle"))
    args = parser.parse_args()
    bundle = Bundle(args.bundle)
    errors = bundle.validate()
    if errors:
        print(f"ECHEC — {len(errors)} erreur(s) de conformance OKF dans {args.bundle}:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK — bundle {args.bundle} conforme : {len(bundle.concepts)} concepts, index racine avec okf_version.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
