# Container scan notes

CVEs that scanners report against our published container images and that we have
assessed as **not affecting** CISO Assistant, with the evidence for each.

These are false positives, not accepted risk. A vulnerability that is real but has no
fix yet does **not** belong here — it gets tracked and fixed. Justifications use the
[OpenVEX](https://openvex.dev) vocabulary so the entries can be turned into VEX
statements if we ever publish them.

Every entry carries a **re-check when** condition. An entry whose condition has been
met is wrong until re-assessed, so it is removed rather than left in place.

To report a vulnerability, see [SECURITY.md](SECURITY.md).

---

## CVE-2026-85091 — zlib

| | |
|---|---|
| **Package** | `zlib` / `zlib1g` |
| **Versions in our images** | `1:1.3.dfsg+really1.3.1-1+dhi3`, `1:1.3.dfsg+really1.3.1-1` |
| **Images** | backend and frontend, community and enterprise |
| **Scanner verdict** | HIGH — affected range `>0`, fixed version `Not Fixed` |
| **Our verdict** | Not affected |
| **Justification** | `vulnerable_code_not_present` |
| **Assessed** | 2026-09-14 |

### Evidence

The advisory describes a heap buffer overflow in `gz_vacate()`, reachable through
`gzprintf()` / `gzvprintf()` after a non-blocking `gzwrite()` stall, and scopes it to
**zlib 1.3.1.2 through 1.3.2**. `gz_vacate()` was added upstream after 1.3.1.

Our images ship zlib 1.3.1 (`libz.so.1.3.1`), which predates the affected range. The
symbol is absent from the shipped library, on both `linux/amd64` and `linux/arm64`.

Backend images:

```console
$ docker run --rm --entrypoint bash ghcr.io/intuitem/ciso-assistant-community/backend:latest \
    -c 'ls -l /usr/lib/*/libz.so.1; grep -c gz_vacate /usr/lib/*/libz.so.1.3.1'
lrwxrwxrwx 1 root root 13 /usr/lib/aarch64-linux-gnu/libz.so.1 -> libz.so.1.3.1
0
```

Frontend images, which are distroless and ship no shell:

```console
$ docker run --rm --entrypoint node ghcr.io/intuitem/ciso-assistant-community/frontend:latest \
    -e "const b=require('fs').readFileSync('/usr/lib/x86_64-linux-gnu/libz.so.1.3.1'); \
        console.log('gz_vacate present:', b.includes('gz_vacate'))"
gz_vacate present: false
```

Debian has not triaged the CVE, so the package is marked `<unfixed>` in the security
tracker. Scanners translate that marker into an open-ended affected range, which is
why every version — including versions that predate the vulnerable code — is reported.

### References

- Debian bug [#1146895](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1146895)
- Upstream issue [madler/zlib#1310](https://github.com/madler/zlib/issues/1310)

### Re-check when

- Debian triages the CVE and assigns a fixed version, **or**
- the installed `zlib1g` revision changes from the ones recorded above — the base
  image tracks a tag, not a digest, so a mirror refresh can move it. Re-run the
  commands above: any version from 1.3.1.2 on is inside the affected range.

---

## CVE-2026-57585, GHSA-6v7p-g79w-8964 — msgpack, vendored in pip

| | |
|---|---|
| **Package** | `pkg:pypi/msgpack` |
| **Versions in our images** | `1.1.2`, inside `/usr/lib/python3/dist-packages/pip/_vendor/msgpack` |
| **Images** | mcp, community |
| **Scanner verdict** | HIGH — affected range `<1.2.1`, fixed version `1.2.1` |
| **Our verdict** | Not affected |
| **Justification** | `vulnerable_code_not_present` |
| **Assessed** | 2026-09-15 |

### Evidence

The advisory is a use-after-free in msgpack's **Cython `_cmsgpack` extension**. pip
vendors only the pure-Python fallback — no native module ships, so the vulnerable code
is absent:

```console
$ docker run --rm --entrypoint python ghcr.io/intuitem/ciso-assistant-community/mcp:latest -c \
    "import pathlib; v=pathlib.Path('/usr/lib/python3/dist-packages/pip/_vendor/msgpack'); \
     print('files:', sorted(p.name for p in v.iterdir())); \
     print('native modules:', [p.name for p in v.rglob('*.so')])"
files: ['COPYING', '__init__.py', 'exceptions.py', 'ext.py', 'fallback.py']
native modules: []
```

Independently, the code is unreachable. The image runs `python -m ca_mcp.server` from a
uv-built venv with `include-system-site-packages = false`, so `dist-packages` is not on
`sys.path` for the interpreter that actually runs:

```console
$ docker run --rm --entrypoint python ghcr.io/intuitem/ciso-assistant-community/mcp:latest -c \
    "import sys, importlib.util as u; print('executable:', sys.executable); \
     print('dist-packages on sys.path:', any('dist-packages' in p for p in sys.path)); \
     print('pkg_resources importable:', u.find_spec('pkg_resources') is not None)"
executable: /code/.venv/bin/python
dist-packages on sys.path: False
pkg_resources importable: False
```

Docker publishes the same assessment for the base image as a signed VEX attestation
(`docker scout vex get dhi.io/python:3.14`), which is why the base scans clean while our
derived image does not — see *VEX does not chain* below.

### References

- [GHSA-6v7p-g79w-8964](https://github.com/advisories/GHSA-6v7p-g79w-8964)
- [CVE-2026-57585](https://nvd.nist.gov/vuln/detail/CVE-2026-57585) — the same flaw; scanners report both

### Re-check when

- pip re-vendors msgpack and starts shipping a compiled `_cmsgpack` module, **or**
- `cli/Dockerfile` stops building the app into an isolated venv, **or**
- the vendored version moves off 1.1.2. Re-run the commands above.

---

## CVE-2025-47273, CVE-2026-59890 — setuptools, vendored in pip

| | |
|---|---|
| **Package** | `pkg:pypi/setuptools` |
| **Versions in our images** | reported as `70.3.0`, inside `/usr/lib/python3/dist-packages/pip/_vendor/pkg_resources` |
| **Images** | mcp, community |
| **Scanner verdict** | HIGH `<78.1.1` and MEDIUM `<83.0.0`, both with fixed versions |
| **Our verdict** | Not affected |
| **Justification** | `vulnerable_code_not_present` |
| **Assessed** | 2026-09-15 |

### Evidence

No copy of setuptools 70.3.0 is installed. pip vendors a stripped `pkg_resources`
subset derived from it, and scanners attribute that subset to the setuptools release it
was cut from. The affected modules are not part of the subset — CVE-2025-47273 is a
path traversal in `setuptools/package_index.py`, CVE-2026-59890 a Unicode-normalization
bug in the sdist build path:

```console
$ docker run --rm --entrypoint python ghcr.io/intuitem/ciso-assistant-community/mcp:latest -c \
    "import pathlib; r=pathlib.Path('/usr/lib/python3/dist-packages/pip/_vendor'); \
     print('files:', sorted(p.name for p in (r/'pkg_resources').rglob('*.py'))); \
     print('package_index.py:', [str(p) for p in r.rglob('package_index.py')]); \
     print('sdist.py:', [str(p) for p in r.rglob('sdist.py')])"
files: ['__init__.py']
package_index.py: []
sdist.py: []
```

The installed setuptools is `84.0.0`, past both fixed versions. The venv-isolation
evidence under the msgpack entry applies here unchanged: `setuptools` and
`pkg_resources` are both unimportable from the entrypoint interpreter.

### References

- [CVE-2025-47273](https://nvd.nist.gov/vuln/detail/CVE-2025-47273) — path traversal in `setuptools/package_index.py`
- [CVE-2026-59890](https://nvd.nist.gov/vuln/detail/CVE-2026-59890) — Unicode normalization in the sdist build path

### Re-check when

- pip vendors a fuller `pkg_resources` that includes `package_index.py`, **or**
- the reported version moves off 70.3.0, **or**
- real setuptools appears in the runtime venv rather than only in `dist-packages`.

---

## Notes on scanner coverage and VEX

Recorded 2026-09-15 so the mechanics do not get re-derived. All of it was measured, not
read off documentation.

**These four findings are Docker Scout–only.** Scout ingests pip's own CycloneDX vendor
BOM; Trivy and Grype identify Python packages from `.dist-info`/`.egg-info` metadata,
which vendored trees do not carry, so neither scanner lists the packages at all:

```console
$ trivy image --quiet --format json <image> | ...   # msgpack in SBOM: False | setuptools: False
$ grype <image> -o json --quiet | ...               # msgpack in SBOM: False | setuptools: False
```

Measured with Trivy 0.74.0 and Grype 0.118.0. This is not agreement — on the same image
Grype reports 86 matches / 28 High where Scout reports 1 High. The tools disagree about
what is in the image, not only about severity.

**VEX does not chain to derived images.** `dhi.io/python:3.14` and our mirror of it are
the same digest, and that base reports zero fixable CVEs because Docker attaches a VEX
attestation covering exactly these four. The attestation applies to the base image only;
anything built `FROM` it is re-indexed from the filesystem and reports them again.

**Publishing our own VEX would not suppress them for anyone by default.** Scout gates
suppression on `--vex-author`, which defaults to `<.*@docker.com>`, and the gate applies
to attestations and local files alike:

- our own document, via `--vex-location`, is loaded and annotates each finding
  `not affected [vulnerable code not present]` — but the counts stay at 3H/1M
- adding `--only-vex-affected --vex-author '<.*@intuitem.com>'` takes it to 0
- conversely, scanning the DHI base with `--vex-author '<.*@nobody.invalid>'` makes
  Docker's own attestation stop suppressing: 0 becomes 3H/1M

**Registry-side discovery does not work on GHCR.** GHCR does not implement the OCI 1.1
Referrers API — `GET /v2/intuitem/ciso-assistant-community/mcp/referrers/<digest>`
returns `404 MANIFEST_UNKNOWN` — so a VEX attestation pushed as a referrer cannot be
discovered there. Trivy's `--vex oci` additionally expects Cosign DSSE envelopes or, from
v0.73.0, Scout's bare `application/vnd.in-toto+json` referrers, and its product IDs must
be `pkg:oci/<name>?repository_url=<repo>` rather than image tags. Grype has no registry
discovery at all and takes local files only.

The practical consequence: a VEX document is worth keeping as a **local file** that every
scanner accepts (`--vex-location` for Scout, `--vex` for Trivy and Grype), not as a
distribution mechanism. Deleting dead code from an image remains the only remedy that
travels with the image and needs no consumer-side flags.
