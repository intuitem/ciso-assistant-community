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
symbol is absent from the shipped library, on both `linux/amd64` and `linux/arm64`:

```console
$ docker run --rm --entrypoint bash ghcr.io/intuitem/ciso-assistant-community/backend:latest \
    -c 'ls -l /usr/lib/*/libz.so.1; grep -c gz_vacate /usr/lib/*/libz.so.1.3.1'
lrwxrwxrwx 1 root root 13 /usr/lib/aarch64-linux-gnu/libz.so.1 -> libz.so.1.3.1
0
```

Debian has not triaged the CVE, so the package is marked `<unfixed>` in the security
tracker. Scanners translate that marker into an open-ended affected range, which is
why every version — including versions that predate the vulnerable code — is reported.

### References

- Debian bug [#1146895](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1146895)
- Upstream issue [madler/zlib#1310](https://github.com/madler/zlib/issues/1310)

### Re-check when

- Debian triages the CVE and assigns a fixed version, **or**
- our zlib moves to 1.3.1.2 or later, which is inside the affected range.
