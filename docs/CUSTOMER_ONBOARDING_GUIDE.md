# BioNexus Customer Onboarding Guide

**For Lab IT Administrators and QC Managers**

---

**Document Information**

| Field | Value |
|-------|-------|
| Document ID | BNX-CG-001 |
| Version | 1.0 |
| Date | 2026-02-28 |
| Audience | Lab IT Admins, QC Managers, Lab Technicians, Principal Investigators, Auditors |
| Classification | Customer-Facing |

---

## Table of Contents

1. [Welcome and Overview](#1-welcome-and-overview)
2. [Pre-Deployment Checklist](#2-pre-deployment-checklist)
3. [Step 1: Tenant Setup](#3-step-1-tenant-setup)
4. [Step 2: User Provisioning](#4-step-2-user-provisioning)
5. [Step 3: BioNexus Box Installation](#5-step-3-bionexus-box-installation)
6. [Step 4: Instrument Registration](#6-step-4-instrument-registration)
7. [Step 5: System Configuration](#7-step-5-system-configuration)
8. [Step 6: First Data Workflow](#8-step-6-first-data-workflow)
9. [Step 7: Qualification and Go-Live](#9-step-7-qualification-and-go-live)
10. [Day-to-Day Operations](#10-day-to-day-operations)
11. [Troubleshooting](#11-troubleshooting)
12. [Frequently Asked Questions](#12-frequently-asked-questions)
13. [Support and Contact](#13-support-and-contact)
14. [Appendix: Regulatory Rationale](#14-appendix-regulatory-rationale)

---

## 1. Welcome and Overview

Welcome to BioNexus. You have just taken an important step toward eliminating paper-based data transcription from your quality control lab and replacing it with a compliant, fully auditable electronic record system.

This guide will walk you from initial setup through your first certified data record. It is written for Lab IT administrators and QC managers, not software developers. Technical terms are explained the first time they appear.

### What BioNexus Does for Your Lab

Every day, your instruments — dissolution testers, HPLC systems, pH meters, spectrophotometers, balances — produce results. Today, those results are often printed on paper, hand-transcribed into a spreadsheet or LIMS (Laboratory Information Management System), and reviewed by someone who was not there when the measurement was taken. That process is slow, error-prone, and increasingly difficult to justify during a regulatory inspection.

BioNexus replaces that workflow in three parts:

**1. The BioNexus Box (the hardware)**
A small, rugged device that you connect to your instrument via a standard serial or USB cable. It captures the instrument's raw output the moment it is produced — no manual steps required. Every reading is time-stamped, hashed (cryptographically fingerprinted) and queued for secure upload to the cloud.

**2. The BioNexus Platform (the cloud software)**
The data arrives in your secure cloud workspace where AI-assisted parsing extracts the key values, presents them for human review, and lets authorised staff validate and correct results with a full documented reason for every change.

**3. The Certified Report (the output)**
Once a Principal Investigator certifies the results using double authentication (password plus one-time code), BioNexus generates an immutable signed report with a full audit trail — ready for submission to an auditor or regulatory authority at any time.

### Key Benefits

| Benefit | What It Means for You |
|--------|----------------------|
| Eliminates manual transcription | No more paper printouts, no retyping errors |
| Automatic audit trail | Every action is logged with who did it and when — automatically |
| 21 CFR Part 11 and EU Annex 11 ready | Designed for regulated pharma/biotech environments from day one |
| Same-day installation | BioNexus Box connects and streams data within one hour of unpacking |
| Tamper-evident records | SHA-256 chaining makes any data manipulation immediately detectable |
| Offline resilience | If your network goes down, the Box keeps capturing and uploads automatically when reconnected |

### Who This Guide Is For

This guide is primarily written for the two people most responsible for making BioNexus work in your lab:

- **Lab IT Administrator** — the person who will configure user accounts, manage the network connection, and oversee the technical deployment
- **QC Manager** — the person responsible for ensuring data quality, compliance, and correct use by lab staff

Separate sections describe day-to-day tasks for Lab Technicians, Principal Investigators, and Auditors.

---

## 2. Pre-Deployment Checklist

Before your BioNexus Box arrives and before anyone creates a user account, work through this checklist. Completing it in advance will make your installation smooth and fast.

### Network Requirements

- [ ] Outbound internet access is available from the bench or instrument room where the Box will sit (HTTPS, port 443, to `api.bionexus.io`)
- [ ] An Ethernet cable and a free network port are available near the instrument
- [ ] Your firewall or proxy does not block outbound HTTPS traffic to external addresses (if in doubt, ask your IT team to whitelist `api.bionexus.io`)
- [ ] An NTP (Network Time Protocol) server is reachable, or the Box can access the public NTP pool (`pool.ntp.org`) — accurate timestamps are required for compliance
- [ ] If your lab uses a proxy server, you have the proxy hostname, port, and any authentication credentials ready

> **Why this matters:** The BioNexus Box communicates only outbound over HTTPS (the same protocol your browser uses for secure websites). No inbound ports are opened on your network. Accurate time synchronisation is a regulatory requirement — every record must carry a trustworthy, contemporaneous timestamp.

### Instrument Inventory

For each instrument you plan to connect, gather the following before installation day:

- [ ] Instrument make, model, and serial number
- [ ] Instrument type (e.g. dissolution tester, HPLC, pH meter, balance)
- [ ] Communication interface: RS232 (serial) or USB?
  - If RS232: note the baud rate (commonly 9600), data bits (usually 8), parity (usually None), and stop bits (usually 1). This is often printed on a label near the instrument's serial port or in the instrument manual under "Data Output" or "RS-232 Settings."
  - If USB: note the USB cable type (Type A, Type B, mini-USB, etc.)
- [ ] Cable availability — BioNexus ships a standard RS232 cable and USB cable in the box; confirm the instrument connector type matches
- [ ] Calibration due date for each instrument (required for GxP records)
- [ ] Name or ID used for the instrument in your lab's existing records (this becomes the instrument identifier in BioNexus)

### User List

- [ ] Prepare a list of all staff who will use BioNexus, with name, email address, and role (see Step 2 for role descriptions)
- [ ] Identify at least one System Administrator — typically the Lab IT Admin
- [ ] Identify which users will have Principal Investigator (PI) role — typically the QC Manager or senior scientist with authority to certify results
- [ ] Identify any external auditors who may need read-only access

### IT Prerequisites

- [ ] At least one person on site has the authority and access to approve network connectivity for a new device
- [ ] A browser-capable workstation is available for the initial admin setup (Chrome, Edge, Firefox, or Safari — all modern versions are supported)
- [ ] If your organisation requires asset registration of new hardware, the BioNexus Box device ID (printed on the box label) is available to submit before installation
- [ ] Any required IT change requests or approvals have been raised and approved in advance

### Compliance and QA Prerequisites

- [ ] A GxP validation scope has been agreed — contact your BioNexus onboarding specialist if you are unsure whether IQ/OQ/PQ qualification is required before go-live
- [ ] Your organisation's electronic records and electronic signatures policy (or SOP) permits the use of a cloud-based system with double-authentication electronic signatures
- [ ] If your site is under an active FDA or EMA inspection, notify your BioNexus account manager before beginning deployment

> **IQ/OQ/PQ explained:** IQ (Installation Qualification) confirms the system is installed correctly. OQ (Operational Qualification) confirms it works as intended. PQ (Performance Qualification) confirms it performs correctly in your specific environment. BioNexus works with GMP4U, a specialist qualification partner, to support formal validation if required by your QA team. See Step 7 for details.

---

## 3. Step 1: Tenant Setup

A **tenant** in BioNexus is your organisation's private, isolated workspace in the cloud. All your instruments, users, data, and audit records belong to your tenant and are completely separated from every other BioNexus customer's data.

### 3.1 Account Creation

BioNexus provisions your tenant as part of the onboarding process. You will receive a welcome email containing:

- Your organisation's unique BioNexus web address (e.g. `https://app.bionexus.io`)
- Your temporary System Administrator username and password
- A link to complete account setup

**First login steps:**

1. Open the welcome email and click the "Complete Account Setup" link.
2. You will be prompted to create a new, permanent password. Your password must be at least 12 characters and include uppercase letters, numbers, and special characters.
3. You will then be asked to set up two-factor authentication (2FA) — this is required for all Administrator accounts. Use an authenticator app (Google Authenticator, Microsoft Authenticator, or Authy) to scan the QR code shown on screen.
4. Read and accept the Terms of Service and Data Processing Agreement.
5. You are now logged in as your organisation's first System Administrator.

> **Regulatory note:** Strong password policies and two-factor authentication for administrators are required by 21 CFR Part 11 Section 11.300, which mandates that controls exist to ensure the identity of electronic signature users.

### 3.2 Organisation Configuration

After first login, navigate to **Settings > Organisation** and complete the following:

**Required fields:**
- Organisation name (as it should appear on certified reports)
- Primary contact name and email address
- Site address (used on report headers)
- Regulatory context: select from FDA 21 CFR Part 11, EU Annex 11, or both

**Optional but recommended:**
- Organisation logo (appears on report headers and PDF exports)
- Lab site name (if you have multiple sites, each gets its own tenant)
- GxP document control number for this system (if applicable under your document management process)

### 3.3 Notification Configuration

Navigate to **Settings > Notifications** to configure where alerts are sent:

- **Operations contact email**: receives alerts when a BioNexus Box goes offline, when an instrument stops sending data, or when a system error occurs
- **Security contact email**: receives alerts when unusual login activity or audit chain integrity issues are detected
- **Report distribution list**: users who receive email notifications when certified reports are generated

> **Recommendation:** Use a shared team inbox (e.g. `lab-systems@yourcompany.com`) rather than an individual's email for operations and security alerts. If a key person is on leave, alerts will still be seen.

---

## 4. Step 2: User Provisioning

### 4.1 Understanding the Five Roles

BioNexus uses role-based access control (RBAC — a system where each user is assigned a role that defines exactly what they can and cannot do). There are five roles, designed to match the real structure of a QC laboratory:

---

**Role 1: Admin (System Administrator)**
_For: Lab IT Administrator, QA System Owner_

The Admin has full access to every part of the system: creating and deactivating users, registering instruments, configuring system settings, and viewing all data and audit trails. Every organisation must have at least one Admin. There should be no more than two or three Admins to maintain access control discipline.

What an Admin can do:
- Create, modify, and deactivate user accounts
- Register and configure instruments and BioNexus Boxes
- Access and export all audit trail records
- Configure system-wide compliance settings
- Manage data retention policies

What an Admin cannot do on behalf of others:
- Certify a data record (certification must be done by the PI who owns the decision)

---

**Role 2: Principal Investigator (PI)**
_For: QC Manager, Senior Scientist, Method Owner, Analytical Lead_

The PI is the person with scientific authority to certify that a data record is correct and ready for the audit trail. This is the role that corresponds to a "second reviewer" or "authorising signatory" in a paper-based process. PIs can create and validate data, and they are the only role that can perform the final certification (which requires double authentication).

What a PI can do:
- Upload instrument data files and review parsed results
- Make and document corrections to parsed data
- Certify validated data records using double authentication (electronic signature)
- View all audit trail records for their tenant
- Download certified PDF reports

---

**Role 3: Lab Technician**
_For: QC Analyst, Instrument Operator, Lab Scientist_

The Lab Technician is the person who runs the instrument, uploads the raw data file, and performs the initial review and correction of parsed results. They can do everything needed to prepare a data record for PI certification, but they cannot perform the final certification themselves.

What a Lab Technician can do:
- Upload instrument data files (CSV, PDF, or from BioNexus Box)
- Review and correct parsed data fields (with a documented reason for each correction)
- Mark a data record as ready for PI review
- View their own submitted records and audit trail entries

What a Lab Technician cannot do:
- Certify a data record
- Access other users' records (only records assigned to their team)
- Change system configuration

---

**Role 4: Auditor**
_For: Internal QA Auditor, External Regulatory Inspector, Qualified Person (QP)_

The Auditor has read-only access to everything: all data records, all certified reports, and the complete audit trail. Nothing an Auditor does modifies any record — they can only view and download. This role is specifically designed to support inspection readiness: when an FDA or EMA inspector arrives, you can create a time-limited Auditor account for them.

What an Auditor can do:
- View all data records in any state
- View the complete, unfiltered audit trail
- Download certified reports and audit trail exports
- Verify the integrity of the audit chain

What an Auditor cannot do:
- Create, modify, or delete any record
- Upload data
- Change any system setting

---

**Role 5: Viewer**
_For: Management, Regulatory Affairs staff, external partners with limited access needs_

The Viewer is a read-only role similar to Auditor, but with restricted scope. Viewers can see approved and certified records and reports but cannot see the raw audit trail or in-progress records. This is appropriate for management dashboards or sharing results with a contract organisation.

What a Viewer can do:
- View certified reports and approved records
- Download approved PDF reports

What a Viewer cannot do:
- View in-progress or uncertified records
- View the audit trail
- View raw instrument data

---

### 4.2 Role Permissions Summary

| Permission | Admin | PI | Technician | Auditor | Viewer |
|------------|-------|----|-----------|---------|--------|
| Create/manage users | Yes | No | No | No | No |
| Register instruments | Yes | No | No | No | No |
| Upload data | Yes | Yes | Yes | No | No |
| Correct parsed data | Yes | Yes | Yes | No | No |
| Certify records | No | Yes | No | No | No |
| View all audit trail | Yes | Yes | No | Yes | No |
| Export audit trail | Yes | Yes | No | Yes | No |
| View certified reports | Yes | Yes | Yes | Yes | Yes |
| System configuration | Yes | No | No | No | No |

### 4.3 Creating User Accounts

Navigate to **Settings > Users > Add User**.

For each user, enter:
1. First name and last name
2. Email address (this becomes their login username)
3. Role (from the five options above)
4. Optional: department or site (useful for larger organisations)

After you save, the user receives a welcome email with a link to set their password. The link expires after 48 hours — if a user misses it, you can resend it from the Users list.

**Important:** Each user must complete their own password setup and 2FA configuration before they can log in. You, as the Admin, never see or set passwords for other users. This is by design — it ensures that each electronic signature is uniquely traceable to the individual.

### 4.4 User Account Best Practices

- Use only individual accounts — never create shared accounts (e.g. "lab_shared"). Every action in BioNexus is attributed to the individual user; shared accounts make the audit trail meaningless and non-compliant.
- Set a password expiry policy under **Settings > Security** — 90-day expiry is the industry norm for regulated environments.
- Deactivate (do not delete) accounts when a user leaves. Deleting an account would remove the attribution from historical audit records. Deactivated accounts cannot log in but their history is preserved.
- Review the user list every six months and deactivate any accounts for staff who have changed roles or left the organisation.

---

## 5. Step 3: BioNexus Box Installation

The BioNexus Box is the physical device that connects your lab instrument to the BioNexus cloud. This section covers unpacking, physical installation, network connection, and confirming the device is online.

### 5.1 What Is in the Box

Your BioNexus Box shipment includes:

- BioNexus Box device (industrial-grade compact computer)
- Power supply (USB-C cable and adapter, or barrel-jack adapter for some models)
- Ethernet cable (1.5 m, RJ45)
- RS232 serial cable (DB9 to DB9, 1.5 m) — for serial instruments
- USB-A to USB-B cable — for USB instruments
- Quick reference card (LED status codes)
- Tamper-evident seal labels (additional set for re-sealing after configuration)

The Box ships pre-provisioned from the BioNexus factory. You do not need to install any software on it. It is ready to connect.

### 5.2 Physical Setup

**Placement:**
- Place the Box within cable reach of the instrument's RS232 or USB port
- The Box can be placed on the bench top, mounted on a DIN rail (in an electrical cabinet), or secured with the included Velcro strips
- Keep the Box away from sources of significant heat or liquids
- Ensure the ventilation slots (if present) are not obstructed
- The Box has no fan and makes no noise during normal operation

**Connections — connect in this order:**

```
Step 1: Connect the RS232 or USB cable
        Instrument <--------cable---------> BioNexus Box
        (RS232: DB9 port)                   (RS232-1 or USB-A port)

Step 2: Connect the Ethernet cable
        Network switch <----RJ45 cable----> BioNexus Box
                                            (ETH-1 port)

Step 3: Connect power
        Power outlet <---USB-C or barrel---> BioNexus Box
                                             (POWER port)
```

> **Important:** Connect the instrument cable before powering on the Box. The Box's software starts collecting data immediately on boot. If the instrument cable is connected after boot, the Box will detect it within 30 seconds, but connecting before power-on is simpler.

**Cable connection reference (RS232):**

The RS232 port on the BioNexus Box is a female DB9 connector (the 9-pin trapezoid-shaped connector). On most laboratory instruments, the RS232 port is also a DB9 but may be male. The supplied cable is a standard straight-through (not null-modem) DB9-F to DB9-M cable. If your instrument uses a DB25 connector, an adapter is available from BioNexus Support.

### 5.3 LED Status Guide

The Box has five status LEDs on the front panel. Here is what each one means:

```
+----------------------------------------------+
|   BioNexus Box — Front Panel                 |
|                                              |
|  [PWR]  [NET]  [INST]  [ERR]  [SYNC]        |
|  Green  Blue   Amber   Red    White          |
+----------------------------------------------+
```

| LED | Colour | State | Meaning |
|-----|--------|-------|---------|
| PWR (Power) | Green | Solid | Box is powered and OS is running normally |
| PWR | Green | Blinking slowly | Box is starting up (allow up to 2 minutes on first boot) |
| PWR | Off | — | No power — check cable and power supply |
| NET (Network) | Blue | Solid | Ethernet connected and internet access confirmed |
| NET | Blue | Blinking | Network connected but cloud connection not yet established |
| NET | Off | — | No network connection |
| INST (Instrument) | Amber | Solid | At least one instrument is actively sending data |
| INST | Amber | Blinking | Instrument connected but no data received yet |
| INST | Off | — | No instrument connection detected |
| ERR (Error) | Red | Off | Normal — no errors |
| ERR | Red | Blinking slowly | Non-critical warning (check dashboard for details) |
| ERR | Red | Solid | Critical error — device needs attention (contact support) |
| SYNC (Sync) | White | Blinking | Data is being uploaded to the cloud |
| SYNC | White | Solid | Data uploaded and queue is clear |
| SYNC | Off | — | No data to upload, or upload paused (check NET) |

**Normal startup sequence:**
1. PWR blinks (starting up) — approximately 60–90 seconds
2. PWR goes solid
3. NET blinks (finding network), then goes solid blue
4. SYNC blinks (sending first heartbeat to cloud)
5. INST blinks (searching for instrument), then goes solid amber when data arrives

If you reach step 4 (SYNC blinking and NET solid), your Box is online and your BioNexus onboarding specialist can see it in the management console.

### 5.4 Network Registration Confirmation

Once the Box is powered and connected:

1. Log in to the BioNexus platform at `https://app.bionexus.io`
2. Navigate to **Devices > BioNexus Boxes**
3. Your Box should appear in the list with status **Online** within 2–3 minutes of first connection
4. The device ID printed on the label on the bottom of the Box should match what appears on screen

If the Box does not appear after 5 minutes:
- Confirm the NET LED is solid blue (full network connectivity)
- Check that outbound HTTPS (port 443) to `api.bionexus.io` is not blocked by your firewall
- See the Troubleshooting section for further steps

### 5.5 Applying Tamper-Evident Seals

Once the Box is in its final position and all cables are connected:

1. Apply the tamper-evident seal stickers over the screws on the enclosure and over the USB/HDMI ports that are not in use
2. Write the installation date and your initials on the seals
3. Record the seal numbers in your site's equipment log

> **Why seals matter:** If a seal is broken without documentation, this is a physical indicator of potential tampering. The Box also logs any use of the physical reset button to the cloud audit trail. Physical security of data capture hardware is part of GxP requirements for electronic records integrity.

---

## 6. Step 4: Instrument Registration

Once your BioNexus Box is online, you register each connected instrument in the platform. This creates a permanent identity record for the instrument and tells the Box how to interpret the data it receives.

### 6.1 Adding an Instrument

Navigate to **Instruments > Add Instrument**.

Fill in the following fields:

**Instrument Identity (required):**
- Instrument name (e.g. "HPLC-01" or "Waters Alliance 2695 Lab 3") — use the same name your lab uses in other records
- Instrument type (select from the dropdown: Dissolution Tester, HPLC, UV-Vis Spectrophotometer, pH/Conductivity Meter, Balance, Karl Fischer Titrator, Environmental Monitor, Other)
- Manufacturer
- Model number
- Serial number
- Asset tag or internal inventory number (if your organisation uses one)

**Calibration Information (required for GxP):**
- Last calibration date
- Calibration due date
- Calibration certificate reference number

**Assignment:**
- Assign to BioNexus Box: select the Box it is physically connected to
- Physical port: select which port on the Box the cable is connected to (RS232-1, RS232-2, USB-1, USB-2)

### 6.2 Selecting a Parser Profile

A **parser profile** is the software configuration that tells BioNexus how to read and interpret the specific data format that your instrument outputs. Different instruments use completely different output formats — an HPLC prints results differently from a pH meter, and even two HPLC models from the same manufacturer may use different formats.

When you select an instrument type, BioNexus shows you the available parser profiles for that type. For common instruments, a pre-built profile already exists. Select the profile that matches your instrument model. If you do not see a match, select "Generic" for your instrument type and contact BioNexus Support — we build custom parser profiles as part of the onboarding service.

**Serial port parameters (for RS232 instruments):**

If the auto-detected settings are incorrect, you can set them manually. These settings must match what is configured in the instrument itself:

- Baud rate: the speed of the serial connection (most commonly 9600 for older instruments, 19200 or higher for newer ones)
- Data bits: almost always 8
- Parity: most commonly "None" (N)
- Stop bits: most commonly 1

If you are unsure, check the instrument's "Data Output" or "Serial Communication" settings screen, or the manual. These settings are also often shown on the instrument's display under Setup or Configuration menus.

### 6.3 Testing the First Data Capture

After saving the instrument configuration, BioNexus automatically pushes the configuration to the Box. Within 30–60 seconds, the Box restarts its data collection for the newly configured instrument.

To test:

1. Navigate to **Instruments > [Your Instrument Name] > Live View**
2. Trigger a measurement or print operation on the instrument (the exact action depends on your instrument — typically pressing the "Print" button, completing a run, or triggering a manual output)
3. Within a few seconds of the instrument outputting data, you should see a new reading appear in the Live View with the parsed data fields

If the instrument sends data but it appears garbled or the fields are empty:
- Confirm the correct parser profile is selected
- Confirm the serial parameters match the instrument settings
- See the Troubleshooting section

Once a reading appears correctly parsed:
- Review the extracted data fields against the instrument's own display or printout to confirm they match
- This is your first confirmation that data capture is working correctly — note the date, time, and outcome in your site's qualification records if you are conducting an IQ

### 6.4 Supported Instruments Reference

BioNexus supports the following instrument categories with pre-built parser profiles:

| Category | Examples |
|----------|---------|
| Dissolution Testers | Agilent 708-DS, Erweka DT820, Sotax AT7, Distek Premiere 5100 |
| HPLC Systems | Waters Alliance e2695, Agilent 1260 Infinity II, Shimadzu LC-20 |
| UV-Vis Spectrophotometers | Shimadzu UV-1900i, Mettler Toledo UV5Nano, Jasco V-730 |
| pH / Conductivity Meters | Mettler Toledo SevenExcellence, Hanna HI5521, Sartorius PB-10 |
| Balances | Mettler Toledo XPR206, Sartorius Cubis II, Ohaus Pioneer |
| Karl Fischer Titrators | Mettler Toledo V20S, Metrohm 851 Titrando |
| Environmental Monitors | Vaisala HMT330, Testo 176 H1 |

If your instrument is not in this list, contact BioNexus Support. Custom parser development is available as a paid service and typically takes 5–10 business days.

---

## 7. Step 5: System Configuration

Before your team begins using BioNexus for live QC data, review and configure the following system-wide settings. Most defaults are appropriate for most labs, but these areas require a deliberate QA decision.

### 7.1 Audit Trail Settings

Navigate to **Settings > Compliance > Audit Trail**.

BioNexus automatically logs every action taken in the system (data uploads, corrections, validations, certifications, logins, and administrative changes). The audit trail cannot be turned off — it is a core system requirement for regulatory compliance.

Options you can configure:

- **Chain integrity verification interval**: How often (in seconds) BioNexus automatically re-verifies the cryptographic integrity of the audit chain. Default is every 30 seconds. We recommend leaving this at the default.
- **Alert on tampering**: Who receives an immediate alert if a chain integrity failure is detected (indicating possible data tampering). Add at least the QC Manager and the System Administrator to this list.
- **Audit trail export format**: Choose JSON, CSV, or both. For regulatory submissions, JSON is preferred as it is machine-verifiable.

> **What is chain integrity?** Every audit record in BioNexus contains a digital fingerprint (SHA-256 hash) that is calculated from both the content of the current record and the fingerprint of the previous record. This creates a chain — if anyone changes a historical record, all the fingerprints after it become invalid, and BioNexus immediately detects the discrepancy. This is similar to how blockchain technology works, but purpose-built for regulatory record-keeping.

### 7.2 Notification Preferences

Navigate to **Settings > Notifications**.

Configure when and how BioNexus sends alerts:

| Alert type | Recommended recipients |
|-----------|----------------------|
| Box offline (5+ minutes) | Lab IT Admin, QC Manager |
| Box offline (30+ minutes) | Lab IT Admin, QC Manager, Operations Manager |
| Instrument silent (no data for unexpected period) | QC Manager, responsible Technician |
| Audit chain integrity failure | QC Manager, Lab IT Admin, QA Director |
| New certified report generated | PI who certified + configured distribution list |
| User login from new device or location | IT Admin, affected user |
| Calibration due date approaching (30/14/7 days) | QC Manager, instrument owner |

Notifications can be sent by email. Webhook notifications (for integration with Slack, Teams, or a ticketing system) are available on the Professional and Enterprise plans.

### 7.3 Data Retention Policy

Navigate to **Settings > Compliance > Data Retention**.

BioNexus stores all data in accordance with regulatory requirements. You should configure the following to match your organisation's data retention policy and local regulatory obligations:

- **Raw data retention**: How long raw instrument output is kept (minimum recommended: 5 years for 21 CFR Part 11 environments; 10 years is common in EU GMP)
- **Certified report retention**: How long certified reports are retained (we recommend matching or exceeding your product dossier retention requirement — often 15+ years for approved products)
- **Audit trail retention**: Cannot be set below the system minimum (7 years). Regulation requires audit trail records to be retained for as long as the associated data.
- **User account history**: Retained permanently (deactivated accounts are never fully deleted)

> **Important:** Once a certified report is created, it is permanently immutable — it cannot be modified or deleted, even by an Admin. The raw data and audit trail can only be deleted by an Admin after the configured retention period expires, and any such deletion is itself logged in a separate administrative audit trail.

### 7.4 Electronic Signature Policy

Navigate to **Settings > Compliance > Electronic Signatures**.

BioNexus supports two certification methods. Confirm with your QA team which is appropriate for your validation status:

**Method 1: Password + One-Time Code (default)**
The certifying PI enters their password and a one-time code sent to their registered email or authenticator app. This meets 21 CFR Part 11 requirements for electronic signatures using a combination of an identification code and a password.

**Method 2: Password + Authenticator App OTP**
Uses the same principle but the one-time code comes from an authenticator app (TOTP — Time-based One-Time Password) rather than email. This is faster and recommended for high-volume labs.

Both methods create a non-repudiable signature record: the system records that a specific named user, after verifying their identity twice, explicitly certified the accuracy of a specific record at a specific date and time.

### 7.5 Compliance Profile

Navigate to **Settings > Compliance > Regulatory Profile**.

Select the regulations under which your lab operates:
- FDA 21 CFR Part 11 (US regulated pharmaceutical)
- EU Annex 11 (European GMP)
- Both (for globally operating organisations)

Selecting a compliance profile activates the corresponding validation rules and adds relevant regulatory references to exported reports. It also affects the compliance score calculation shown on certified reports.

---

## 8. Step 6: First Data Workflow

This section walks you through the complete data workflow from data capture to certified report. It is the most important section for Lab Technicians and PIs to read together before go-live.

### Overview of the Data Journey

```
[Instrument] --> [BioNexus Box] --> [Upload/Ingest] --> [AI Parsing]
                                                             |
                                                             v
[Certified Report] <-- [PI Certification] <-- [Technician Review & Correction]
```

There are four stages for each data record:

| Stage | Label | Who acts |
|-------|-------|---------|
| 1. Raw | Data received, not yet processed | System (automatic) |
| 2. Parsed | Data extracted and ready for review | System (automatic) |
| 3. Validated | Human review complete | Lab Technician |
| 4. Certified | Electronically signed by PI | Principal Investigator |

### 8.1 Data Arrives (Automatic)

When your instrument outputs data, the BioNexus Box captures it within seconds and uploads it to the platform. You can also manually upload data files (PDF or CSV) if, for example, you have historical data or an instrument that is not yet connected to a Box.

**Manual upload:**
1. Navigate to **Data > Upload File**
2. Select your PDF or CSV file
3. Choose the instrument the data came from
4. Click **Upload**

**Automatic capture (via BioNexus Box):**
No action required. The data appears automatically in your **Data > Pending Review** queue.

### 8.2 Reviewing Parsed Data (Lab Technician)

Navigate to **Data > Pending Review** and click on the new record.

The validation screen is divided into two halves:

**Left panel: Original file**
Shows the raw data exactly as it came from the instrument — the original machine output. You can see the printout, CSV table, or raw text. This view is read-only and permanent. It is your reference for checking the AI's interpretation.

**Right panel: Validation form**
Shows the data fields that the AI has extracted and labelled. Each field has a colour indicator:
- **Green background**: AI extracted this value with high confidence
- **Yellow background**: AI is less certain — pay extra attention to these fields

**How to review:**
1. Work through each field in the right panel, comparing it visually with the original data in the left panel
2. For fields marked yellow, verify carefully that the extracted value matches the original
3. If a field is incorrect, click the edit icon next to it

**Making a correction:**
When you click to edit a field, you will be prompted for:
- The corrected value
- A reason for the correction (required — e.g. "AI misread decimal point" or "Unit format standardised")

Every correction is automatically logged in the audit trail with your name, timestamp, the original value, and the corrected value. You cannot delete a correction once it is made — you can only make further corrections. This preserves a full history of every change.

**The Correction Tracker panel** (below the form) shows all corrections made to this record so far:

```
Corrections Made (2)
--------------------
Field: equipment_name
  Original:  "Spectrophotometre A"
  Corrected: "Spectrophotometer A"
  Reason:    Typo in instrument output
  By:        j.smith @ 14:35:22

Field: sample_volume
  Original:  "50mL"
  Corrected: "50 mL"
  Reason:    Format standardisation
  By:        j.smith @ 14:36:05
```

**Compliance score badge:**

In the top right corner of the validation screen, you will see a badge showing the current compliance score for this record (e.g. "CONF: 84% | Chain Verified | GxP v2.1"). This score increases as you complete the review steps. A score above 90% is typically expected before certification.

The "Chain Verified" indicator confirms that the audit trail for this record has not been tampered with. If it ever shows "Chain FAILED", stop work and contact your Lab IT Admin immediately.

**Submitting for PI review:**
When you have reviewed all fields and made all necessary corrections, click **Submit for Certification**. Add a brief note (e.g. "All fields verified. 2 corrections documented.") and confirm. The record moves to the PI's certification queue. You can no longer edit it.

### 8.3 Certifying the Record (Principal Investigator)

Navigate to **Data > Awaiting Certification** and click on the record.

**The PI sees:**
- The same split-view screen as the Technician
- All corrections made and the reason for each
- The compliance score
- The full audit trail for this record

**Before certifying, the PI should:**
1. Confirm the original data in the left panel looks complete and authentic
2. Review all corrections and their documented reasons — if any correction appears incorrect or the reason is insufficient, the PI should send the record back to the Technician with comments
3. Confirm the compliance score is acceptable
4. Confirm the "Chain Verified" badge is showing

**The certification process (three steps):**

When the PI is satisfied, click **Certify for Audit**. A dialog box opens:

**Step 1 — Re-enter your password:**
You are asked to type your current password again. This is not an error — it is intentional. The system is confirming that you, the authorised PI, are personally present at the keyboard at this moment. This prevents accidental certification or certification by someone using an unattended logged-in session.

**Step 2 — Enter your one-time code:**
A six-digit code is sent to your registered email address or authenticator app. Enter it in the dialog. This code is valid for 10 minutes and can only be used once.

**Step 3 — Review and confirm:**
A final summary shows:
- The record ID
- The date and time of certification
- Your name as certifier
- A declaration: "I certify that I have reviewed this data record and that it is accurate and complete to the best of my knowledge."

Click **I Certify** to complete the process.

> **Why double authentication?** 21 CFR Part 11 (Section 11.200) requires that electronic signatures used for certification of records in regulated environments must employ at least two distinct identification components (such as an identification code and a password). The PI's password verifies who they are; the one-time code verifies they are present and in control of their registered device or email. This two-factor approach prevents anyone from certifying a record using someone else's credentials, even if they have stolen that person's password.

### 8.4 The Certified Report

After certification, BioNexus automatically generates:

**An immutable certified report containing:**
- All data fields (original and corrected)
- A record of every correction with reason, author, and timestamp
- The complete audit trail for this record
- The certifying PI's name, timestamp, and signature identifier
- A SHA-256 hash (digital fingerprint) of the entire report
- A QR code linking to the live chain verification endpoint
- The compliance score and GxP version

**A PDF report** available for download from **Data > Certified Reports > [Record ID] > Download PDF**. This PDF can be printed or shared for inspection purposes. The QR code on the PDF allows an auditor to verify the report's authenticity at any time by scanning it.

**A confirmation screen** showing:

```
Record Certified

Report ID:      RPT-2026-00045
Certified by:   Dr. A. Johnson
Date/Time:      2026-02-28 14:35:22 UTC
Report Hash:    a4f9e2d1c8b7...
Chain Status:   Verified
Compliance:     94%

[Download PDF]    [View Full Audit Trail]
```

The certified report is now permanent. It cannot be modified, deleted, or superseded. If a subsequent review reveals an error, a new data record must be created and certified — the original remains in the system as a historical record.

---

## 9. Step 7: Qualification and Go-Live

### 9.1 Do You Need Formal Qualification?

If your lab operates under a validated computer system requirement (common in pharmaceutical manufacturing, QC release testing for drug products, or any GMP environment subject to Annex 11 or 21 CFR Part 11), you may be required to formally qualify BioNexus before using it for official QC data.

**Qualification is typically required if:**
- Your lab releases pharmaceutical products (API or finished product)
- Your organisation has a Computer System Validation (CSV) policy
- Your GMP auditors have previously noted computerised systems on your validation list
- Your qualified person (QP) or regulatory affairs team requires it

**Qualification may not be required if:**
- You are using BioNexus only for non-GMP research or development
- Your organisation's CSV policy explicitly excludes cloud-hosted data capture tools below a certain risk tier
- You are in a discovery or pilot phase

If you are unsure, consult your QA team or contact your BioNexus account manager.

### 9.2 Working with GMP4U for IQ/OQ/PQ

BioNexus works with **GMP4U** (qualification specialist partner: Johannes Eberhardt) to support formal validation at customer sites. GMP4U provides:

- **IQ (Installation Qualification)** — documents that BioNexus is installed correctly, the BioNexus Box is operating as specified, and all user accounts are configured per the approved design
- **OQ (Operational Qualification)** — formal testing that BioNexus functions as specified: data capture, audit trail, correction tracking, double-authentication certification, chain integrity verification, report generation
- **PQ (Performance Qualification)** — testing that BioNexus performs correctly in your specific laboratory environment with your specific instruments and typical data sets

GMP4U delivers a complete validation package including:
- Validation Plan
- User Requirements Specification (URS)
- Functional and Design Specifications (FS/DS)
- IQ/OQ/PQ test protocols and executed test evidence
- Validation Summary Report

Contact your BioNexus account manager to arrange a qualification scoping call with GMP4U. Timelines typically range from 2–6 weeks depending on the number of instruments and your site's documentation requirements.

### 9.3 Go-Live Checklist

Work through this checklist before authorising live QC use of BioNexus:

**Technical readiness:**
- [ ] All BioNexus Boxes are online and showing NET and PWR LEDs solid
- [ ] All instruments are registered and data capture is confirmed (INST LED solid amber, live readings visible in dashboard)
- [ ] All user accounts created, passwords set, and 2FA configured
- [ ] System Admin has tested creating a user, deactivating a user, and resetting a password
- [ ] Notification emails have been tested and are arriving correctly
- [ ] A complete test workflow (upload → review → correct → validate → certify → download PDF) has been performed successfully by at least one PI and one Technician

**Compliance readiness:**
- [ ] Data retention policy has been reviewed and configured
- [ ] Electronic signature method has been confirmed with QA team
- [ ] Audit trail export has been tested and the output format accepted by your QA team
- [ ] Tamper-evident seals have been applied to all BioNexus Boxes
- [ ] Instrument calibration records are up to date in BioNexus
- [ ] (If required) Qualification documentation is completed and signed

**Training:**
- [ ] Lab Technicians have been trained on the upload and review workflow
- [ ] PIs have been trained on the certification process
- [ ] Auditors (if applicable) have been trained on accessing the audit trail and certified reports
- [ ] Training records are documented (date, attendee names, content covered)

**Go-live:**
- [ ] QA Manager has formally signed off on go-live
- [ ] A "go-live date" has been recorded — this becomes the start of your validated use period
- [ ] Support contact details are posted in the lab

---

## 10. Day-to-Day Operations

### For Lab Technicians — Daily Workflow

**Morning (start of shift):**
1. Log in to BioNexus at `https://app.bionexus.io`
2. Check **Devices > BioNexus Boxes** — confirm your Box(es) show "Online" status
3. Confirm instrument LEDs on the Box(es) are solid amber (instruments active)
4. Check **Data > Pending Review** for any records from overnight that need attention

**After each instrument run:**
1. Navigate to **Data > Pending Review** — the new record should appear within 60 seconds of the instrument completing its output
2. Open the record and work through the validation form:
   - Compare each parsed field against the instrument's own display or printout
   - Correct any fields that are wrong, with a documented reason
3. When all fields are verified, click **Submit for Certification**
4. Add a brief summary note and click **Confirm**

**End of shift:**
1. Confirm all records from your shift are in "Awaiting Certification" or "Certified" status
2. No records should remain in "Pending Review" unless you have a documented reason to defer them

**If you need to manually upload a file:**
1. Navigate to **Data > Upload File**
2. Select the file and the correct instrument
3. Click **Upload** — the record will appear in Pending Review within 60 seconds

### For Principal Investigators — Certification Workflow

**Checking for records awaiting certification:**
1. You will receive an email notification when a Technician submits a record for certification
2. You can also check **Data > Awaiting Certification** at any time

**Certifying a record:**
1. Open the record and review the Technician's work
2. Check the original file (left panel) against the validated data (right panel)
3. Read each correction and its documented reason — if anything is unclear, use the Comments feature to ask the Technician before certifying
4. If everything is correct, click **Certify for Audit** and complete the three-step certification process (password + one-time code + explicit confirmation)
5. Download the PDF if you need a copy for a site file or for forwarding

**Sending a record back to the Technician:**
If the Technician's work is incomplete or a correction is undocumented, you can click **Return to Technician** with a comment explaining what needs to be addressed. The record goes back to the Technician's queue with your comment visible. This return is logged in the audit trail.

### For Auditors — Inspection and Review Workflow

**Viewing the audit trail:**
1. Navigate to **Audit Trail** in the main menu
2. Use filters to narrow by date range, instrument, user, record type, or operation type
3. Every row shows: timestamp, user who performed the action, what changed (before and after values), and the cryptographic signature

**Verifying chain integrity:**
1. Navigate to **Audit Trail > Chain Integrity Verification**
2. Click **Run Verification** — this recalculates all SHA-256 fingerprints in the chain and confirms no record has been modified
3. A report shows: total records checked, date range, result (Pass/Fail), and details of any anomalies

**Exporting the audit trail for inspection:**
1. Navigate to **Audit Trail > Export**
2. Select the date range and record types you want
3. Choose format (JSON recommended for full verifiability; CSV for readability)
4. Click **Export** — a certified export file is generated with a digital signature over the entire export, confirming it has not been modified since download

**Verifying a certified report:**
1. Open any certified report and note the Report Hash (the long string of letters and numbers at the top)
2. Navigate to **Reports > Verify Report** and enter the Report ID or hash
3. The system confirms whether the hash on record matches the hash in the report, and whether the audit chain for that record is intact

### For System Administrators — Administrative Tasks

**Monthly tasks:**
- Review active user accounts and deactivate any for staff who have left or changed roles
- Review the audit trail export for any unusual activity patterns
- Check that all instrument calibration due dates are current (navigate to **Instruments** and look for yellow or red calibration indicators)
- Confirm all BioNexus Boxes have updated to the latest firmware (navigate to **Devices > Firmware**)

**When a staff member leaves:**
1. Navigate to **Settings > Users**
2. Find the user and click **Deactivate** (not Delete)
3. The user immediately loses login access but all their historical actions remain attributed to them in the audit trail

**When a new instrument is added:**
Follow Step 4 (Instrument Registration) in this guide.

**When a BioNexus Box needs to be replaced:**
Contact BioNexus Support before physically swapping a Box. The replacement Box must be provisioned by BioNexus and registered to your tenant. Do not attempt to configure a new Box independently — the provisioning process includes security credentials that must be issued by BioNexus.

---

## 11. Troubleshooting

### Box Connectivity Issues

**Problem: Box NET LED is off (no network)**

Check the following in order:
1. Confirm the Ethernet cable is firmly plugged in at both ends (Box and network switch/wall port)
2. Try a different Ethernet cable (cables can fail)
3. Confirm the network port is active — connect a laptop to the same port and check for internet access
4. If you are using a managed switch with port security (MAC address filtering), the Box's MAC address needs to be permitted. The MAC address is printed on the label on the bottom of the Box.
5. If your network requires a static IP assignment, contact BioNexus Support — the Box uses DHCP by default but can be configured with a static IP via the management console

**Problem: Box NET LED is blue but Box does not appear as Online in the dashboard**

The Box has a network connection but cannot reach `api.bionexus.io`. Check:
1. Does your network use an outbound proxy? If so, proxy configuration is needed — contact BioNexus Support.
2. Is the firewall blocking outbound HTTPS to external addresses? Ask IT to whitelist `api.bionexus.io` (TCP port 443).
3. Is DNS resolution working? From a PC on the same network, try opening `https://api.bionexus.io` in a browser — if you get a response (even an error page), DNS and firewall are working.

**Problem: Box was online, now shows Offline**

1. Check the Box physically — is it powered (PWR LED solid green)?
2. Check the network cable and switch port
3. If the Box has been offline for more than 30 minutes, you should receive an automatic alert email (if notification contacts are configured)
4. The Box stores data locally while offline and will upload automatically when connectivity is restored — no data is lost in typical outages of up to several weeks

### Parsing and Data Quality Issues

**Problem: A record shows garbled or missing data fields**

The most common cause is a mismatch between the parser profile and the instrument's actual output format.
1. Navigate to the record and click **View Raw File** in the left panel — check what the raw instrument output actually looks like
2. Navigate to **Instruments > [Instrument Name] > Edit** and confirm the correct parser profile is selected
3. If the output format looks different from what you expect (unusual characters, different column order), contact BioNexus Support with a screenshot of the raw file — we will create or update the parser profile

**Problem: Fields are consistently wrong in the same way**

For example, the instrument name always has a typo, or a measurement unit is always missing. You have two options:
1. Continue correcting each record manually (the correction is logged, which is compliant)
2. Contact BioNexus Support to adjust the parser profile or create a field transformation rule — this eliminates the systematic error at source

**Problem: AI parsing confidence is always low (many yellow fields)**

Low AI confidence is most common when instrument output is formatted inconsistently (e.g. different column headers on different days, or output that varies based on instrument settings). Contact BioNexus Support — additional AI training on your specific instrument's output format can significantly improve confidence scores.

### Login and Authentication Issues

**Problem: A user cannot log in**

1. Ask the user to use the "Forgot Password" link on the login page
2. If they cannot receive the password reset email, check their email address is correct in **Settings > Users**
3. If 2FA is failing, an Admin can reset the user's 2FA from **Settings > Users > [User Name] > Reset 2FA** — the user will be prompted to re-enrol at next login

**Problem: A user's one-time code for certification is not working**

1. Confirm the user's email is receiving the code (check spam/junk folder)
2. One-time codes expire after 10 minutes — if it has been longer than that, request a new code by closing and reopening the certification dialog
3. If using an authenticator app, confirm the app's clock is synchronised (time drift causes TOTP failures) — on most phones, go to the authenticator app settings and select "Sync time"

**Problem: A user is locked out after too many failed password attempts**

Account lockouts release automatically after 30 minutes, or an Admin can immediately unlock the account from **Settings > Users > [User Name] > Unlock Account**.

### Audit Trail Questions

**Problem: An auditor asks about a gap in the data (no readings for a period)**

1. Navigate to **Devices > [Box Name] > Offline History** — this shows any periods when the Box was offline
2. Navigate to **Audit Trail** and filter by the instrument and date range — the audit trail will show any error events, including "Instrument silent" warnings
3. If the gap corresponds to a known network outage, the audit trail will show the offline period, the reconnection event, and the backlog upload
4. If the gap is unexplained, escalate to your QA team and BioNexus Support for investigation

**Problem: The chain integrity verification shows a failure**

This is a serious compliance event. Do not dismiss the alert.
1. Stop any active data processing on the affected records
2. Contact BioNexus Support immediately (use the emergency contact in Section 13)
3. Document the time you discovered the alert, the records affected, and any actions taken
4. Do not attempt to resolve this independently — forensic investigation is required

In practice, chain integrity failures are almost always caused by a system bug or a database migration issue, not deliberate tampering — but the appropriate response is the same either way: escalate and investigate.

---

## 12. Frequently Asked Questions

**Q: Can we use BioNexus without the BioNexus Box? We just want to upload CSV files manually.**

Yes. You can use BioNexus as a pure upload-and-review platform without any hardware. Upload CSV or PDF files directly from the **Data > Upload File** screen. The full audit trail, correction tracking, and certification workflow apply to manually uploaded files in exactly the same way as Box-captured data.

**Q: What happens to our data if BioNexus shuts down or we cancel our subscription?**

You own your data. BioNexus provides data export tools that allow you to download all your records — raw files, parsed data, corrections, certified reports, and the complete audit trail — in standard JSON and PDF formats. We recommend performing a full data export at least quarterly and storing it in your own secure archive. Before cancelling, your contract includes a 90-day data access window for full export.

**Q: Can a certified record be changed or deleted?**

No. Once a record is certified, it is permanently immutable. Not even a System Administrator can modify or delete it. This is a deliberate design choice — 21 CFR Part 11 and EU Annex 11 both require that certified electronic records cannot be modified without detection. If a certified record is found to contain an error, the correct procedure is to create a new record, document the reason for supersession, and certify the corrected version. Both records remain in the system permanently.

**Q: We have multiple lab sites. Can we use one BioNexus account for all sites?**

Yes, with caveats. Each site can have its own tenant (completely isolated data) or you can use a single tenant with location-based filtering. For most GxP environments, separate tenants per site are preferable because they enforce a cleaner data isolation boundary and simplify site-specific audit and inspection activities. Consult your QA team on which structure suits your organisation's validation scope.

**Q: What happens if the BioNexus Box loses power during a data capture?**

The Box uses a database storage mode (SQLite with Write-Ahead Logging) specifically designed to survive unexpected power loss without data corruption. Any reading that was fully received before the power cut is preserved and will upload when power is restored. Any reading that was in the process of being received at the moment of power cut may be incomplete and will be flagged as an error in the audit trail — it will not be silently lost or silently uploaded as a partial record.

**Q: How do we handle instrument maintenance periods when no data is expected?**

Navigate to **Instruments > [Instrument Name] > Schedule Maintenance Window** and enter the planned start and end time. During this window, the "instrument silent" alert will be suppressed. The maintenance window is recorded in the instrument's audit history. If the maintenance runs longer than planned, extend the window from the same screen.

**Q: What patient data does BioNexus store?**

None. BioNexus is designed to capture instrument measurements associated with sample IDs — not patient identities. Sample IDs should be pseudonymised reference codes (e.g. "QC-2026-00451") that have no direct link to patient information. BioNexus is not a clinical data system and should not be used to store data that could identify individual patients.

**Q: Can we integrate BioNexus with our existing LIMS?**

BioNexus provides a REST API that allows certified reports and audit trail data to be read by external systems. Direct integration with specific LIMS platforms (LabWare, STARLIMS, Benchling, etc.) is available as a professional services engagement. Contact your account manager for details.

**Q: Is BioNexus validated? Do we need to validate it ourselves?**

BioNexus is developed according to GAMP5 Category 4/5 software development practices. We provide a complete supplier qualification package including design specifications, test evidence, and a Supplier Qualification Report. For most customers, this package — combined with your site-level IQ/OQ/PQ — constitutes the full validation evidence required under Annex 11 and 21 CFR Part 11. Contact your account manager to receive the supplier qualification package.

**Q: What is the difference between the compliance score percentage on each record and being "compliant"?**

The compliance score (shown as a percentage on each record) reflects how completely that specific data record follows the BioNexus compliance workflow: audit trail entries created, corrections documented, chain integrity verified, validation completed, and certification completed. A score of 100% means every expected step was followed for that record. A score of 70% might mean the data was uploaded and certified but there were no corrections documented (which may indicate the review step was rushed rather than genuinely correction-free). The compliance score is a quality indicator, not a regulatory pass/fail gate — your QA team should set internal thresholds and review any records below the threshold.

---

## 13. Support and Contact

### How to Get Help

**In-app help:**
Click the **?** icon in the top right corner of any screen to open contextual help for the section you are in. Most screens have a "Learn more" link that opens relevant documentation.

**Support portal:**
For non-urgent questions, feature requests, and bug reports, open a ticket at `https://support.bionexus.io`. Include:
- Your organisation name and tenant ID (shown in **Settings > Organisation**)
- A description of the issue
- The record ID, instrument ID, or device ID affected (where relevant)
- Screenshots if available

**Email support:**
For questions not requiring immediate resolution: `support@bionexus.io`

**Phone support:**
For urgent production issues (Box completely offline, data loss risk, chain integrity alerts): call the support line provided in your contract. Phone support is available during business hours Monday–Friday. After-hours emergency support is available for Critical priority issues.

### Service Level Expectations

| Priority | Definition | Initial Response | Resolution Target |
|---------|-----------|-----------------|------------------|
| Critical | Complete service outage, data loss risk, chain integrity failure | 1 hour | 4 hours |
| High | Key workflow blocked, Box offline with pending data, login failures affecting operations | 4 hours | 1 business day |
| Medium | Individual feature not working, parsing errors, non-blocking issues | 1 business day | 3 business days |
| Low | Questions, configuration help, feature requests | 2 business days | Roadmap/backlog |

Critical and High priority issues are escalated automatically to senior support engineers. You do not need to request escalation — your ticket's priority level determines it.

### Your BioNexus Team

Every customer has a named account manager and a customer success manager:

- **Account Manager** — commercial questions, subscription changes, professional services
- **Customer Success Manager** — onboarding, training, qualification support, best practice guidance

Your account manager's contact details are in your welcome email and in the BioNexus platform under **Settings > Support > My Account Team**.

### Qualification and Compliance Support

For questions specifically relating to regulatory compliance, validation documentation, or audit preparation:
- Contact GMP4U directly via `qualification@gmp4u.com` (reference your BioNexus account)
- Or route through your BioNexus customer success manager who can arrange a qualification consultation call

---

## 14. Appendix: Regulatory Rationale

This appendix is intended for QA teams, Qualified Persons, and regulatory affairs staff who want to understand the compliance logic behind specific BioNexus design decisions. It answers the question "why does BioNexus work this way?" rather than "how do I use it?"

### 14.1 Why Records Cannot Be Deleted

**Regulation:** 21 CFR Part 11.10(e) requires that systems protect records to enable accurate and ready retrieval throughout the records retention period. EU Annex 11 Clause 7.1 requires that data is stored to prevent corruption and data loss throughout the retention period.

**BioNexus implementation:** Certified records are stored in an append-only system. The `CertifiedReport` model in the database has no delete endpoint at the application layer. Even database-level access (which only BioNexus infrastructure engineers have) uses an additional authorisation layer that logs and alerts on any deletion attempts. The SHA-256 chain means that any record that was part of the chain before deletion would cause all subsequent records to fail chain verification — making deletion immediately detectable.

### 14.2 Why Every Correction Requires a Documented Reason

**Regulation:** 21 CFR Part 11.10(e) requires audit trails that include the date and time of operator entries and actions, and any changes made. FDA's data integrity guidance (2018) specifically states that corrections should be documented with the reason for the change, the date, and the identity of the person making the change. EU Annex 11 Clause 9 requires audit trails to capture changes to data.

**BioNexus implementation:** The `CorrectionTracker` model requires a non-empty reason field for every field change. The UI makes it impossible to save a correction without entering a reason. This is not a courtesy prompt — the reason field is a mandatory field at the database level.

### 14.3 Why Certification Requires Double Authentication

**Regulation:** 21 CFR Part 11.200(a)(1) requires that electronic signatures not based on biometrics employ at least two distinct identification components such as an identification code and a password. This applies to electronic signatures used to indicate that an individual has reviewed, approved, or certified a record.

**BioNexus implementation:** The certification process requires the certifying user to provide both their password (something they know) and a one-time code delivered to a registered device or email (something they have). The one-time code is single-use and time-limited (10 minutes). Both components are verified server-side before the signature is created. The audit trail records the certification method used (password+OTP) alongside the certified record, making the signature method verifiable during an audit.

### 14.4 Why Audit Trail Records Are Cryptographically Chained

**Regulation:** FDA's data integrity guidance emphasises that audit trails must be protected from unauthorised modification. EU GMP Annex 11 Clause 9 states that audit trails should be regularly reviewed. MHRA's data integrity guidance (2018) notes that audit trails must be protected from modification and available for review.

**BioNexus implementation:** Each audit log record contains a SHA-256 hash that is computed from the content of the current record combined with the hash of the previous record. This creates a chain where any modification to a historical record breaks the hash relationship to all subsequent records — the tamper is immediately detectable by recalculating the chain. The chain is automatically verified every 30 seconds in the background. An auditor or QA manager can manually trigger a full chain verification at any time, and the result is itself logged. This provides continuous, automated assurance of audit trail integrity without relying solely on database access controls.

### 14.5 Why Each User Must Have a Unique Account

**Regulation:** 21 CFR Part 11.300(b) requires that only genuine owners of identification codes and passwords use them. 21 CFR Part 11.100(a) requires that each electronic signature be unique to one individual and not reused by or reassigned to anyone else. EU Annex 11 Clause 12.1 requires that access control prevents unauthorised persons from accessing data.

**BioNexus implementation:** The system enforces one-account-per-person by requiring email addresses as unique identifiers (no two accounts can share an email). Shared accounts would make the audit trail attributions meaningless — "lab_shared uploaded this file" tells an auditor nothing about who actually did it. Shared accounts also make it impossible to implement per-user password rotation, account lockout on suspicious activity, or differential role assignments based on individual competencies.

### 14.6 Why the BioNexus Box Hashes Data Before Transmission

**Regulation:** 21 CFR Part 11.10(c) requires that computer-generated audit trails include sufficient information to reconstruct the original data. Data integrity guidance from multiple regulators requires that the original, unmodified record be preserved.

**BioNexus implementation:** The Box computes a SHA-256 hash of the raw instrument bytes before they leave the instrument connection. This hash travels with the data all the way to the cloud and is stored alongside the raw data. At any point, any party can take the raw bytes on record and re-compute the hash to confirm they have not been modified. The parsed/interpreted data (what the AI extracted) is stored separately from and linked to the raw bytes — the raw bytes cannot be changed without breaking the hash check. This ensures that what is stored in the cloud is exactly what came out of the instrument.

### 14.7 Why Tamper-Evident Seals Are Applied to the Box

**Regulation:** EU GMP Annex 11 Clause 12.1 and FDA 21 CFR Part 11 both require physical and logical access controls to ensure that only authorised persons can use systems that create, modify, or certify regulated records. Physical security of data capture hardware is part of the overall control framework.

**BioNexus implementation:** The BioNexus Box's data originates at its physical connection to the instrument. If an unauthorised person could physically access the Box and substitute a different device, falsified data could be introduced into the record stream. Tamper-evident seals provide a simple visual indicator that the Box has not been opened or substituted. The Box also logs any use of the physical reset button to the cloud audit trail (even before the reboot executes), providing a logged record of physical interventions. For higher-security environments, the Box supports chassis intrusion switch wiring that creates a cloud alert if the enclosure is opened.

### 14.8 Why Accounts Are Deactivated Rather Than Deleted

**Regulation:** 21 CFR Part 11.10(e) requires that the identity of the operator making an entry be captured in the audit trail. FDA's data integrity guidance states that the attribution of actions to specific individuals must be maintained throughout the record's retention period.

**BioNexus implementation:** If a user account were deleted, the audit trail records associated with that user would lose their attribution — the system could no longer definitively state who performed those actions. By deactivating rather than deleting, the account information is retained indefinitely, the user cannot log in, and all historical audit attributions remain intact. An auditor reviewing records from 10 years ago can still see the full name and role of every person who touched each record, even if those individuals left the organisation years earlier.

---

*BioNexus Customer Onboarding Guide — Document ID BNX-CG-001 — Version 1.0 — 2026-02-28*

*Questions about this guide? Contact your Customer Success Manager or email `support@bionexus.io`*
