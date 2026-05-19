# Releasing HomeCopy to PyPI

This repository publishes the `HomeCopy` installer package to PyPI using GitHub
Actions Trusted Publishing.

## One-time PyPI setup

1. Sign in to PyPI with the account that should own the `HomeCopy` project.
2. Open `https://pypi.org/manage/account/publishing/`.
3. Add a GitHub Actions trusted publisher with:
   - PyPI project name: `HomeCopy`
   - Owner: `Tommy-OMI`
   - Repository: `HomeCopy`
   - Workflow filename: `publish-pypi.yml`
   - Environment: `pypi`
4. If `HomeCopy` does not yet exist on PyPI, create it by registering the pending
   publisher above. The first successful publish will create the project.

## Release flow

1. Update package version in:
   - `pyproject.toml`
   - `src/homecopy_installer/__init__.py`
   - any user-facing docs that mention the installer version
2. Commit and push the version change to `main`.
3. Create and push a version tag:

```bash
git tag v0.9.1
git push origin v0.9.1
```

4. GitHub Actions will run `.github/workflows/publish-pypi.yml` and publish the
   package to PyPI.

## Local preflight

Before tagging a release:

```bash
python3 -m build
python3 -m pip install -e .
homecopy doctor
homecopy version
```
