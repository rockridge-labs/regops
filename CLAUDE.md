# RegOps — CLAUDE.md

*Document d'orientation pour les sessions Claude et l'agent Tachikoma*
*Créé le 2026-05-22 · v1*

---

## Vue d'ensemble

RegOps est un outil CLI Python qui maintient la traçabilité entre le code source, les exigences, les risques et les tests dans les projets de dispositifs médicaux logiciels. La source de vérité de la compliance vit dans le repo du client — pas dans une base de données externe.

**Philosophie centrale : Compliance as Code.**
Tagline : *"Your repo. Your compliance. Always."*

Cible : PME medtech (5–50 personnes), normes EU MDR + IEC 62304 + ISO 14971, avec extension FDA 510k prévue.

Stade actuel : **V0 — MVP CLI**, pas encore déployé, pas de clients.

---

## Architecture

```
regops/                         # package Python installable via pipx
├── regops/
│   ├── cli.py                  # entrypoint Typer : check / init / report
│   ├── parser.py               # scan annotations @req @risk @class dans le code
│   ├── loader.py               # charge les YAMLs compliance/ du repo cible
│   ├── checker.py              # moteur de détection de gaps
│   ├── schema.py               # méta-modèle configurable (.regops/schema.yaml)
│   └── reporter.py             # output Rich terminal + --json flag
├── tests/
│   ├── test_parser.py
│   ├── test_checker.py
│   └── test_loader.py
├── fixtures/                   # repo medtech synthétique pour les tests
│   ├── .regops/
│   │   └── schema.yaml         # schéma de démonstration
│   ├── compliance/
│   │   ├── requirements/       # SR-xxx.yaml, SYS-xxx.yaml, UN-xxx.yaml
│   │   ├── risks/              # RISK-xxx.yaml
│   │   └── tests/              # TC-xxx.yaml
│   └── src/
│       ├── calibration.cpp
│       ├── signal.py
│       ├── dicom.go
│       └── ui.dart
├── pyproject.toml
└── README.md
```

---

## Stack technique

| Composant | Choix | Raison |
|---|---|---|
| Langage | Python 3.11+ | Ecosystème rich, pathlib, dataclasses |
| CLI framework | **Typer** | Moderne, autodoc, type hints natifs |
| Terminal output | **Rich** | Couleurs, tables, progress bars |
| YAML parsing | **PyYAML** | Standard, simple |
| Tests | **pytest** | Standard Python |
| Packaging | **pyproject.toml** + **pipx** | Standard moderne, isolation CLI |
| Annotations dans le code | Commentaires `# @req` / `// @req` | Universel multi-langage |

**Langages cibles supportés pour le parsing d'annotations :**
C++, Python, Cython (.pyx/.pxd), Go, Dart (Flutter), OpenCL (.cl), Terraform (.tf)

**Installation utilisateur finale :**
```bash
pipx install git+https://github.com/rockridge-labs/regops
regops check --repo .
```

---

## Modèle de données central

### Annotations dans le code source

Format universel (commentaire sur la ligne précédant la fonction/classe/bloc) :

```python
# @req SR-003 @risk RISK-042 @class C
def calibrate_probe(signal):
    ...
```

```cpp
// @req SR-007 @risk RISK-018 @class B
void DicomParser::parseHeader(const Buffer& buf) { ... }
```

Tags supportés :
- `@req <ID>` — référence une exigence ou un besoin (SR-xxx, SYS-xxx, UN-xxx, REG-xxx, SEC-xxx, ARCH-xxx, SI-xxx, SU-xxx)
- `@risk <ID>` — référence un risque (RISK-xxx)
- `@class <A|B|C>` — classe de sécurité IEC 62304
- `@mitigation <ID>` — référence une mitigation (MIT-xxx)
- `@test <ID>` — référence un test case (TC-xxx)

### Taxonomie des besoins (needs)

RegOps modélise plusieurs *sources de besoin* mappant toutes au concept standard `user_need` (au sens ISO 13485:2016 §7.3 *Stakeholder Needs*) :

| Type | Préfixe | Origine |
|---|---|---|
| `user_need` | UN | Besoin clinique ou opérationnel de l'utilisateur final |
| `regulatory_need` | REG | Conformité à une norme ou loi externe (MDR, IEC 62304, FDA…) |
| `security_need` | SEC | Cybersécurité, sécurité patient (ISO 14971, IEC 81001-5-1, HIPAA, GDPR) |
| `architectural_need` | ARCH | Contrainte technique (interop, plateforme, langage…) |

Tous mappent à `user_need` comme concept standard — les règles de conformité (R-TRACE-NO-PARENT, etc.) s'appliquent uniformément, et un SYS peut déclarer `parent_refs: [UN-001, SEC-001]` pour tracer une origine composite.

