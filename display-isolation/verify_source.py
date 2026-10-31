from pathlib import Path
import hashlib
import subprocess

BASE = "63d35f702ee9e362e43263742981836ec0710384"
PATCH_SHA256 = "a9d8a897c4cbb595e15eabfe572082f55ce9a22e9ee39dc66467d27d6b4439d9"
HEADER_SHA256 = "3cb952ee0b4dcab2fb4310b7a8c73cf252a4567e4dee28f4014e1c1195c04828"


def verify(root):
    reference = (root / "display-isolation/reference.patch").read_bytes()
    if hashlib.sha256(reference).hexdigest() != PATCH_SHA256:
        raise RuntimeError("Reviewed patch hash mismatch")
    actual = subprocess.check_output([
        "git", "-C", str(root), "diff", BASE, "--",
        "src/video.cpp", "src/platform/windows/display_base.cpp",
    ])
    if actual.replace(b"\r\n", b"\n") != reference.replace(b"\r\n", b"\n"):
        raise RuntimeError("Runtime changes do not match the reviewed build")
    header = (root / "src/strict_display_policy.h").read_bytes()
    if hashlib.sha256(header).hexdigest() != HEADER_SHA256:
        raise RuntimeError("Display policy hash mismatch")
    changed = subprocess.check_output([
        "git", "-C", str(root), "diff", "--name-only", BASE, "--", "src",
    ], text=True).splitlines()
    allowed = {"src/video.cpp", "src/platform/windows/display_base.cpp", "src/strict_display_policy.h"}
    if set(changed) - allowed:
        raise RuntimeError("Unexpected runtime source changes")
    print("Runtime source matches the reviewed Windows build")


if __name__ == "__main__":
    verify(Path(__file__).resolve().parents[1])
