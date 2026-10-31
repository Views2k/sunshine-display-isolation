from pathlib import Path
import os
import shutil
import subprocess
import sys

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
workflow_root = target / ".github/workflows"
for name in ("build-windows.yml", "release.yml"):
    shutil.copy2(root / "display-isolation" / name, workflow_root / name)
for name in ("README.md", "NOTICE.md", "build-windows.yml", "release.yml", "prepare_fork.py", "apply_patch.py", "strict_display_policy.h"):
    (target / "display-isolation" / name).unlink()
subprocess.run([sys.executable, str(target / "display-isolation/verify_source.py")], check=True)
subprocess.run(["g++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-pedantic", "-I", str(target / "src"), str(target / "display-isolation/test_strict_display_policy.cpp"), "-o", str(target.parent / "policy-tests")], check=True)
subprocess.run([str(target.parent / "policy-tests")], check=True)
git(target, "config", "user.name", author_name)
git(target, "config", "user.email", author_email)
git(target, "switch", "-c", BRANCH)
git(target, "add", "src/video.cpp", "src/platform/windows/display_base.cpp", "src/strict_display_policy.h", "README.md", "NOTICE.md", "display-isolation", ".github/workflows")
git(target, "diff", "--cached", "--check")
git(target, "commit", "-m", "Keep Windows capture bound to its configured display")
subprocess.run(["git", "-C", str(target), "push", "origin", f"HEAD:refs/heads/{BRANCH}"], check=True)
print("Published source branch:", git(target, "rev-parse", "HEAD"))