### Structure YAML des exigences (compliance/requirements/SR-xxx.yaml)

```yaml
id: SR-003
type: software_requirement       # maps_to dans le méta-modèle
title: "Probe calibration accuracy"
description: >
  The system shall calibrate probe sensitivity within ±2% of reference standard.
safety_class: C                  # A | B | C (IEC 62304)
parent_refs: [SYS-001]           # dérive de
risk_refs: [RISK-042, RISK-043]  # risques associés
test_refs: [TC-089, TC-090]      # tests de vérification attendus
status: approved                 # approved | draft | deprecated
last_reviewed: 2025-11-15
```

### Structure YAML des risques (compliance/risks/RISK-xxx.yaml)

```yaml
id: RISK-042
title: "Incorrect calibration leading to false measurement"
hazard: HAZ-007
severity: critical               # critical | major | minor
probability: possible
mitigation_refs: [MIT-012]
residual_risk: acceptable
status: approved
```

### Structure YAML des tests (compliance/tests/TC-xxx.yaml)

```yaml
id: TC-089
title: "Calibration accuracy within tolerance"
type: unit_test                  # unit_test | integration_test | system_test | validation
verifies_refs: [SR-003]
file: tests/test_calibration.py::test_probe_calibration_accuracy
regression: true
last_run: 2026-01-15
last_result: passed
```

---

## Méta-modèle (.regops/schema.yaml)

Le schéma configure la terminologie du projet client. Chaque type de noeud est mappé vers un concept standard. Les règles de conformité s'appliquent au concept standard, pas au label.

```yaml
node_types:
  user_need:
    label: "User Need"
    abbreviation: "UN"
    maps_to: user_need
    requires_code: false

  regulatory_need:                 # même concept standard, classification fine
    label: "Regulatory Need"
    abbreviation: "REG"
    maps_to: user_need
    requires_code: false

  security_need:
    label: "Security Need"
    abbreviation: "SEC"
    maps_to: user_need
    requires_code: false

  architectural_need:
    label: "Architectural Need"
    abbreviation: "ARCH"
    maps_to: user_need
    requires_code: false

  system_requirement:
    label: "System Requirement"
    abbreviation: "SYS"
    maps_to: system_requirement
    requires_code: false

  software_requirement:
    label: "Software Requirement"
    abbreviation: "SR"
    maps_to: software_requirement
    requires_code: true

  software_item:
    label: "Software Item"
    abbreviation: "SI"
    maps_to: software_item
    requires_code: true

  software_unit:
    label: "Software Unit"
    abbreviation: "SU"
    maps_to: software_unit
    requires_code: true

active_standards:
  - iec_62304
  - iso_14971
```

---

## Commandes CLI V1

### `regops check`

Analyse le repo courant (ou `--repo <path>`) et produit le rapport de gaps.

```
$ regops check

RegOps Traceability Report
Repo: /home/user/mydevice  |  Commit: a3f92c1  |  2026-05-22

  CRITICAL  SR-007 — aucune référence dans le code
  CRITICAL  SR-003 (classe C) — aucun test unitaire trouvé
  WARNING   RISK-042 — mitigation MIT-012 non référencée dans le code
  WARNING   SR-015 — implémenté mais safety_class non déclarée
  INFO      47 / 52 exigences couvertes (90%)

Submission readiness: BLOCKED (2 critical gaps)
Run `regops check --json` for machine-readable output.
```

Options :
- `--repo <path>` — repo à analyser (défaut : `.`)
- `--json` — output JSON pour CI/CD
- `--output <file>` — exporter le rapport en markdown

### `regops init`

Bootstrap la structure compliance/ dans un nouveau repo.

```
$ regops init --standard iec62304 --class B
```

Crée `.regops/schema.yaml` + `compliance/` avec des fichiers d'exemple.

### `regops report`

Génère un rapport markdown exportable depuis l'état courant.

```
$ regops report --output traceability-report-2026-05.md
```

---

## Règles de conformité V1 (moteur checker.py)

| ID règle | Norme | Condition | Sévérité |
|---|---|---|---|
| R-62304-NOT-IMPL | IEC 62304 §5.3 | Exigence SW sans référence dans le code | critical |
| R-62304-CLASS-C-TEST | IEC 62304 §5.5.2 | SU/SR classe C sans unit test | critical |
| R-62304-CLASS-B-TEST | IEC 62304 §5.5.2 | SU/SR classe B sans test (unit ou intégration) | warning |
| R-62304-NO-CLASS | IEC 62304 §4.3 | Exigence SW sans safety_class déclarée | warning |
| R-14971-RISK-NO-MIT | ISO 14971 §6.3 | Risque sans mitigation référencée dans le code | critical |
| R-14971-MIT-ORPHAN | ISO 14971 §6.4 | Mitigation référencée dans le code mais absente du risk file | warning |
| R-TRACE-ORPHAN-REQ | Traçabilité | Annotation @req pointant vers un ID inexistant | critical |
| R-TRACE-NO-PARENT | IEC 62304 §5.2 | SR sans parent (SYS ou tout type mappant à `user_need` : UN, REG, SEC, ARCH) déclaré | warning |

