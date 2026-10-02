# Release checklist

Run through this list for every install on a clinic computer. The automated part is
`python -m backend.release_check --tests` (exit 0 = no blocker). Everything below
it is a human step that no script can do.

## 1. Automated (release_check)

- [ ] Frontend bundle and stylesheet match the source (`node build.mjs --check`)
- [ ] Growth validation passes; WHO tables active
- [ ] All clinical vignettes match their hand derivation
- [ ] Every vignette signed off by a clinician (none disagreeing)
- [ ] Identifiers encrypted at rest, with the key file **outside** the app folder
- [ ] No AGPL package in the runtime requirements
- [ ] Full test suite passes
- [ ] Installed from a committed, tagged revision (record the tag here: ______)

## 2. Clinical

- [ ] Validation protocol completed for each module in use (`VALIDATION-PROTOCOL.md`)
- [ ] Every inactive reference on the Overview tab has been reviewed, and the
      clinic accepts that those outputs are refused until the data is supplied
- [ ] Every threshold in `backend/clinical/thresholds.json` reviewed against its guideline
- [ ] The intended-use and limitations section of the README read and accepted

## 3. Site and security

- [ ] Authentication decision recorded. The shipped default is OFF (owner decision):
      the app answers only on this computer, and approvals are signed `dev-no-auth`.
      If several clinicians share the computer, set `PCW_AUTH_ENABLED=1`.
- [ ] The database file (`backend/data/tw3.db`) contains no test fixtures.
      Start from an empty database for clinical use.
- [ ] Backups of the database, and **separately** of the key, tested by a restore
- [ ] Disk encryption (BitLocker) on the clinic computer
- [ ] `/api/health` shows no warnings except the recorded auth decision

## 4. Regulatory (confirm with a regulatory consultant)

This workspace computes clinical measures and flags findings. In India, software
intended for diagnosis or treatment decisions may be a medical device under the
Medical Devices Rules 2017 (CDSCO; SaMD risk classes A–D). Before clinical use
beyond the owner's own supervised practice, obtain professional advice on:

- [ ] Classification and whether registration or a licence is needed
- [ ] Software lifecycle evidence (IEC 62304), risk management (ISO 14971),
      and a quality system (ISO 13485) if it is to be supplied to others
- [ ] Data protection obligations (Digital Personal Data Protection Act 2023) for
      patient data, consent and retention
- [ ] Licences of third-party data: WHO tables (CC BY-NC-SA 3.0 IGO:
      non-commercial), the TW3 tables (licensed book), IAP data

None of the above is legal or regulatory advice. It lists questions to put to
someone qualified to answer them.

## Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Responsible clinician | | | |
| Person who installed it | | | |
