# BioNexus Box — Hardware Gateway Architecture

## Document Information

**Document ID:** BNX-HW-001
**Version:** 1.0
**Status:** Draft — Engineering Reference
**Date:** 2026-02-28
**Prepared by:** BioNexus Engineering Team
**Review Partner:** GMP4U (Johannes Eberhardt) — CSV/Qualification Specialist
**Classification:** Internal Engineering — Restricted Distribution

---

## Table of Contents

1. [Overview](#1-overview)
2. [Hardware Specifications](#2-hardware-specifications)
3. [Supported Instrument Interfaces](#3-supported-instrument-interfaces)
4. [Supported Instruments](#4-supported-instruments)
5. [Software Architecture](#5-software-architecture)
6. [Communication Protocol](#6-communication-protocol)
7. [Data Flow](#7-data-flow)
8. [Offline and Disconnected Mode](#8-offline-and-disconnected-mode)
9. [Security Model](#9-security-model)
10. [Firmware Update Strategy](#10-firmware-update-strategy)
11. [Deployment and Provisioning](#11-deployment-and-provisioning)
12. [Monitoring and Diagnostics](#12-monitoring-and-diagnostics)
13. [GxP Compliance Considerations](#13-gxp-compliance-considerations)
14. [Physical and Environmental Requirements](#14-physical-and-environmental-requirements)
15. [Roadmap](#15-roadmap)

---

## 1. Overview

### 1.1 What Is the BioNexus Box?

The BioNexus Box is a purpose-built, industrial-grade hardware gateway device that bridges the gap between legacy laboratory instruments and the modern BioNexus cloud platform. It is a compact, fan-less, Linux-based single-board computer (SBC) enclosed in a DIN-rail-mountable or bench-top enclosure, designed to operate continuously in quality control laboratory environments.

The Box connects to one or more laboratory analyzers via RS232 serial or USB interfaces, captures raw instrument output in real time, and transmits it securely to the BioNexus GCP backend over HTTPS. It is the foundational component that makes BioNexus's "Plug and Play" promise possible.

### 1.2 The Problem It Solves

Quality control laboratories in pharmaceutical and biotechnology SMBs face a persistent, costly, and high-risk problem: the manual transcription of instrument data.

Instruments such as dissolution testers, HPLC systems, spectrophotometers, and pH/conductivity meters produce results continuously. These results are typically:

- Printed on paper and manually transcribed into a LIMS or spreadsheet
- Exported via proprietary vendor software requiring expensive workstation licenses
- Subject to transcription errors that compromise data integrity
- Not captured with contemporaneous electronic audit trails, violating 21 CFR Part 11

The BioNexus Box eliminates this transcription step entirely. It sits between the instrument and the network, capturing data at the source the moment the instrument outputs it, and creating an immutable, timestamped, cryptographically verified record in the cloud.

### 1.3 Why It Exists — Strategic Context

BioNexus's primary competitive differentiator versus LabWare LIMS, STARLIMS, and Benchling is the combination of Plug and Play hardware with SaaS software. Enterprise LIMS implementations typically require 12 to 18 months of integration work, custom scripting, and six-figure consulting fees. The BioNexus Box compresses this to a same-day installation:

1. Ship the Box to the customer site
2. Customer plugs it into the instrument's RS232/USB port and their network
3. A BioNexus technician completes cloud registration remotely in under one hour
4. Data flow begins immediately

This model targets QC labs in pharma/biotech SMBs (50–500 employees) who cannot afford or justify an enterprise LIMS deployment, but still operate under 21 CFR Part 11 and EU Annex 11 obligations.

### 1.4 High-Level Architecture Position

```
+------------------+     RS232/USB     +------------------+     HTTPS/TLS 1.3    +----------------------+
|                  |                   |                  |                      |                      |
|  Lab Instrument  +------------------>+  BioNexus Box    +--------------------->+  GCP Backend         |
|  (Analyzer)      |                   |  (Edge Gateway)  |                      |  (BioNexus Platform) |
|                  |                   |                  |                      |                      |
+------------------+                   +------------------+                      +----------+-----------+
                                              |                                             |
                                    Local SQLite buffer                          +----------+-----------+
                                    (store-and-forward)                          | Django REST API      |
                                    SHA-256 packet hashing                       | PostgreSQL           |
                                    Device cert auth                             | Audit Trail          |
                                    Offline operation                            | RawFile ingestion    |
                                                                                 +----------------------+
```

---

## 2. Hardware Specifications

### 2.1 Primary Platform — Raspberry Pi CM4 (Compute Module 4)

The recommended production platform for BioNexus Box v1.0 is the **Raspberry Pi Compute Module 4 (CM4)** mounted on a custom or third-party carrier board. The CM4 was selected over a full Raspberry Pi 4B for its industrial suitability: it omits the exposed full-size USB and HDMI ports of the development board, integrates eMMC storage (no SD card to fail), and is available in industrial temperature variants.

| Parameter | Specification |
|-----------|---------------|
| **SBC** | Raspberry Pi CM4 (CM4004032 or CM4104032) |
| **CPU** | Broadcom BCM2711, quad-core Cortex-A72 (ARM v8), 1.5 GHz |
| **RAM** | 4 GB LPDDR4-3200 |
| **Storage** | 32 GB eMMC (onboard, no SD card) |
| **OS** | Raspberry Pi OS Lite (64-bit, Debian 12 Bookworm base) — headless |
| **Ethernet** | Gigabit Ethernet via carrier board (primary uplink) |
| **USB** | USB 2.0 host ports via carrier board (2x, for USB-serial adapters) |
| **RS232** | Via onboard UART or carrier board DB9 connector(s) |
| **Power Input** | 5V DC via USB-C or barrel jack; supports 9–24V DC input via buck converter |
| **Power Draw** | ~3–5 W typical, 7 W peak |
| **Temperature** | 0°C to 70°C operating (standard); CM4 Lite variant for extended range |
| **Storage (alt)** | NVMe M.2 SSD via PCIe lane on selected carrier boards (preferred for write endurance) |

### 2.2 Industrial Alternative — Advantech ARK or Moxa UC Series

For customers with stricter EMC requirements, cleanroom deployments, or extended temperature range needs, the following industrial alternatives are supported:

| Vendor | Model | Notes |
|--------|-------|-------|
| **Advantech** | ARK-1124H | DIN-rail, Atom E3940, -40°C to 70°C, 4x RS232, 2x LAN |
| **Moxa** | UC-8112A-ME-T | ARM Cortex-A8, -40°C to 70°C, 2x RS232/422/485, 2x ETH |
| **Siemens** | IOT2040 | Intel Quark x1020, industrial I/O, -20°C to 60°C |
| **Kontron** | KBox A-202-AL | AMD Ryzen, -40°C to 75°C, full x86, PCIe expansion |

Industrial alternatives run the same BioNexus Box software stack. The additional cost is justified for cleanroom or harsh environments. Default deployments use the CM4 platform.

### 2.3 Enclosure and Connectivity Summary

```
+------------------------------------------------+
|  BioNexus Box — Physical Interface Panel       |
|                                                |
|  [POWER]  [STATUS LED]  [RESET*]               |
|                                                |
|  RS232-1 (DB9-F)  RS232-2 (DB9-F)             |
|  USB-A (x2)       USB-C (power in)             |
|  ETH-1 (RJ45)     ETH-2 (RJ45, optional)      |
|  [MicroHDMI - diagnostic only, sealed]         |
|                                                |
|  *RESET requires physical access (tamper log)  |
+------------------------------------------------+
```

- **RS232 ports**: DB9 female, hardware flow control (RTS/CTS) supported, baud rates 300–115200
- **USB-A ports**: USB 2.0, used for USB-to-serial adapters (CH340, FTDI FT232) or direct USB CDC-ACM instruments
- **Ethernet**: Primary uplink; Gigabit preferred. PoE (802.3af) supported on select carrier boards to eliminate separate power cable
- **Status LEDs**: Power (green), Network (blue), Instrument active (amber), Error (red), Sync status (white)
- **Physical reset**: Hardware button requires a pin insertion (recessed); reset event is logged to the cloud audit trail before the reboot executes if network is available

### 2.4 Carrier Board Recommendation

The recommended carrier board for CM4 in production is the **Waveshare CM4-NANO-B** or **Seeed Studio reRouter CM4 102110**. For higher-volume production, a custom carrier board with:

- Onboard RS232 transceivers (MAX3232) for direct DB9 connections (no adapter needed)
- Onboard RTC with battery backup (DS3231 or equivalent) for accurate timestamping during power outages
- Hardware watchdog timer for automatic recovery from software lockup
- TPM 2.0 chip (SLB9670 or equivalent) for device identity and secure key storage
- Status LED array driven by GPIO

---

## 3. Supported Instrument Interfaces

### 3.1 RS232 Serial (Primary — Current Support)

RS232 is the dominant physical interface for laboratory instruments manufactured between 1985 and 2015 and remains common in new instruments designed for regulated environments due to its deterministic, simplex nature.

**Interface characteristics supported:**

| Parameter | Range / Values |
|-----------|---------------|
| Baud rates | 300, 600, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200 bps |
| Data bits | 7 or 8 |
| Parity | None, Even, Odd, Mark, Space |
| Stop bits | 1 or 2 |
| Flow control | None, Hardware (RTS/CTS), Software (XON/XOFF) |
| Voltage levels | Standard RS232 (+/-12V); tolerates +/-15V |
| Max cable length | 15 m (50 ft) at 9600 baud; shorter at higher rates |
| Connector | DB9 Female on Box side; DB9 or DB25 on instrument side (cable adapters supplied) |

**Configuration per port** is stored in `/etc/bionexus/instruments.yaml` and includes baud rate, parity, timeout, and parser module assignment.

### 3.2 USB Serial (CDC-ACM and FTDI)

Many modern instruments present a USB interface that emulates a serial port. The Box supports:

- **USB CDC-ACM**: Linux kernel native driver (`cdc_acm`), no additional drivers needed. Instruments present as `/dev/ttyACM0`, `/dev/ttyACM1`, etc.
- **FTDI FT232R/FT2232**: Via kernel `ftdi_sio` module. Instruments present as `/dev/ttyUSB0`, `/dev/ttyUSB1`, etc.
- **CH340/CH341**: Common on lower-cost USB-serial adapters. Supported via kernel `ch341` module.
- **Prolific PL2303**: Supported via `pl2303` kernel module.

USB device assignment is deterministic via `udev` rules that bind device nodes to instrument identifiers by USB vendor ID, product ID, and serial number. This prevents port remapping when multiple USB instruments are connected.

```
# /etc/udev/rules.d/99-bionexus-instruments.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", \
  ATTRS{serial}=="A50285BI", SYMLINK+="bionexus-hplc-1", MODE="0660", GROUP="bionexus"
```

### 3.3 TCP/IP Socket (Planned — Phase 2)

Newer instruments (Waters ACQUITY, Agilent OpenLAB-compatible analyzers) expose a TCP/IP socket or REST API on the local network. Phase 2 of the Box software will support:

- Raw TCP socket polling (configurable host:port, poll interval, delimiter)
- Modbus TCP (common in environmental monitoring instruments)
- OPC-UA client (industry 4.0 instruments)

TCP/IP connections are initiated outbound from the Box, maintaining the same security boundary as RS232 capture. No inbound ports are opened on the instrument network.

### 3.4 Analog Input (Future — Phase 3)

Direct 4–20 mA or 0–10V analog signal capture via ADC hat (e.g., Waveshare High-Precision AD/DA) for instruments that produce only analog output (legacy pH probes, temperature sensors).

### 3.5 Interface Summary

```
Interface        Status          Connector        Max Instruments
-----------------------------------------------------------------
RS232            Supported       DB9 / adapter    2 (native ports)
USB Serial       Supported       USB-A            4 (via hub)
TCP/IP Socket    Phase 2         Ethernet         Unlimited
Modbus TCP       Phase 2         Ethernet         Unlimited
OPC-UA           Phase 2         Ethernet         Unlimited
Analog (ADC)     Phase 3         GPIO header      4 channels
Bluetooth LE     Phase 3         USB dongle       TBD
Wi-Fi            Phase 3         USB dongle       N/A (uplink)
```

---

## 4. Supported Instruments

### 4.1 Instrument Categories and Common Data Formats

The BioNexus Box is instrument-agnostic at the hardware level. Support for specific instruments is implemented as parser modules in the Box software. The following categories are supported or planned:

#### 4.1.1 Dissolution Testers

**Examples:** Agilent 708-DS, Erweka DT820, Sotax AT7, Distek Premiere 5100

**Output formats:**
- Fixed-width ASCII tables (most common)
- CSV via RS232
- USP apparatus type, paddle/basket speed (RPM), vessel temperature, time-point results (%dissolved)

**Typical RS232 output:**
```
DISSOLUTION TESTER DT820
BATCH: LOT-2026-0045
APPARATUS: II PADDLE
SPEED: 75 RPM
TEMP: 37.0 C
TIME  V1     V2     V3     V4     V5     V6
15    12.4   12.1   12.6   12.3   12.5   12.2
30    45.8   45.3   45.9   45.7   45.6   45.4
45    78.3   78.1   78.4   78.2   78.5   78.0
60    98.1   97.9   98.3   98.0   98.2   97.8
END
```

#### 4.1.2 HPLC Systems

**Examples:** Waters Alliance e2695, Agilent 1260 Infinity II, Shimadzu LC-20

**Output formats:**
- Custom ASCII report formats (instrument-specific)
- CSV export files (triggered at run end)
- CDF/netCDF binary (requires converter)
- Waters Empower `.arw` report export (ASCII)

**Data captured:** Sample ID, method name, injection volume, column details, retention time, peak area, peak height, USP tailing factor, theoretical plates, run start/end timestamps.

**Note:** Full chromatogram data (raw ADC signal) is not currently captured; only the processed results table. Raw signal capture is on the roadmap.

#### 4.1.3 UV-Vis Spectrophotometers

**Examples:** Shimadzu UV-1900i, Mettler Toledo UV5Nano, Jasco V-730

**Output formats:**
- Fixed-width ASCII tables
- CSV
- Wavelength scan data (wavelength vs. absorbance pairs)
- Single-point absorbance at defined wavelengths

**Data captured:** Sample ID, wavelength(s), absorbance, transmittance, concentration (if calibration curve applied), path length, timestamp.

#### 4.1.4 pH / Conductivity Meters

**Examples:** Mettler Toledo SevenExcellence, Hanna HI5521, Sartorius PB-10

**Output formats:**
- Simple delimited ASCII: `pH=7.42 T=23.1C COND=8.42mS/cm`
- GLP-format output blocks with instrument ID, calibration data, and result

**Data captured:** pH value, temperature compensation, conductivity/resistivity, electrode calibration date, operator ID, timestamp.

#### 4.1.5 Balances and Microbalances

**Examples:** Mettler Toledo XPR206, Sartorius Cubis II, Ohaus Pioneer

**Output formats:**
- Simple net weight string: `N   10.4321 g`
- GLP-format printout with header, result, and signature
- SBI (Simple Balance Interface) command/response protocol

**Data captured:** Net weight, gross weight, tare weight, unit, stability flag, balance ID, timestamp.

#### 4.1.6 Karl Fischer Titrators

**Examples:** Mettler Toledo V20S, Metrohm 851 Titrando, Hydranal-series

**Output formats:**
- Fixed ASCII results block
- CSV
- Content: water content (mg or %), sample weight, titration volume, endpoint, drift

#### 4.1.7 Environmental Monitoring (Temperature, RH)

**Examples:** Vaisala HMT330, Testo 176 H1, TSI Quest

**Output formats:**
- Continuous streaming ASCII (one reading per line)
- Modbus RTU (via RS232/RS485)

**Data captured:** Temperature (°C), relative humidity (%), dew point, timestamp; alarm thresholds compared against configured limits.

#### 4.2 Parser Module System

Each instrument category (and often specific instrument models) has a corresponding Python parser module on the Box:

```
/opt/bionexus/parsers/
├── base_parser.py              # Abstract base class
├── dissolution/
│   ├── generic_ascii.py
│   ├── erweka_dt820.py
│   └── sotax_at7.py
├── hplc/
│   ├── waters_arw.py
│   ├── agilent_chemstation.py
│   └── shimadzu_lc20.py
├── spectrophotometry/
│   ├── generic_uv.py
│   └── shimadzu_uv1900.py
├── ph_conductivity/
│   ├── mettler_seven.py
│   └── generic_ph.py
├── balance/
│   ├── sbi_protocol.py
│   └── mettler_xpr.py
└── environmental/
    ├── continuous_stream.py
    └── modbus_rtu.py
```

The parser base class defines the contract:

```python
class BaseParser:
    def parse(self, raw_bytes: bytes) -> ParsedReading | None:
        """
        Parse raw bytes from instrument serial port.
        Returns a ParsedReading on success, None if incomplete buffer,
        raises ParserError on malformed data.
        """
        raise NotImplementedError

    def get_schema(self) -> dict:
        """Return JSON Schema for this parser's output."""
        raise NotImplementedError
```

---

## 5. Software Architecture

### 5.1 Operating System

The Box runs **Raspberry Pi OS Lite (64-bit)** based on Debian 12 (Bookworm), configured headless with no desktop environment. The OS is hardened post-installation:

- Unused services and packages removed (Avahi, Bluetooth daemon, triggerhappy, etc.)
- `sshd` enabled for remote diagnostics with key-based authentication only (password auth disabled)
- Automatic security updates enabled via `unattended-upgrades` for OS packages
- All BioNexus services run under a dedicated unprivileged system account (`bionexus`, UID 999)
- `firewalld` or `nftables` configured to block all inbound connections except SSH (port 22, restricted to BioNexus management IP range)
- Kernel parameters hardened: ASLR enabled, IP forwarding disabled, source routing disabled

For industrial SBC alternatives (Advantech, Moxa), the same hardening is applied to their respective Debian/Ubuntu base images.

### 5.2 Software Stack

```
+----------------------------------------------------------+
|                    BioNexus Box Software                 |
+----------------------------------------------------------+
|  bionexus-agent (Python 3.12)                            |
|  +-----------------------+  +-------------------------+  |
|  |  Collector Service    |  |  Uplink Agent           |  |
|  |  - Serial port reader |  |  - HTTPS POST to GCP    |  |
|  |  - Parser dispatch    |  |  - Retry with backoff   |  |
|  |  - SHA-256 hashing    |  |  - Certificate pinning  |  |
|  |  - Local queue write  |  |  - Heartbeat sender     |  |
|  +-----------+-----------+  +----------+--------------+  |
|              |                         |                  |
|  +-----------v-------------------------v--------------+  |
|  |           Local Queue (SQLite WAL-mode)            |  |
|  |           /var/lib/bionexus/queue.db               |  |
|  +----------------------------------------------------+  |
|                                                          |
|  bionexus-watchdog (systemd-based)                      |
|  bionexus-updater  (OTA firmware management)            |
|  bionexus-diag     (diagnostics and health reporting)   |
+----------------------------------------------------------+
|            Debian 12 Linux (64-bit, hardened)            |
+----------------------------------------------------------+
|             Raspberry Pi CM4 Hardware                    |
+----------------------------------------------------------+
```

### 5.3 Collector Service

The Collector Service is a long-running Python daemon (`bionexus-collector`) that:

1. Opens configured serial ports (RS232 / USB-serial) using `pyserial`
2. Reads data using instrument-specific framing (end-of-line delimiter, fixed-length packet, or timeout-based capture)
3. Dispatches raw bytes to the assigned parser module
4. On successful parse, computes SHA-256 hash of the raw bytes
5. Writes the reading to the local SQLite queue
6. Records a local audit event (collector-level log)

Each configured instrument runs in its own thread. The collector is resilient to serial port disconnects: it attempts to reopen the port with exponential backoff, logging each failure to the diagnostics service.

```python
# Pseudocode — collector core loop
class InstrumentCollector(threading.Thread):
    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                with serial.Serial(**self.serial_config) as port:
                    buffer = b""
                    while not self.stop_event.is_set():
                        chunk = port.read(port.in_waiting or 1)
                        buffer += chunk
                        if self.parser.is_complete_frame(buffer):
                            reading = self.parser.parse(buffer)
                            if reading:
                                self.queue.enqueue(reading, raw_bytes=buffer)
                            buffer = b""
            except serial.SerialException as exc:
                self.diagnostics.report_error(self.instrument_id, exc)
                self.stop_event.wait(timeout=self.backoff.next())
```

### 5.4 Local Queue (SQLite WAL Mode)

The local queue is a SQLite database in Write-Ahead Log (WAL) mode, providing concurrent read/write access between the Collector (writer) and Uplink Agent (reader/deleter).

**Schema:**

```sql
CREATE TABLE reading_queue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id TEXT NOT NULL,
    captured_at   TEXT NOT NULL,         -- ISO 8601 UTC timestamp
    raw_bytes_b64 TEXT NOT NULL,         -- Base64-encoded raw instrument bytes
    raw_sha256    TEXT NOT NULL,         -- SHA-256 of raw_bytes
    parsed_json   TEXT NOT NULL,         -- Parser output as JSON string
    packet_sha256 TEXT NOT NULL,         -- SHA-256 of (instrument_id|captured_at|parsed_json)
    retry_count   INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now', 'utc')),
    status        TEXT DEFAULT 'PENDING' -- PENDING | UPLOADING | UPLOADED | FAILED
);

CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,           -- CAPTURE | UPLOAD | ERROR | CONFIG_CHANGE | BOOT | SHUTDOWN
    instrument_id TEXT,
    queue_id    INTEGER,
    detail      TEXT,
    timestamp   TEXT DEFAULT (datetime('now', 'utc'))
);
```

SQLite was selected over a message broker (RabbitMQ, Redis) for the embedded environment because:
- Zero external dependencies
- WAL mode provides non-blocking concurrent reads
- File-level encryption possible via SQLCipher
- Survives power loss without corruption (WAL + synchronous=FULL)

### 5.5 Uplink Agent

The Uplink Agent is a separate thread (part of `bionexus-agent`) that:

1. Polls the local queue for `status='PENDING'` readings
2. Batches up to 50 readings per HTTP request (configurable)
3. Posts the batch to the GCP backend (`POST /api/v1/ingest/readings/`)
4. On HTTP 200/201: marks readings as `UPLOADED`, purges after configurable retention (default: 7 days)
5. On HTTP 4xx (client error): marks as `FAILED`, logs error, does not retry (data issue)
6. On HTTP 5xx or network error: increments `retry_count`, backs off exponentially, retries up to `MAX_RETRIES` (default: 10)
7. Readings with `retry_count > MAX_RETRIES` are flagged for human review via the monitoring dashboard

### 5.6 Configuration Management

All Box configuration is stored in YAML files under `/etc/bionexus/`:

```yaml
# /etc/bionexus/config.yaml
device:
  device_id: "box-a1b2c3d4e5f6"          # Immutable UUID assigned at provisioning
  tenant_id: "tenant-uuid-here"
  site_id: "customer-lab-001"
  firmware_version: "1.3.2"

uplink:
  api_endpoint: "https://api.bionexus.io/api/v1"
  cert_pin_sha256: "sha256//AbCdEfGhIjKl..."   # Backend TLS cert pin
  heartbeat_interval_seconds: 60
  upload_batch_size: 50
  max_retry_count: 10
  retry_backoff_base_seconds: 5
  retry_backoff_max_seconds: 300

queue:
  db_path: "/var/lib/bionexus/queue.db"
  retention_days: 7
  max_queue_size_mb: 500

instruments:
  - id: "instrument-hplc-001"
    name: "Waters Alliance 2695 HPLC"
    type: "hplc"
    interface: "rs232"
    port: "/dev/bionexus-hplc-1"
    baud_rate: 9600
    data_bits: 8
    parity: "N"
    stop_bits: 1
    parser: "hplc.waters_arw"
    timeout_seconds: 5

  - id: "instrument-ph-001"
    name: "Mettler Toledo SevenExcellence pH"
    type: "ph_conductivity"
    interface: "usb_serial"
    port: "/dev/bionexus-ph-1"
    baud_rate: 19200
    parser: "ph_conductivity.mettler_seven"
```

Configuration changes are applied via a `bionexus-config apply` CLI command, which validates the YAML schema, writes the new config atomically (write to temp file, `rename()` for atomicity), and creates a local audit log entry. Configuration is also pushed from the cloud management plane (see Section 11).

---

## 6. Communication Protocol

### 6.1 Authentication — Device Identity

Each BioNexus Box has a unique identity established at manufacturing/provisioning time:

- **Device Certificate (X.509)**: An RSA-4096 or EC-P256 client certificate issued by the BioNexus Certificate Authority (CA), stored in the TPM's non-volatile memory. The private key never leaves the TPM; all signing operations are performed inside the TPM.
- **Device ID**: A UUID derived from the certificate's serial number, stored in `/etc/bionexus/config.yaml`.
- **API Key (secondary)**: A 256-bit randomly generated API key stored in an encrypted file at `/var/lib/bionexus/secrets/api_key.enc`, decrypted at runtime using a TPM-sealed key.

For MVP (pre-TPM), device identity uses the API key stored in an encrypted file. The TPM upgrade is Phase 2.

**Authentication flow for each upload batch:**

```
Box                                    GCP Backend
 |                                         |
 |  TLS ClientHello (SNI: api.bionexus.io) |
 |---------------------------------------->|
 |                                         |
 |  TLS: ServerCertificate                 |
 |<----------------------------------------|
 |  [Box verifies cert against pinned SHA256]
 |                                         |
 |  TLS: ClientCertificate (device cert)   |
 |---------------------------------------->|
 |  [Backend verifies cert against BioNexus CA]
 |                                         |
 |  POST /api/v1/ingest/readings/          |
 |  Authorization: Bearer <device-api-key> |
 |  X-Device-ID: box-a1b2c3d4e5f6         |
 |  Content-Type: application/json         |
 |  [Body: batch payload]                  |
 |---------------------------------------->|
 |                                         |
 |  HTTP 201 Created                       |
 |  {"accepted": 50, "rejected": 0}        |
 |<----------------------------------------|
```

### 6.2 TLS Configuration

- **TLS Version**: TLS 1.3 required. TLS 1.2 with AEAD cipher suites permitted as fallback (for backward compatibility with older Python/OpenSSL).
- **TLS 1.3 Cipher Suites**: TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256
- **Certificate Pinning**: The Box stores the SHA-256 digest of the GCP backend's TLS certificate (or its CA certificate) in the configuration. If the presented certificate's digest does not match, the connection is refused and an alert is sent to the monitoring endpoint. Certificate rotation requires a coordinated firmware config update pushed via the management plane.
- **mTLS**: Mutual TLS (device client certificate + server certificate) is implemented in Phase 2. MVP uses API key in the Authorization header over server-authenticated TLS.

### 6.3 Message Format

Each upload batch is a JSON document:

```json
{
  "device_id": "box-a1b2c3d4e5f6",
  "tenant_id": "tenant-uuid-here",
  "batch_id": "batch-20260228-143022-001",
  "batch_sha256": "e3b0c44298fc1c149afb...",
  "sent_at": "2026-02-28T14:30:22.145Z",
  "firmware_version": "1.3.2",
  "readings": [
    {
      "queue_id": 1042,
      "instrument_id": "instrument-hplc-001",
      "captured_at": "2026-02-28T14:29:55.000Z",
      "raw_bytes_b64": "RFVTU09MVVRJT04gVEVTVEVS...",
      "raw_sha256": "a665a45920422f9d417e4867ef...",
      "parsed_json": {
        "instrument_type": "hplc",
        "sample_id": "QC-2026-00451",
        "method": "USP-HPLC-API-001",
        "run_id": "R20260228-001",
        "injection_volume_ul": 10.0,
        "results": [
          {
            "peak_name": "Active API",
            "retention_time_min": 4.823,
            "peak_area": 1245678.3,
            "peak_height": 98432.1,
            "concentration_pct": 99.7,
            "usp_tailing": 1.03,
            "theoretical_plates": 8234
          }
        ],
        "run_start": "2026-02-28T14:20:00Z",
        "run_end": "2026-02-28T14:29:55Z"
      },
      "packet_sha256": "f4d9e8c7b6a5..."
    }
  ]
}
```

**`batch_sha256`**: SHA-256 of the entire `readings` array serialized as canonical JSON (sorted keys, no extra whitespace). Computed on the Box before sending; verified on the backend before ingestion.

### 6.4 Retry Logic

```
Upload attempt  →  HTTP 201  →  Mark UPLOADED, done
                →  HTTP 400  →  Mark FAILED (schema error — log, do not retry)
                →  HTTP 401  →  Mark FAILED (auth error — alert operations)
                →  HTTP 409  →  Mark UPLOADED (duplicate — already received)
                →  HTTP 5xx  →  Increment retry_count, schedule retry:
                                  delay = min(base * 2^retry_count, max_delay)
                                  base=5s, max=300s
                →  Timeout   →  Same as HTTP 5xx
                →  retry_count > 10  →  Mark FAILED, alert operations dashboard
```

Exponential backoff with jitter (±10% of computed delay) prevents thundering herd during backend maintenance windows affecting many Boxes simultaneously.

---

## 7. Data Flow

### 7.1 End-to-End Data Flow

```
+------------------+
| Lab Instrument   |
| (e.g., HPLC)     |
+--------+---------+
         |
         | RS232 serial bytes (raw ASCII/binary instrument output)
         |
+--------v---------+
| Serial Port      |
| /dev/ttyS0 or    |
| /dev/ttyUSB0     |
+--------+---------+
         |
         | pyserial read()
         |
+--------v---------+       +-----------------+
| Collector        |       | Parser Module   |
| Service          +------>| (e.g., waters_  |
| (Thread per      |       | arw.py)         |
| instrument)      |<------+                 |
+--------+---------+       | ParsedReading{} |
         |                 +-----------------+
         | SHA-256(raw_bytes)
         | SHA-256(instrument_id|captured_at|parsed_json)
         |
+--------v---------+
| Local SQLite     |
| Queue            |
| (WAL mode)       |
| status=PENDING   |
+--------+---------+
         |
         | Poll for PENDING readings (batch of up to 50)
         |
+--------v---------+
| Uplink Agent     |
| (Thread)         |
| - Build batch    |
| - Sign batch     |
| - TLS connect    |
+--------+---------+
         |
         | HTTPS POST /api/v1/ingest/readings/
         | (TLS 1.3 + API key auth)
         |
+--------v----------+
| GCP Backend       |
| Django REST API   |
+--------+----------+
         |
         | IngestView:
         | 1. Verify device_id + API key
         | 2. Verify batch_sha256
         | 3. Verify packet_sha256 per reading
         | 4. Create RawFile record per reading
         |    (file_hash = raw_sha256)
         | 5. Create AuditLog (entity=RawFile, op=CREATE)
         | 6. Enqueue async parse task (Celery)
         | 7. Return HTTP 201
         |
+--------v----------+
| PostgreSQL        |
| RawFile table     |
| AuditLog table    |
+-------------------+
         |
         | (async, via Celery)
         |
+--------v----------+
| ParsingService    |
| - AI extraction   |
| - Pydantic valid. |
| - PENDING state   |
| - Human review    |
|   required        |
+-------------------+
```

### 7.2 Timestamp Chain

Timestamps are captured at four points, forming a tamper-evident chain:

| # | Timestamp | Source | Description |
|---|-----------|--------|-------------|
| 1 | `instrument_time` | Instrument RTC | Time embedded in instrument output (if present) |
| 2 | `captured_at` | Box RTC (hardware RTC with battery, NTP-synced) | Time the serial bytes were received by the Collector |
| 3 | `sent_at` | Box clock | Time the batch was assembled and POSTed |
| 4 | `received_at` | GCP backend | `django.utils.timezone.now()` at request receipt |

The Box RTC is synchronized via NTP (pool.ntp.org or a customer-provided NTP server) with a maximum allowed drift of 2 seconds. If NTP sync fails for more than 15 minutes, the Collector logs a warning but continues capturing. If drift exceeds 30 seconds, the Box halts uploads and alerts operations (timestamp integrity compromise — 21 CFR Part 11 requires accurate, contemporaneous timestamps).

---

## 8. Offline and Disconnected Mode

### 8.1 Store-and-Forward Design

The BioNexus Box is designed to tolerate indefinite network outages without data loss. The local SQLite queue is the primary mechanism:

```
Network      Collector       Queue          Uplink Agent
state                        state
  |              |              |                |
ONLINE       capturing   PENDING → UPLOADED   uploading in near-real-time
  |              |              |                |
OFFLINE      continues   PENDING (growing)   paused, retrying with backoff
  |          capturing        ...             ...
  |              |              |                |
  |              |         [7 days of data       |
  |              |          stored safely]        |
  |              |              |                |
ONLINE           |         PENDING (backlog)  resumes, uploads backlog
reconnect        |              |              in batches of 50
```

**Queue capacity**: Default SQLite database limited to 500 MB on the eMMC/NVMe. At typical instrument sampling rates (one reading per minute per instrument), this represents:

- 1 instrument: approximately 6 months of offline storage
- 4 instruments: approximately 6 weeks of offline storage
- NVMe option: configurable up to 10 GB, extending this to years

If the queue approaches the size limit (at 80% capacity), an alert is sent via alternative channel (SMS/email to the configured operations contact, triggered by the next successful heartbeat).

### 8.2 Data Integrity During Network Outage

Every reading queued locally contains two SHA-256 hashes computed before network transmission:

1. **`raw_sha256`**: Hash of the raw bytes received from the instrument. Verifies no corruption of the raw capture.
2. **`packet_sha256`**: Hash of the canonical JSON of `(instrument_id, captured_at, parsed_json)`. Verifies no tampering of the parsed/interpreted data.

When the Box reconnects and uploads the backlog, the GCP backend verifies both hashes. Any mismatch causes the reading to be rejected with HTTP 422 and flagged for investigation. This ensures that data stored locally during an outage cannot be silently modified before upload.

### 8.3 Sync Reconciliation

After a prolonged offline period, the backend performs a reconciliation check:

1. The Box reports the IDs and timestamps of all readings uploaded in the reconnection batch.
2. The backend checks for any gaps in the `captured_at` sequence per instrument.
3. If gaps exist (readings missing without a corresponding error log), the backend generates a gap alert in the audit trail noting the missing time range.
4. This gap alert is reportable to auditors and must be explained during a 21 CFR Part 11 audit.

### 8.4 Power Loss Recovery

The SQLite WAL mode with `PRAGMA synchronous=FULL` ensures that any writing committed to the queue database survives a power loss. The WAL file is flushed to disk before the transaction is acknowledged. This prevents data loss from unexpected power cuts (common in lab environments during equipment moves).

On Box reboot after unexpected power loss:
1. `bionexus-agent` checks SQLite integrity (`PRAGMA integrity_check`) at startup.
2. If integrity check fails, the corrupted database is moved aside and a new empty queue is started. An alert is sent and a local audit event records the data loss event.
3. All `status='UPLOADING'` records (were in-flight at crash time) are reset to `status='PENDING'` and re-uploaded. The backend deduplicates by `packet_sha256`, so there are no duplicate records created.

---

## 9. Security Model

### 9.1 Device Identity

Each Box has a unique, non-forgeable identity:

**MVP (Phase 1):**
- Unique `device_id` (UUID) assigned at cloud provisioning
- 256-bit API key stored in encrypted file (`/var/lib/bionexus/secrets/api_key.enc`)
- Encryption key derived from device serial number + provisioning secret (HKDF-SHA256)
- API key rotation supported via management plane push

**Production (Phase 2):**
- X.509 device certificate issued by BioNexus CA, stored in TPM 2.0
- Private key is TPM-resident; never exported; all signing operations are in-TPM
- Mutual TLS (mTLS) for all communication with backend
- Certificate revocation via OCSP; revocation list checked at every connection

### 9.2 Secure Boot

Secure boot (Phase 2) ensures only signed firmware runs on the Box:

```
Power-on → UEFI / ARM TrustZone → verify bootloader signature (BioNexus root key)
         → bootloader verifies kernel signature
         → kernel verifies initrd signature
         → initrd mounts dm-verity protected root filesystem
         → systemd starts bionexus services
```

For Raspberry Pi CM4 (which lacks UEFI secure boot natively), a combination of:
- `rpi-eeprom` firmware with HAT EEPROM attestation (Phase 2)
- `dm-verity` for read-only root filesystem integrity
- Custom bootloader verification script in EEPROM

For industrial x86 alternatives (Advantech, Kontron): full UEFI Secure Boot with BioNexus-enrolled MOK (Machine Owner Key).

### 9.3 Encrypted Local Storage

**Root filesystem**: Read-only (`dm-verity`). Mount integrity verified on every read.

**Data partition** (`/var/lib/bionexus`): Encrypted with LUKS2 (AES-256-XTS). The LUKS key is sealed in the TPM, released only when boot measurements (PCR values) match expected values. If firmware is tampered (modified kernel, modified initrd), PCR values change and the LUKS key is not released — the data partition is inaccessible.

**MVP (pre-TPM)**: Data partition encrypted with LUKS2; key stored in a file encrypted using the device serial number + provisioning secret. Less secure than TPM sealing but provides protection against drive theft.

**Secrets file** (`api_key.enc`, `device_cert.p12`): Encrypted with AES-256-GCM using the device-specific encryption key.

### 9.4 Physical Tamper Considerations

The GxP physical security requirements for edge devices are addressed as follows:

| Threat | Mitigation |
|--------|-----------|
| Physical access to USB/HDMI ports | Ports sealed with tamper-evident labels; HDMI port disabled in device tree |
| SD card removal / substitution | eMMC (onboard, not removable); no SD card slot on production carrier |
| Drive extraction + data theft | LUKS2 encryption on data partition |
| Firmware replacement via SD card | No SD card; eMMC reflash requires physical USB boot mode + serial console access |
| Box replacement with rogue device | mTLS: rogue device has no valid BioNexus CA-signed certificate |
| Physical reset button | Recessed pin-reset; reset event logged to cloud before execution |
| Enclosure opening | Tamper-evident screws + optional chassis intrusion switch wired to GPIO → audit log event |

Enclosures used in Class C/D cleanroom environments use IP54-rated sealed enclosures (see Section 14) that further restrict physical access.

### 9.5 Network Security

- All outbound traffic from the Box goes to `api.bionexus.io` (HTTPS, port 443) only.
- `nftables` blocks all other outbound traffic except NTP (UDP 123) and DNS (UDP/TCP 53).
- No inbound ports except SSH (TCP 22) restricted to BioNexus management IP range (`10.0.0.0/8` or customer-specific allowlist).
- SSH uses key-based authentication; RSA-4096 or ED25519 keys only. Password auth disabled.
- SSH keys for remote diagnostics are rotated monthly.

---

## 10. Firmware Update Strategy

### 10.1 OTA Update Mechanism

BioNexus Box firmware (the entire OS image + software stack) is updated over-the-air via a two-partition A/B update scheme:

```
eMMC Layout:
+------------------+------------------+------------------+------------------+
| Boot partition   | System-A (active)| System-B (standby| Data partition   |
| (read-only)      | Firmware 1.3.2   | Firmware 1.3.3   | LUKS encrypted   |
| 256 MB           | 4 GB (dm-verity) | 4 GB (dm-verity) | remainder        |
+------------------+------------------+------------------+------------------+
         ^                   ^                   ^
    Shared GRUB         Currently booted    Update written here,
    / RPi bootloader    read-only rootfs    verified, then set active
```

**Update process:**

1. Backend management plane pushes update notification to Box via next heartbeat response
2. Box Updater downloads firmware bundle from a signed GCS bucket URL (time-limited, pre-signed)
3. Bundle signature verified (Ed25519, BioNexus Firmware Signing Key)
4. Bundle SHA-256 checksum verified
5. New firmware written to the standby partition (System-B)
6. `dm-verity` hash tree computed and stored for standby partition
7. Standby partition hash verified before marking bootable
8. Box scheduled for reboot at next maintenance window (configurable: immediate, next maintenance window, or manual trigger)
9. Bootloader updated to boot from System-B
10. On first successful boot from B: System-B marked permanent active
11. If boot fails (timeout, watchdog trigger): bootloader reverts to System-A automatically

### 10.2 Rollback Capability

The A/B partition scheme guarantees automatic rollback:

- If System-B fails to boot within a configurable timeout (default: 3 minutes), the hardware watchdog fires and the bootloader reverts to System-A.
- A "boot success" confirmation is written to the bootloader environment after the `bionexus-agent` service starts successfully.
- Manual rollback is available via the management plane ("revert to previous firmware") which triggers the same bootloader switch.
- All firmware versions are retained for 3 rollback generations in the management plane (can redeploy any of the last 3 versions).

### 10.3 Change Control Compliance

Every firmware release must pass the following gate before deployment to customer Boxes:

| Gate | Description |
|------|-------------|
| Version increment | Semantic versioning (MAJOR.MINOR.PATCH); version embedded in signed bundle |
| Changelog | Human-readable list of changes (required for GxP change control documentation) |
| Regression test suite | Automated tests run against firmware in CI/CD pipeline |
| Signing | Ed25519 signature by authorized BioNexus firmware signing officer |
| Staged rollout | 5% → 25% → 100% of Boxes, with 24-hour hold between stages |
| Audit record | Firmware deployment recorded in cloud audit trail with version, deployer, timestamp |

For customer sites under validated computer system (CSV) status, firmware updates may require customer approval (change request) before deployment. The management plane supports a "hold" flag per tenant that prevents automatic updates; the customer's QA team approves updates manually.

### 10.4 Update Verification

After each successful update:

1. Box reports firmware version in next heartbeat
2. Management plane verifies reported version matches intended version
3. If mismatch, Box is flagged for investigation (possible update failure or tampered version)
4. Box reports `dm-verity` status for the active partition (passes/fails); failure triggers immediate alert

---

## 11. Deployment and Provisioning

### 11.1 Overview

The BioNexus Box is shipped to the customer site as a pre-provisioned device. The provisioning workflow is:

```
BioNexus Factory/Lab                          Customer Site
        |                                           |
1. Flash base OS image to eMMC                     |
2. Generate device_id (UUID)                       |
3. Generate API key, encrypt and store             |
4. Register device in cloud (device_id, tenant_id)|
5. Write config.yaml with device_id + endpoint    |
6. Run pre-ship diagnostics (all LEDs, serial     |
   loopback, network connectivity)                |
7. Apply tamper-evident seals to enclosure        |
8. Ship Box + RS232 cable + power supply          |
        |                                           |
        +-----------[physical delivery]------------>|
                                                    |
                                    9. Customer plugs into:
                                       - Power (USB-C)
                                       - Ethernet (to lab network)
                                       - RS232/USB to instrument
                                                    |
                                    10. Box boots, connects to cloud
                                        LED: blue (network OK)
                                                    |
                                    11. BioNexus tech (remote) confirms
                                        device is online in management console
                                    12. Configure instrument in cloud UI:
                                        - Select instrument type
                                        - Set serial params (baud, parity, etc.)
                                        - Assign parser module
                                    13. Push config to Box via management plane
                                    14. Box restarts Collector with new config
                                    15. First readings arrive in cloud dashboard
                                        LED: amber (instrument active)
                                                    |
                                    16. Customer validates first batch of readings
                                        against known instrument output (IQ step)
                                    17. Installation complete — Box operational
```

Total installation time target: under 60 minutes from box unpacking to first data in dashboard.

### 11.2 Device Registration (Cloud Side)

When a Box first connects (using its provisioned API key), the GCP backend:

1. Validates the `device_id` exists in the device registry
2. Sets the device status to `ONLINE`
3. Records `first_seen_at`, `last_seen_at`, `firmware_version`, `ip_address` (for diagnostics)
4. Returns any pending configuration updates in the heartbeat response

```python
# Django model — Device registry
class BoxDevice(models.Model):
    device_id       = models.UUIDField(primary_key=True)
    tenant          = models.ForeignKey(Tenant, on_delete=models.PROTECT)
    site_id         = models.CharField(max_length=100)
    api_key_hash    = models.CharField(max_length=64)   # SHA-256 of API key
    firmware_version = models.CharField(max_length=20)
    status          = models.CharField(max_length=20)   # ONLINE | OFFLINE | DEGRADED | PROVISIONED
    first_seen_at   = models.DateTimeField(null=True)
    last_seen_at    = models.DateTimeField(null=True)
    last_ip_address = models.GenericIPAddressField(null=True)
    config_version  = models.IntegerField(default=1)
    is_update_held  = models.BooleanField(default=False)  # CSV validation hold
    created_at      = models.DateTimeField(auto_now_add=True)
```

### 11.3 Instrument Pairing

Instrument configuration is managed in the cloud and pushed to the Box. The pairing process:

1. QA Administrator creates an instrument record in the cloud UI (instrument type, make, model, serial number, calibration due date)
2. Assigns the instrument to a Box device
3. Specifies the physical port (RS232-1, USB-1, etc.) and serial parameters
4. Cloud pushes the updated `instruments` section of `config.yaml` to the Box (delivered in the next heartbeat response, or immediately via a management push)
5. Box Collector restarts the affected instrument thread with the new configuration
6. The instrument pairing is recorded in the audit trail (entity: BoxDevice, operation: CONFIG_UPDATE)

---

## 12. Monitoring and Diagnostics

### 12.1 Heartbeat

The Box sends a heartbeat to the backend every 60 seconds (configurable). The heartbeat payload:

```json
{
  "device_id": "box-a1b2c3d4e5f6",
  "firmware_version": "1.3.2",
  "uptime_seconds": 1209600,
  "timestamp": "2026-02-28T14:30:00Z",
  "queue_depth": 0,
  "queue_size_bytes": 12288,
  "instruments": [
    {
      "instrument_id": "instrument-hplc-001",
      "status": "ACTIVE",
      "last_reading_at": "2026-02-28T14:29:55Z",
      "readings_today": 48,
      "error_count_today": 0
    },
    {
      "instrument_id": "instrument-ph-001",
      "status": "NO_DATA",
      "last_reading_at": "2026-02-27T18:00:00Z",
      "readings_today": 0,
      "error_count_today": 0
    }
  ],
  "system": {
    "cpu_pct": 8.2,
    "mem_used_pct": 31.4,
    "disk_used_pct": 12.7,
    "ntp_synced": true,
    "ntp_offset_ms": 12,
    "last_successful_upload_at": "2026-02-28T14:29:58Z",
    "failed_uploads_count": 0,
    "dm_verity_active": true,
    "dm_verity_ok": true
  }
}
```

The backend responds to heartbeat with any pending configuration updates or commands (firmware update notification, config push, remote diagnostic request).

### 12.2 Alerting Thresholds

The management plane triggers alerts (email/SMS/webhook to configured operations contacts) for:

| Condition | Threshold | Severity |
|-----------|-----------|---------|
| Box offline | No heartbeat for 5 minutes | WARNING |
| Box offline extended | No heartbeat for 30 minutes | CRITICAL |
| Instrument silent | No readings for configured silence threshold (per instrument) | WARNING |
| Queue depth growing | Queue depth > 1000 readings | WARNING |
| Queue near capacity | Disk usage > 80% | CRITICAL |
| Upload failures | `failed_uploads_count > 0` | WARNING |
| NTP desync | `ntp_offset_ms > 2000` | WARNING |
| dm-verity failure | `dm_verity_ok = false` | CRITICAL + Security Alert |
| Firmware mismatch | Reported version != expected version | WARNING |
| Certificate expiry | Device cert expires within 30 days | WARNING |

### 12.3 Remote Diagnostics

BioNexus support engineers can initiate remote diagnostic commands via the management plane, delivered to the Box in the heartbeat response:

| Command | Description |
|---------|-------------|
| `collect_logs` | Box uploads `/var/log/bionexus/` (last 24h) to a secure diagnostic endpoint |
| `test_serial_port` | Sends a serial port loopback test; reports bytes received |
| `restart_collector` | Restarts the Collector service; all in-flight reads are discarded |
| `restart_agent` | Restarts the entire bionexus-agent; queue state preserved |
| `reboot` | Graceful OS reboot; queued data preserved |
| `run_diagnostics` | Full hardware diagnostic (CPU, memory, disk, network, NTP, serial ports) |
| `flush_queue` | Forces immediate upload of all queued readings |

All remote commands are logged in the cloud audit trail (entity: BoxDevice, operation: REMOTE_COMMAND) with the requesting user's identity.

### 12.4 Status LED Reference

| LED Color | State | Meaning |
|-----------|-------|---------|
| Green | Solid | Power on, system healthy |
| Blue | Solid | Network connected, cloud sync active |
| Blue | Blinking | Network connected, uploading backlog |
| Blue | Off | No network connectivity |
| Amber | Blinking | Instrument data being captured |
| Amber | Solid | Instrument connected, no recent data (expected quiet period) |
| Amber | Off | No instruments configured or connected |
| Red | Blinking (slow) | Upload errors / authentication failure |
| Red | Blinking (fast) | Critical error — dm-verity failure, disk full, hardware fault |
| White | Single flash | Heartbeat sent successfully |
| White | Solid | Firmware update in progress (do not power off) |

---

## 13. GxP Compliance Considerations

### 13.1 GAMP5 Classification

Under GAMP5, the BioNexus Box hardware gateway is classified as:

| Component | GAMP5 Category | Rationale |
|-----------|----------------|-----------|
| Box hardware (CM4, carrier board, enclosure) | Category 1 — Infrastructure | Standard commercial hardware; vendor-qualified |
| Box firmware (OS + bionexus-agent) | Category 4 — Configured Product | Standard OS with configured BioNexus application; not custom built from scratch for a single customer but configured per site |
| Instrument parser modules (custom) | Category 5 — Custom Application | Custom-developed software specific to each instrument type; requires full software lifecycle documentation |

The Category 5 classification for parser modules means each parser requires:
- Requirements specification
- Design specification
- Code review
- Unit tests
- Integration tests
- Release notes

### 13.2 21 CFR Part 11 Compliance at the Edge

The following 21 CFR Part 11 requirements are addressed at the Box level (edge):

| Requirement | Implementation |
|-------------|---------------|
| **§11.10(a) — System validation** | IQ/OQ/PQ qualification performed at each customer site installation; Box passes self-diagnostics on startup |
| **§11.10(b) — Legible records** | All captured data stored as human-readable JSON; raw bytes preserved as Base64 |
| **§11.10(c) — Record generation** | Readings generated by the Box, not manually entered; audit trail records the Box as the data source |
| **§11.10(d) — Protection of records** | LUKS2 encrypted data partition; dm-verity protected OS; tamper-evident physical seals |
| **§11.10(e) — Computer system access** | Box requires API key auth for cloud communication; SSH requires key auth for local access; no anonymous access |
| **§11.10(k) — Operational system checks** | Heartbeat confirms system health; watchdog ensures recovery from software failure |
| **§11.50 — Signed records** | Each reading is SHA-256 signed at the packet level on the Box; signature verified by backend |
| **§11.70 — Link between signature and record** | `packet_sha256` cryptographically links the instrument ID, timestamp, and data — any modification is detectable |

### 13.3 ALCOA+ at the Edge

| ALCOA+ Principle | Box Implementation |
|------------------|-------------------|
| **Attributable** | Every reading carries `device_id` and `instrument_id`; traceable to a specific physical instrument at a specific site |
| **Legible** | Data captured as structured JSON with human-readable fields; raw bytes preserved |
| **Contemporaneous** | `captured_at` timestamp recorded at the moment of serial port read, using NTP-synchronized hardware RTC |
| **Original** | `raw_bytes_b64` preserves the exact bytes output by the instrument; `raw_sha256` detects any modification |
| **Accurate** | Parser modules validated against known instrument output during qualification; parser output compared to instrument display during OQ |
| **Complete** | Offline store-and-forward ensures no readings lost during network outages; gap detection on reconnection |
| **Consistent** | Same parser module applied uniformly to all readings from a given instrument |
| **Enduring** | Local queue with 7-day retention (configurable); cloud PostgreSQL for long-term storage |
| **Available** | Local queue available offline; cloud dashboard available 24/7; audit trail always retrievable |

### 13.4 Qualification Approach

**Installation Qualification (IQ):**
- Verify Box hardware serial number matches shipping manifest
- Verify firmware version matches provisioning record
- Verify device_id in cloud registry
- Verify tamper-evident seals intact
- Verify serial cable connections to instrument
- Verify network connectivity (ping management endpoint)

**Operational Qualification (OQ):**
- Generate known test output on instrument (or use instrument's built-in self-test)
- Verify reading appears in cloud dashboard with correct parsed values
- Verify `captured_at` timestamp is accurate (within ±2 seconds of instrument print time)
- Verify SHA-256 integrity: download raw bytes from cloud, compute hash, verify matches stored `raw_sha256`
- Simulate network outage: disconnect Ethernet, generate 10 readings on instrument, reconnect, verify all 10 appear in cloud
- Verify audit trail entries for all 10 readings

**Performance Qualification (PQ):**
- 30-day observation period: verify all readings captured and transmitted without data loss
- Monthly reconciliation report: cloud audit trail versus instrument printout

### 13.5 Computer System Validation (CSV) Documentation Package

BioNexus provides the following validation documentation for each Box installation (in partnership with GMP4U):

- User Requirements Specification (URS)
- Functional Requirements Specification (FRS)
- Hardware Design Specification (this document + Appendix A: Site Configuration Record)
- Software Design Specification (this document, Sections 5–10)
- Installation Qualification Protocol and Report (IQ)
- Operational Qualification Protocol and Report (OQ)
- Risk Assessment (per ICH Q9)
- Traceability Matrix (requirements → design → test)

---

## 14. Physical and Environmental Requirements

### 14.1 Enclosure Specifications

| Parameter | Specification |
|-----------|---------------|
| Enclosure type | ABS plastic, desktop (bench-top) or DIN-rail mount |
| IP rating | IP40 standard; IP54 available for controlled cleanroom environments |
| Dimensions | ~120 mm × 80 mm × 40 mm (bench-top); 1 DIN module (75 mm × 90 mm) for rail mount |
| Color | RAL 7035 light grey (standard lab equipment color) |
| Labeling | Asset tag, serial number, device ID, CE/FCC markings, UL listing (planned) |
| Tamper evidence | Tamper-evident screw seals on all access panels; holographic serial stickers |
| Mounting | M4 rubber feet (bench-top); 35 mm DIN rail clip (rail mount) |
| Ventilation | Passive convection; no fans (fan-less design for cleanroom compatibility, eliminates particle generation) |

### 14.2 Electrical Requirements

| Parameter | Specification |
|-----------|---------------|
| Input voltage | 5V DC (USB-C) or 9–24V DC (barrel jack, via internal buck converter) |
| Power consumption | 3 W typical, 7 W peak |
| PoE support | 802.3af (15.4 W) on PoE carrier board variant |
| EMC | CE Class B, FCC Part 15 Class B (planned) |
| Operating isolation | Opto-isolated RS232 transceivers on industrial carrier board (optional, for noisy environments) |
| ESD protection | TVS diodes on all external interfaces |

### 14.3 Environmental Requirements

| Parameter | Standard | Industrial (optional) |
|-----------|----------|----------------------|
| Operating temperature | 0°C to 55°C | -25°C to 70°C |
| Storage temperature | -20°C to 70°C | -40°C to 85°C |
| Relative humidity | 20% to 80% non-condensing | 5% to 95% non-condensing |
| Altitude | 0 to 2000 m | 0 to 4000 m |
| Vibration | IEC 60068-2-6 | IEC 60068-2-6 (enhanced profile) |
| Shock | IEC 60068-2-27 | IEC 60068-2-27 (enhanced) |
| Cleanroom compatibility | Class D (ISO 8) passively | Class C (ISO 7) with IP54 enclosure |

**Note on cleanroom environments:** The fan-less, sealed design is critical for Class C/D cleanroom compatibility. Conventional fan-cooled computers generate and recirculate particulates, violating GMP cleanroom requirements. The BioNexus Box passive thermal design is a deliberate product decision driven by GxP lab environment requirements.

### 14.4 Cable and Installation Considerations

- **RS232 cables**: Shielded, braided cables required for runs > 3 m; maximum cable length 15 m at 9600 baud
- **Cable routing**: Cables should not be routed through ventilation ducts or adjacent to high-voltage power cables to minimize EMI interference
- **Grounding**: For opto-isolated variants, instrument and Box grounds are isolated; no loopback ground loops
- **Vertical clearance**: Minimum 20 mm clearance above and below enclosure for passive cooling airflow
- **Location**: Not to be installed directly on top of instruments that generate significant heat (e.g., autoclaves)
- **Labeling**: All connected cables must be labeled with instrument ID and port number per GMP documentation requirements

---

## 15. Roadmap

### 15.1 Phase 1 — Current (v1.x)

- RS232 and USB-serial interface support
- Collector, Queue, and Uplink Agent core pipeline
- Local SQLite store-and-forward
- HTTPS + API key authentication
- SHA-256 data integrity at packet level
- Heartbeat and basic monitoring
- Remote configuration push via heartbeat response
- A/B partition OTA firmware update mechanism
- Parser modules: dissolution, HPLC (Waters ARW), pH/conductivity, UV-Vis (generic), balance (SBI)
- Bench-top enclosure (IP40)

### 15.2 Phase 2 — Q3 2026

- **TPM 2.0 integration**: Device identity via hardware-secured certificates; mTLS
- **Secure boot**: dm-verity root filesystem; TPM-sealed LUKS key
- **Extended parser library**: Shimadzu HPLC, Agilent ChemStation, Erweka dissolution, Sartorius balance, Mettler Toledo full series
- **TCP/IP socket collection**: Raw socket polling for networked instruments
- **Modbus TCP**: Environmental monitoring integration
- **DIN-rail enclosure**: IP54 rated for controlled environments
- **PoE support**: Eliminate separate power cable for simplified installation
- **Hardware RTC**: Battery-backed, eliminates timestamp drift risk during boot

### 15.3 Phase 3 — Q1 2027

- **Multi-instrument hub**: Box supporting 8+ simultaneous instrument connections via internal USB hub + RS232 multiplexer
- **Wi-Fi uplink**: Dual-band 802.11ac (Wi-Fi 5) as backup or primary uplink for sites without convenient Ethernet
- **Bluetooth LE**: Interface to modern BLE-enabled instruments (newer Mettler Toledo, Sartorius balances)
- **OPC-UA client**: Support for Industry 4.0 / NAMUR OPC-UA instruments
- **Edge analytics**: Local statistical process control (SPC) calculations; Shewhart control charts generated on the Box; alerts sent without round-trip to cloud
- **Edge display**: Optional 3.5" touch display for local status and last-reading view (cleanroom-compatible glove operation)
- **Redundant uplink**: LTE/4G cellular backup via USB modem; automatic failover from Ethernet

### 15.4 Phase 4 — 2027+

- **Raw signal capture**: Full chromatogram / spectrum raw ADC data capture and upload for HPLC and spectrophotometry (large file handling, incremental upload)
- **On-box AI parsing**: Local LLM inference for instrument output parsing without cloud round-trip (privacy-preserving, offline-capable)
- **Instrument calibration reminders**: Box aware of instrument calibration schedules; alerts when calibration due date approaching
- **Multi-site aggregation**: Single Box acting as aggregation point for multiple sub-connected satellite devices (star topology for large labs)
- **FIPS 140-3 certification**: Hardware cryptographic module certification for US federal / DoD-adjacent customers

---

## Appendix A: Instrument Parser Implementation Reference

### Parser Output Schema (common fields)

All parsers MUST produce a `ParsedReading` with at least these fields:

```python
@dataclass
class ParsedReading:
    instrument_type: str        # hplc | dissolution | uv_vis | ph | balance | karl_fischer | env
    instrument_id: str          # From Box config
    sample_id: str              # As reported by instrument (pseudonymized; no PII)
    captured_at: datetime       # UTC timestamp of serial port read
    result_data: dict           # Instrument-specific structured results
    raw_text: str               # Human-readable representation of raw output
    parser_version: str         # Parser module version (for traceability)
    parse_confidence: float     # 0.0 to 1.0 (1.0 = unambiguous parse, 0.0 = best-effort)
    parse_warnings: list[str]   # Non-fatal parsing issues
```

### Parser Development Checklist

- [ ] Implement `BaseParser.parse()` and `BaseParser.get_schema()`
- [ ] Handle incomplete buffers (return `None`, do not raise)
- [ ] Handle malformed data (raise `ParserError` with details)
- [ ] Handle all known encoding variants for this instrument model (ASCII, Latin-1, CP1252)
- [ ] Write unit tests covering: clean output, partial output, malformed output, empty output
- [ ] Test against real instrument output files (stored in `tests/instrument_fixtures/`)
- [ ] Document baud rate, parity, stop bits, and framing for this instrument
- [ ] Record parser_version as semantic version string

---

## Appendix B: Network Requirements for Customer Site

To install and operate a BioNexus Box, the customer network must allow:

| Protocol | Destination | Port | Direction | Purpose |
|----------|-------------|------|-----------|---------|
| HTTPS | `api.bionexus.io` | 443/TCP | Outbound | Data upload + heartbeat |
| NTP | `pool.ntp.org` or customer NTP | 123/UDP | Outbound | Clock synchronization |
| DNS | Customer DNS server | 53/UDP+TCP | Outbound | Name resolution |
| SSH | BioNexus management IP range | 22/TCP | Inbound | Remote diagnostics (optional) |

No inbound ports need to be opened beyond SSH (which is optional; remote diagnostics can also be initiated via the heartbeat push mechanism). No direct connection between the Box and customer LIMS, ERP, or other internal systems is required.

---

**Document Version**: 1.0
**Status**: Draft — Engineering Reference
**Last Updated**: 2026-02-28
**Review Cycle**: Quarterly or on major firmware release
**Owner**: BioNexus Engineering
**Classification**: Internal Engineering — Restricted Distribution