---

## Ce que la V1 ne fait PAS (scope explicite)

- Pas d'UI web
- Pas de connexion Git (pas de diff automatique entre commits)
- Pas d'import MatrixReq (V2)
- Pas de génération de Technical File / DHF (V3)
- Pas de module cybersécurité / SBOM (V2)
- Pas d'inférence IA des liens non annotés (V2)
- Pas de support FDA 510k (V2)

---

## Mode agent autonome via OpenClaw (Tachikoma)

Quand tu reçois une instruction via Slack (channel `#regops`) depuis le compte de Thomas Deschamps, tu DOIS suivre les règles ci-dessous.

### Règles globales (identiques sur tous les projets Rockridge Labs)

#### 1. Exploration avant planification
Avant tout plan ou code, fais cet audit :
- Lis ce CLAUDE.md en entier
- Vérifie la branche par défaut via `git branch -r`
- Identifie les conventions de fait via `git log --pretty=%s -25`
- Vérifie si la feature demandée n'est pas déjà implémentée
- Détecte les divergences entre CLAUDE.md et code réel — signale-les

#### 2. Reformulation du plan AVANT le code
Aucune ligne de code n'est écrite avant que Thomas ait validé un plan explicite contenant :
- Fichiers touchés (estimés, avec delta de lignes prévu)
- Choix techniques justifiés
- Risques principaux identifiés
- Cas de tests couverts
- Diff size estimé
- Confirmations numérotées

Envoie le plan dans Slack, attends l'OK explicite avant de coder.

#### 3. Branche `feature/*` depuis `master`
- Toujours créer une branche `feature/<slug-court>` depuis `origin/master`
- JAMAIS commit sur `master` directement

#### 4. Limite de diff par PR : 200 lignes humaines max
Si dépassement prévisible : signaler AVANT de coder, demander dérogation explicite.

**Comptent dans les 200 lignes :** code applicatif (`regops/*.py` hors docstrings), config (pyproject.toml, hatch), CLAUDE.md, README, plans `.tachikoma/plans/`

**Ne comptent pas :** code de test (`tests/`), docstrings, `*.lock`, fixtures YAML (compliance/, fixtures/), snapshots pytest

*Note : un volume de tests déraisonnable peut être signalé en review au cas par cas.*

#### 5. Tests obligatoires
Toute PR touchant `parser.py`, `checker.py`, `loader.py`, ou `schema.py` DOIT inclure ou mettre à jour les tests pytest correspondants. Commande : `pytest tests/ -v`

#### 6. Conventions de commits
Conventional commits : `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`

Exemples :
```
feat: add @mitigation tag parsing in parser.py
fix: handle missing safety_class in checker R-62304-NO-CLASS
test: add fixtures for RISK orphan detection
docs: update CLAUDE.md with schema.yaml format
```

#### 7. Corps de PR obligatoire
Chaque PR doit contenir :
```
## Ce que fait cette PR
[description courte]

## Fichiers touchés
- fichier.py : +X / -Y lignes

## Diff
X lignes humaines [+ Y lignes non-comptées si applicable]

## Tests
- [ ] pytest tests/ -v passe
- [ ] regops check sur fixtures/ produit le résultat attendu
```

#### 8. Quand bloquer et demander
- Instruction contradictoire avec CLAUDE.md
- Scope amène à toucher `.env`, infra, secrets
- Dépendance externe inattendue nécessaire
- Feature déjà implémentée détectée
- Ambiguïté sur une règle de conformité médicale

### Spécificités RegOps

#### Règle domain — Ne pas inventer des règles de normes
Les règles de conformité dans `checker.py` doivent correspondre exactement aux normes listées dans ce CLAUDE.md. Ne pas ajouter de règles R-xxx sans validation explicite de Thomas — une règle incorrecte est pire qu'une règle manquante dans un outil de compliance médicale.

#### Règle domain — Fixtures comme oracle de vérité
Les fichiers dans `fixtures/` représentent un cas medtech réaliste de référence. Tout nouveau module doit être testé contre ces fixtures. Si une PR modifie le comportement attendu sur les fixtures, le corps de PR doit expliquer pourquoi.

#### Conventions de code observées
Conventional commits dès le premier commit. Type hints Python obligatoires. Dataclasses pour les structures de données. Pas de dépendances externes non listées dans pyproject.toml sans validation.
