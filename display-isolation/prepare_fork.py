from pathlib import Path
import os
import json
import shutil
import subprocess
import sys
import urllib.request

BASE = "63d35f702ee9e362e43263742981836ec0710384"
BRANCH = "display-isolation"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


root = Path(__file__).resolve().parents[1]
if os.environ.get("GITHUB_REPOSITORY") != "Views2k/sunshine-display-isolation":
    raise RuntimeError("Unexpected repository")
if git(root, "ls-remote", "--heads", "origin", f"refs/heads/{BRANCH}"):
    raise RuntimeError("The destination branch already exists; nothing was replaced")
author_name = git(root, "show", "-s", "--format=%an", "HEAD")
author_email = git(root, "show", "-s", "--format=%ae", "HEAD")
if not author_name or not author_email.endswith("@users.noreply.github.com"):
    raise RuntimeError("Expected the configured GitHub noreply identity")
target = Path(os.environ["RUNNER_TEMP"]) / "sunshine-public-source"
subprocess.run(["git", "-C", str(root), "worktree", "add", "--detach", str(target), BASE], check=True)
subprocess.run([sys.executable, str(root / "display-isolation/apply_patch.py"), str(target)], check=True)
shutil.copytree(root / "display-isolation", target / "display-isolation")
shutil.copy2(root / "display-isolation/README.md", target / "README.md")
shutil.copy2(root / "display-isolation/NOTICE.md", target / "NOTICE.md")
for name in ("README.md", "NOTICE.md", "build-windows.yml", "release.yml", "prepare_fork.py", "apply_patch.py", "strict_display_policy.h"):
    (target / "display-isolation" / name).unlink()
subprocess.run([sys.executable, str(target / "display-isolation/verify_source.py")], check=True)
subprocess.run(["g++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-pedantic", "-I", str(target / "src"), str(target / "display-isolation/test_strict_display_policy.cpp"), "-o", str(target.parent / "policy-tests")], check=True)
subprocess.run([str(target.parent / "policy-tests")], check=True)
git(target, "config", "user.name", author_name)
git(target, "config", "user.email", author_email)
git(target, "switch", "-c", BRANCH)
git(target, "add", "src/video.cpp", "src/platform/windows/display_base.cpp", "src/strict_display_policy.h", "README.md", "NOTICE.md", "display-isolation")
subprocess.run([
    "git", "-C", str(target), "diff", "--cached", "--check", "--", ".",
    ":(exclude)display-isolation/reference.patch",
], check=True)
git(target, "commit", "-m", "Keep Windows capture bound to its configured display")


def api(path, data):
    request = urllib.request.Request(
        "https://api.github.com/repos/Views2k/sunshine-display-isolation/" + path,
        data=json.dumps(data).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


entries = []
for path in git(target, "diff", "--name-only", BASE, "HEAD").splitlines():
    content = subprocess.check_output(["git", "-C", str(target), "show", "HEAD:" + path]).decode("utf-8")
    entries.append({"path": path, "mode": "100644", "type": "blob", "content": content})
tree = api("git/trees", {"base_tree": git(target, "rev-parse", BASE + "^{tree}"), "tree": entries})
if tree["sha"] != git(target, "rev-parse", "HEAD^{tree}"):
    raise RuntimeError("Remote source tree differs from the verified local tree")
identity = {"name": author_name, "email": author_email}
commit = api("git/commits", {
    "message": "Keep Windows capture bound to its configured display",
    "tree": tree["sha"], "parents": [BASE], "author": identity, "committer": identity,
})
print("Prepared source commit:", commit["sha"])
print("Verified source tree:", tree["sha"])
