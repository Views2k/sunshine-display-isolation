from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

from verify_source import verify, BASE

EXPECTED = {
    "display-test-results.xml": "a31d5299cf652d1ef2bcce00131b300a30db5685e0ea2e0a2401b4aaebe98dc2",
    "linkage.txt": "417d88d894b6a5207813b0635d74d26f44a3d8175918ec924ae21019ba6a655d",
    "source.patch": "a9d8a897c4cbb595e15eabfe572082f55ce9a22e9ee39dc66467d27d6b4439d9",
    "strict_display_policy.h": "3cb952ee0b4dcab2fb4310b7a8c73cf252a4567e4dee28f4014e1c1195c04828",
    "sunshine.exe": "d6dab428ed4097ee92fb612a206a77c76854b2c7d6b1c6e7c177f18247560880",
    "toolchain-packages.txt": "82aa5302ca77d5f848a7ca743aa9b1b7a22a9488c6413f6a2a0a779351a14796",
    "zlib1.dll": "8ae7aeb0467763a1e271cd831ca8e2f7fd101602adb9923100ea26c6be2a559b",
    "provenance.json": "d3cf41581222327eb6ea11b2c3e40cbe0a25c6125b26dfe42fb2c5845a945eb2",
}

root = Path(__file__).resolve().parents[1]
verify(root)
archive = root / "input/build.zip"
if hashlib.sha256(archive.read_bytes()).hexdigest() != "d60a930759b86e1775cde78dee1d5f1fc081eddb09861a30876d5f87156c4e8e":
    raise RuntimeError("Reviewed archive hash mismatch")
extracted = root / "input/extracted"
extracted.mkdir()
with zipfile.ZipFile(archive) as bundle:
    entries = bundle.infolist()
    if len(entries) != len(EXPECTED) or {entry.filename for entry in entries} != set(EXPECTED):
        raise RuntimeError("Unexpected archive entries")
    if sum(entry.file_size for entry in entries) > 500 * 1024 * 1024:
        raise RuntimeError("Unexpected archive size")
    for entry in entries:
        data = bundle.read(entry)
        if hashlib.sha256(data).hexdigest() != EXPECTED[entry.filename]:
            raise RuntimeError("Artifact hash mismatch: " + entry.filename)
        (extracted / entry.filename).write_bytes(data)
results = ET.parse(extracted / "display-test-results.xml").getroot()
if int(results.attrib["tests"]) != 152 or int(results.attrib["failures"]) or int(results.attrib["errors"]):
    raise RuntimeError("Expected all 152 display-configuration tests to pass")
package = root / "release-package"
package.mkdir()
for name in ("sunshine.exe", "zlib1.dll"):
    shutil.copy2(extracted / name, package / name)
for name in ("LICENSE", "NOTICE.md"):
    shutil.copy2(root / name, package / name)
notices = package / "third-party-notices"
tracked = subprocess.check_output(["git", "ls-files", "--recurse-submodules"], cwd=root, text=True).splitlines()
for name in tracked:
    path = Path(name)
    if path.name.upper().startswith(("LICENSE", "COPYING", "NOTICE")) and (root / path).is_file():
        destination = notices / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, destination)
readme = """Sunshine display isolation 2026.1030.1\n\nWindows update for Sunshine 2026.914.233613.\n\nStop the Sunshine instance being updated. Back up sunshine.exe and zlib1.dll,\nthen replace those two files with the copies in this archive. Keep the existing\nassets, configuration, and pairing data. Start Sunshine and reconnect Moonlight.\nFor multiple instances, repeat the update for each instance.\n\nSunshine is developed by LizardByte and its contributors.\nDisplay-isolation changes are maintained by Views2k.\n\nSource and setup: https://github.com/Views2k/sunshine-display-isolation\nUpstream: https://github.com/LizardByte/Sunshine\nLicense: GNU GPL version 3. See LICENSE and NOTICE.md.\n"""
(package / "README.txt").write_text(readme, encoding="utf-8", newline="\n")
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
record = {
    "Version": "2026.1030.1",
    "UpstreamRevision": BASE,
    "PublishedSourceRevision": revision,
    "BuildDate": "2026-10-30",
    "DisplayConfigurationTests": {"Passed": 152, "Failed": 0},
    "RuntimeSourceVerification": "Exact reviewed patch and policy hashes matched",
    "Files": {name: EXPECTED[name] for name in ("sunshine.exe", "zlib1.dll", "source.patch", "strict_display_policy.h")},
}
(package / "BUILD.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
shutil.copy2(extracted / "toolchain-packages.txt", package / "toolchain-packages.txt")
print("Verified the reviewed build, source, and 152 passing test results")
