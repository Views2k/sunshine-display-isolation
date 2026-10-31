from pathlib import Path
import hashlib
import os
import subprocess
import tempfile

BASE = "63d35f702ee9e362e43263742981836ec0710384"
PATCH_SHA256 = "a9d8a897c4cbb595e15eabfe572082f55ce9a22e9ee39dc66467d27d6b4439d9"
HEADER_SHA256 = "3cb952ee0b4dcab2fb4310b7a8c73cf252a4567e4dee28f4014e1c1195c04828"


def verify(root):
    reference = (root / "display-isolation/reference.patch").read_bytes()
    if hashlib.sha256(reference).hexdigest() != PATCH_SHA256:
        raise RuntimeError("Reviewed patch hash mismatch")
    with tempfile.TemporaryDirectory(prefix="sunshine-index-", dir=root) as temporary:
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = str(Path(temporary) / "index")
        command = ["git", "-C", str(root)]
        subprocess.run(command + ["read-tree", BASE], env=environment, check=True)
        subprocess.run(command + ["apply", "--cached", str(root / "display-isolation/reference.patch")], env=environment, check=True)
        for name in ("src/video.cpp", "src/platform/windows/display_base.cpp"):
            expected = subprocess.check_output(command + ["rev-parse", ":" + name], env=environment, text=True).strip()
            content = (root / name).read_bytes().replace(b"\r\n", b"\n")
            actual = subprocess.check_output(command + ["hash-object", "--stdin"], input=content).decode().strip()
            if actual != expected:
                raise RuntimeError("Runtime file does not match the reviewed build: " + name)
            print(name + ": full Git blob hash matched")
    header = (root / "src/strict_display_policy.h").read_bytes().replace(b"\r\n", b"\n")
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
