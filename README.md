# RegOps

**Compliance as Code** — traceability between code, requirements, risks and tests for medical device software.

> *"Your repo. Your compliance. Always."*

## The problem

In medical device software (IEC 62304, ISO 14971, EU MDR, FDA 510k), traceability between requirements, code, risks and tests must be maintained continuously. Today, this lives in external tools (Greenlight Guru, MatrixReq, Aligned Elements) — separated from the code, always out of date, and creating vendor lock-in.

RegOps moves compliance into your repository. The source of truth is your code, not someone else's database.

## Install

```bash
pipx install git+https://github.com/rockridge-labs/regops
```

## Usage

```bash
# Check traceability gaps in current repo
regops check

# Check specific repo, output JSON for CI/CD
regops check --repo /path/to/mydevice --json

# Export markdown report
regops check --output report.md

# Bootstrap compliance structure in new repo
regops init --standard iec62304 --class B
```

## How it works

### 1. Annotate your code

Add compliance annotations in comments — works in any language:

```python
# @req SR-003 @risk RISK-042 @class C @mitigation MIT-012
def calibrate_probe(reference_signal):
    ...
```

```cpp
// @req SR-007 @class B
void DicomParser::parseHeader(const Buffer& buf) { ... }
```

### 2. Define compliance in YAML

```
compliance/
  requirements/   SR-xxx.yaml, SYS-xxx.yaml, UN-xxx.yaml
  risks/          RISK-xxx.yaml
  tests/          TC-xxx.yaml
.regops/
  schema.yaml     configurable meta-model
```

### 3. Run `regops check`

```
RegOps Traceability Report
Repo: /home/user/acmedevice  |  2026-05-22

  ✗ CRITICAL  R-62304-NOT-IMPL     SR-005 — no code annotation found
  ✗ CRITICAL  R-62304-CLASS-C-TEST SR-002 (class C) — no unit test found
  ⚠ WARNING   R-14971-RISK-NO-MIT  RISK-003 — mitigation MIT-003 not in code

Coverage : 4/5 SW requirements annotated (80%)
Gaps     : 2 critical  1 warning

Submission readiness: BLOCKED
```

## Supported languages

C, C++, Python, Cython, Go, Dart, OpenCL, Terraform

## Standards supported (V1)

- IEC 62304 (software lifecycle for medical devices)
- ISO 14971 (risk management)

Planned: EU MDR Technical Documentation, FDA 510k, IEC 62366, AI Act.

## Development

```bash
git clone https://github.com/rockridge-labs/regops
cd regops
pip install -e ".[dev]"
pytest tests/ -v

# Run on the included fixtures (synthetic medtech codebase)
regops check --repo fixtures/
```

## License

MIT
