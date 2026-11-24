import argparse
import os
import shutil
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def build_skill_zip(out_path, bundle_dir, skill_dir):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(skill_dir, "SKILL.md"), "SKILL.md")
        for dirpath, _dirnames, filenames in os.walk(bundle_dir):
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                arc = os.path.join("knowledge", os.path.relpath(full, bundle_dir))
                zf.write(full, arc)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Package la skill agent (SKILL.md + bundle OKF) en zip uploadable dans LibreChat.")
    parser.add_argument("--out", default=os.path.join(ROOT, "dist", "okf-dixit-coach-skill.zip"))
    parser.add_argument("--bundle", default=os.path.join(ROOT, "okf-bundle"))
    parser.add_argument("--skill", default=os.path.join(ROOT, "skill"))
    args = parser.parse_args()
    out = build_skill_zip(os.path.abspath(args.out), args.bundle, args.skill)
    size = os.path.getsize(out)
    print(f"Skill packagee: {out} ({size} octets)")
    print("Contenu: SKILL.md a la racine + knowledge/ (bundle OKF complet).")
    print("Upload: dans LibreChat, ouvrir le panneau Skills/Agents et uploader ce zip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
