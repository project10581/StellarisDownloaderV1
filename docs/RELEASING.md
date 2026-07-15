# Release process

Releases must be built from a clean, pushed commit. Do not build a public release
from an uncommitted working tree, and do not move a tag after publishing it.

1. Update `core/version.py` to the intended semantic version.
2. Run `ruff check .` and `python -m pytest -q`.
3. If `steamcmd/steamcmd.exe` changed, verify its Valve Authenticode signature and
   update `docs/STEAMCMD.md`.
4. Commit and push the complete source tree to `main` through review.
5. Create and push a tag whose name exactly matches `core.version.__version__`.
6. Let `.github/workflows/release.yml` build and upload the Windows archive.
7. Confirm the Release points to the same commit as the tag.

If a published tag or binary is wrong, publish a new patch version instead of
rewriting the existing tag.
