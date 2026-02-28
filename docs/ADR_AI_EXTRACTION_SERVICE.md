# Architecture Decision Record: AI Extraction Service
## BioNexus Platform — ADR-001

---

**Document ID:** BNX-ADR-001
**Version:** 1.0
**Status:** Proposed
**Date:** 2026-02-28
**Decision Makers:** BioNexus Engineering Lead, Head of Product, Regulatory Affairs Lead, GMP4U (Johannes Eberhardt — CSV/Qualification Specialist)
**Review Cycle:** Upon major model release, significant pricing change, or relevant regulatory guidance update
**Classification:** Architecture — Internal Engineering

---

## Document Control

### Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-02-10 | BioNexus Engineering | Initial draft for internal review |
| 0.2 | 2026-02-20 | BioNexus Engineering | Added GDPR assessment and GxP validation sections |
| 1.0 | 2026-02-28 | BioNexus Engineering | Proposed for decision |

### Related Documents

| Document ID | Title |
|-------------|-------|
| BNX-COMP-001 | GxP Compliance Master Document |
| BNX-VAL-001 | System Validation Plan |
| BNX-SEC-001 | Security Architecture |
| PARSING_ARCHITECTURE.md | BioNexus Parsing Service Architecture |

---

## Table of Contents

1. [Context](#1-context)
2. [Decision Drivers](#2-decision-drivers)
3. [Options Considered](#3-options-considered)
4. [Decision Matrix](#4-decision-matrix)
5. [Recommended Decision](#5-recommended-decision)
6. [Data Privacy Assessment](#6-data-privacy-assessment)
7. [GxP Validation Considerations](#7-gxp-validation-considerations)
8. [Cost Analysis](#8-cost-analysis)
9. [Fallback Strategy](#9-fallback-strategy)
10. [Monitoring and Quality](#10-monitoring-and-quality)
11. [AI Hallucination Prevention](#11-ai-hallucination-prevention)
12. [Vendor Assessment Under GAMP5](#12-vendor-assessment-under-gamp5)
13. [Consequences](#13-consequences)
14. [Review Triggers](#14-review-triggers)

---

## 1. Context

### 1.1 The Problem

Laboratory instruments — HPLC systems, dissolution testers, UV-Vis spectrophotometers, pH meters, centrifuges, PCR machines, and others — produce output in a wide variety of file formats. These include vendor-specific CSV dialects, PDF reports, plain-text instrument logs, and proprietary binary exports. The structure, field naming, and layout of these files differs significantly across instrument manufacturers, firmware versions, and customer configuration. A Shimadzu HPLC system does not produce the same CSV schema as an Agilent system, and neither produces the same format across software versions.

The current manual process at BioNexus customer sites involves lab technicians reading these output files and manually transcribing values into LIMS or spreadsheet systems. This process is:

- **Error-prone**: Transcription errors introduce inaccuracies into batch records and sample results.
- **Slow**: Manual entry for a single dissolution run file (potentially dozens of rows with multiple result columns) can take 20–40 minutes.
- **Non-attributable**: Spreadsheet entry rarely captures contemporaneous timestamps and user attribution at the field level, which is a direct deficiency under ALCOA+.
- **Unscalable**: As customers onboard more instruments, the manual burden grows linearly.

### 1.2 What AI Extraction Solves

Large language model (LLM) AI services can parse unstructured and semi-structured text and produce structured JSON output corresponding to a defined schema. When combined with strict schema enforcement via Pydantic and a mandatory human review gate, AI extraction can:

- **Eliminate manual transcription** for the majority of routine instrument output files.
- **Accelerate data intake**: Extraction of a multi-page PDF instrument report from seconds to under 15 seconds with AI, versus 20–40 minutes manually.
- **Reduce transcription errors**: Errors caused by fatigue or misreading are replaced by a deterministic schema validation pass, with a human reviewer catching residual AI mistakes rather than performing the transcription themselves.
- **Support ALCOA+ attribution**: Every extraction is attributed to a model version, a requesting user, a timestamp, and an immutable SHA-256 hash of the source file.

### 1.3 Instrument Data Types Covered

The AI extraction service is scoped to extract structured data from the following instrument output types:

| Instrument Category | Common Output Formats | Data Fields Extracted |
|---------------------|-----------------------|-----------------------|
| HPLC Systems | CSV, PDF reports | Sample ID, run timestamp, peak areas, retention times, batch ID |
| Dissolution Testers | CSV, plain-text logs | Sample ID, vessel number, timepoint, % dissolved, temperature |
| UV-Vis Spectrophotometers | CSV, PDF | Sample ID, wavelength, absorbance, concentration |
| pH Meters | CSV, plain-text | Sample ID, pH value, temperature, electrode calibration date |
| Centrifuges | PDF maintenance logs, CSV | Equipment ID, run parameters, maintenance dates, status |
| General Lab Equipment | CSV inventory files | Equipment ID, name, type, location, serial number, status |
| Sample Management | CSV, barcode logs | Sample ID, type, collection timestamp, storage location |

### 1.4 Current Implementation State

The parsing pipeline is currently implemented in:

- `bionexus-platform/backend/core/parsing_service.py`: `ParsingService` class with `upload_file()`, `parse_file()`, `validate_and_confirm()`, and `reject_parsing()` methods.
- `bionexus-platform/backend/core/parsing_schemas.py`: Pydantic `EquipmentData`, `SampleData`, and `BatchExtractionResult` schemas with `extra="forbid"` configuration.
- `bionexus-platform/PARSING_ARCHITECTURE.md`: Architecture documentation.

The `parse_file()` method accepts `ai_extracted_data: dict` as a parameter, meaning the AI call itself is currently external to the service. The service validates AI output against the schema and manages the workflow state. The actual API call to GPT-4 or Claude is referenced in documentation but not yet implemented as a managed service component. This ADR decides how that external API call should be implemented, which provider should be used, and what the operational and compliance posture should be.

---

## 2. Decision Drivers

The following factors are ranked by importance for BioNexus's specific situation. The weighting values are used in the Decision Matrix in Section 4.

| # | Driver | Weight | Rationale |
|---|--------|--------|-----------|
| 1 | **Extraction accuracy** | 25% | Incorrect extractions that pass human review enter the batch record. In GxP environments, data accuracy is a primary quality metric. |
| 2 | **Data privacy and GDPR compliance** | 20% | Instrument files are sent to a third-party API. Must comply with GDPR Art. 28 (Data Processing Agreement), data residency requirements for EU customers, and 21 CFR Part 11 electronic records obligations. |
| 3 | **Regulatory compliance posture** | 15% | The chosen architecture must be defensible in an FDA inspection or EU regulatory audit. Traceability, change control, and validation must be achievable. |
| 4 | **Operational reliability and availability** | 12% | Lab workflows depend on timely data intake. Service unavailability must degrade gracefully, not block lab operations. |
| 5 | **Cost at scale** | 10% | Token-based pricing means costs scale with file volume. At 10,000 files/month across a customer base, per-file cost becomes a material line item. |
| 6 | **Latency** | 8% | Lab technicians uploading files expect feedback within a reasonable time. Extraction taking more than 30 seconds for a typical file will be perceived as slow. |
| 7 | **Vendor lock-in and provider risk** | 5% | Dependency on a single external AI provider creates supplier risk. Provider terms-of-service changes, pricing changes, or service discontinuation can disrupt operations. |
| 8 | **Engineering implementation complexity** | 5% | The parsing pipeline is already implemented. The remaining work is the AI API call layer. Implementation complexity affects time-to-market. |

---

## 3. Options Considered

### Option A: OpenAI GPT-4 / GPT-4o

**Description:** Use OpenAI's GPT-4 or GPT-4o API as the exclusive AI extraction provider. The `parse_file()` method would call the OpenAI Chat Completions API, pass the file content as text within the prompt, and receive a structured JSON response.

**Technical Details:**
- API: `https://api.openai.com/v1/chat/completions`
- Models: `gpt-4-turbo`, `gpt-4o`, `gpt-4o-mini`
- Structured output: Supports JSON mode and function calling for schema-constrained output
- Input context: GPT-4o supports up to 128,000 tokens (~100,000 words), sufficient for large instrument reports
- Latency: Typically 3–15 seconds for a standard instrument file

**Strengths:**
- Highest public benchmark scores on structured extraction tasks as of early 2026
- JSON mode and function calling with schema enforcement reduces hallucination risk at the API level
- Mature, well-documented API with extensive client library support
- Wide developer familiarity; easier to hire for

**Weaknesses:**
- Data residency: By default, OpenAI processes data on US infrastructure. EU data residency is available via the Azure OpenAI Service (separate product), but this requires an additional Azure relationship and contract.
- GDPR Art. 28: OpenAI's standard Data Processing Agreement is available but the terms around sub-processor chains and international data transfers require careful legal review for EU customer deployments.
- No zero data retention by default on the standard API tier: prompts may be used for abuse monitoring for up to 30 days unless Zero Data Retention is explicitly configured.
- 21 CFR Part 11: No specific pharmaceutical regulatory track record with FDA; all compliance burden remains with BioNexus.
- Vendor pricing and terms have changed multiple times; GPT-4 was deprecated and replaced by GPT-4o; change management overhead is non-trivial.

**Pricing (as of 2026-02):**
- GPT-4o: ~$2.50 / 1M input tokens, ~$10.00 / 1M output tokens
- GPT-4o-mini: ~$0.15 / 1M input tokens, ~$0.60 / 1M output tokens
- A typical instrument CSV file (5KB of text) uses approximately 1,500–3,000 input tokens and 500–1,000 output tokens

---

### Option B: Anthropic Claude (Sonnet / Opus)

**Description:** Use Anthropic's Claude API as the exclusive AI extraction provider. The current `parsing_service.py` already references `claude-3` as a potential `extraction_model` value. Claude 3.5 Sonnet and Claude 3 Opus are the primary candidates.

**Technical Details:**
- API: `https://api.anthropic.com/v1/messages`
- Models: `claude-sonnet-4-5`, `claude-opus-4-5`, `claude-haiku-3-5`
- Structured output: Supports tool use (function calling) for schema-constrained JSON output
- Input context: Up to 200,000 tokens, larger than GPT-4o, better for large PDF reports
- Latency: Typically 4–12 seconds for a standard instrument file with Sonnet

**Strengths:**
- Strong performance on structured extraction and instruction-following tasks
- 200K context window is advantageous for large multi-page PDF instrument reports
- Anthropic publishes a GDPR-compliant Data Processing Addendum (DPA); EU data residency options available
- Claude's Constitutional AI training emphasizes not fabricating information, which has relevance to hallucination reduction (though Pydantic validation remains the primary safeguard regardless of provider)
- Tool use (function calling) with strict JSON Schema input reduces schema non-compliance in raw model output

**Weaknesses:**
- Slightly less developer tooling ecosystem compared to OpenAI
- Same fundamental GDPR and 21 CFR Part 11 concerns apply as with any external API provider
- Model versioning and deprecation risk exists (as with all LLM providers)
- No on-premises deployment option; data must leave BioNexus infrastructure

**Pricing (as of 2026-02):**
- Claude 3.5 Sonnet: ~$3.00 / 1M input tokens, ~$15.00 / 1M output tokens
- Claude 3 Haiku: ~$0.25 / 1M input tokens, ~$1.25 / 1M output tokens
- Claude 3 Opus: ~$15.00 / 1M input tokens, ~$75.00 / 1M output tokens

---

### Option C: Self-Hosted Open-Source Model (Llama 3, Mistral, or similar)

**Description:** Deploy an open-source LLM on BioNexus-controlled infrastructure (GCP Vertex AI custom endpoints, GKE, or customer-premises hardware). Candidate models include Meta Llama 3.1 70B/405B, Mistral Large 2, or Mixtral 8x22B.

**Technical Details:**
- Deployment: GCP Vertex AI Custom Model Serving, or GKE with GPU nodes (NVIDIA A100/H100)
- Models: Llama 3.1 70B (minimum viable), Llama 3.1 405B (higher quality, higher cost)
- Structured output: Requires prompt engineering and potentially constrained decoding (outlines, lm-format-enforcer) to reliably produce schema-valid JSON
- Input context: 128K tokens (Llama 3.1), varies by model
- Latency: 10–60 seconds depending on hardware and model size; significantly higher than managed APIs

**Strengths:**
- No data leaves BioNexus infrastructure: eliminates all third-party data processing concerns under GDPR Art. 28 for the extraction step
- No per-token cost at inference time once infrastructure is provisioned
- Full control over model version, upgrade timing, and change management
- Can be deployed in customer-premises configuration for customers with strict data locality requirements

**Weaknesses:**
- Extraction accuracy is meaningfully lower than frontier models (GPT-4o, Claude Sonnet) on complex structured extraction tasks. For HPLC or dissolution tester multi-column reports, error rates on smaller open-source models can be 5–15% vs. 1–3% for frontier models.
- Infrastructure cost is high: a GCP A100 GPU node for serving a 70B model costs approximately $3–5/hour, or ~$2,200–$3,600/month for continuous availability. Spot instances reduce cost but introduce availability risk.
- Engineering complexity is significantly higher: model serving infrastructure, prompt versioning, scaling, monitoring, and model updates all require dedicated engineering effort.
- GxP validation is harder: the model itself must be treated as a validated component, meaning any model update requires a change control process and re-validation testing.
- No SLA from the model developer; uptime is entirely BioNexus-managed.
- JSON schema adherence without constrained decoding is unreliable in smaller open-source models, increasing the rate of schema validation failures.

**Pricing:**
- Infrastructure: ~$2,200–$5,000/month for GCP GPU serving (A100 node, sustained use discount applied)
- Engineering overhead: estimated 2–4 engineer-weeks initial setup; ongoing maintenance ~0.5 FTE
- No per-file variable cost at inference time

---

### Option D: Hybrid Approach — Cloud AI Primary with Configurable Provider and Rule-Based Fallback

**Description:** Implement an `AIExtractionClient` abstraction layer that supports multiple backend providers (Claude primary, OpenAI secondary), with a rule-based parser as a deterministic fallback for simple, well-structured file formats. The provider is configurable per environment and per tenant. This is the recommended option (see Section 5).

**Technical Details:**
- Abstraction layer: `core/ai_extraction/client.py` with a `BaseExtractionClient` interface
- Primary provider: Anthropic Claude 3.5 Sonnet via `claude_client.py`
- Secondary/fallback provider: OpenAI GPT-4o via `openai_client.py` (switchable via Django settings)
- Rule-based fallback: Template-based CSV parser for known, fixed-format files (e.g., specific instrument models that produce consistent output)
- Retry logic: Automatic retry with exponential backoff on transient errors; automatic provider failover after N consecutive failures
- Provider switching: Can be changed in `settings.py` (`EXTRACTION_PRIMARY_PROVIDER = "claude"`) without code deployment

**Strengths:**
- No single point of failure: if Claude API is unavailable, fall back to OpenAI; if both are unavailable, fall back to rule-based or queued processing
- Provider negotiation: can switch primary provider if pricing changes significantly or if a new model significantly outperforms the current one
- Rule-based fallback for known formats eliminates API cost entirely for those files and increases reliability
- Isolates provider-specific code behind an interface, making future provider additions straightforward
- Best accuracy: frontier models used for complex, variable-format files; deterministic parsing for known formats

**Weaknesses:**
- Higher initial implementation complexity vs. single-provider integration
- Two AI provider relationships to maintain (contracts, DPAs, API keys)
- Rule-based fallback requires maintenance as new instrument models are onboarded
- Two providers means two change management processes when models are updated

---

### Option E: Rule-Based Parsing Only (No AI)

**Description:** Implement all file parsing using traditional regex, template matching, and CSV/PDF parsing libraries (Python's `csv` module, `pdfplumber`, `pypdf`). Each supported instrument model has a dedicated parser class.

**Technical Details:**
- Framework: Python `csv`, `pdfplumber` for PDF, `re` for regex-based text parsing
- Architecture: `InstrumentParser` base class with subclasses per instrument model/format
- Schema validation: Same Pydantic schemas as the AI path; parsers must produce conformant output

**Strengths:**
- Fully deterministic: same input always produces same output, which simplifies GxP validation
- No external API calls: no data privacy implications, no third-party dependency
- No per-file variable cost
- Lower latency: parsing is essentially instantaneous
- No hallucination risk at the parsing stage

**Weaknesses:**
- Does not scale to new instrument formats without engineering effort: each new instrument model or firmware version requires a new parser
- BioNexus targets customers with diverse instrument fleets; maintaining parsers for every instrument variant is not viable
- Fragile to minor format changes: a new firmware version that adds a single column or changes a header name breaks the parser
- Competitive disadvantage: the core value proposition of BioNexus includes reducing the integration burden for new instruments; rule-based parsing negates this
- Cannot handle PDF reports with variable layouts (e.g., dissolution reports with different numbers of vessels)
- Not viable as the sole parsing strategy for a multi-instrument, multi-vendor product

---

## 4. Decision Matrix

The following table scores each option against each decision driver. Scores are 1 (poor) to 5 (excellent). Weighted scores are Driver Weight × Raw Score. Maximum possible total is 500.

| Decision Driver | Weight | Option A (OpenAI) | Option B (Claude) | Option C (Self-Hosted) | Option D (Hybrid) | Option E (Rule-Based) |
|-----------------|--------|-------------------|-------------------|------------------------|-------------------|-----------------------|
| Extraction accuracy | 25% | 5 | 5 | 3 | 5 | 2 |
| Data privacy / GDPR | 20% | 3 | 4 | 5 | 4 | 5 |
| Regulatory compliance posture | 15% | 3 | 4 | 4 | 4 | 5 |
| Operational reliability | 12% | 4 | 4 | 2 | 5 | 5 |
| Cost at scale | 10% | 3 | 3 | 2 | 3 | 5 |
| Latency | 8% | 4 | 4 | 2 | 4 | 5 |
| Vendor lock-in risk | 5% | 2 | 2 | 5 | 4 | 5 |
| Engineering complexity | 5% | 4 | 4 | 2 | 3 | 3 |
| **Weighted Total** | **100%** | **3.88** | **4.08** | **3.15** | **4.19** | **3.79** |

**Scoring rationale notes:**

- Option C receives a lower data privacy score (5 raw) than Option E because while self-hosting eliminates third-party data processing, it introduces GxP validation complexity for the model itself that creates a compliance burden distinct from, but comparable to, the GDPR concern for cloud options.
- Option D receives a 4 on data privacy because both cloud providers have GDPR DPAs available and the abstraction layer allows routing specific tenant data to appropriate providers (e.g., EU-domiciled customers can be configured to use EU-region API endpoints).
- Option E's low extraction accuracy score (2) reflects that it is not viable for the heterogeneous instrument landscape BioNexus serves, making its other high scores partially academic.
- Option D's reliability score of 5 reflects the multi-layer fallback architecture (primary cloud AI → secondary cloud AI → rule-based).

---

## 5. Recommended Decision

**Decision: Option D — Hybrid Approach**

**Primary AI Provider: Anthropic Claude 3.5 Sonnet**
**Secondary AI Provider: OpenAI GPT-4o (failover)**
**Rule-Based Fallback: For known, fixed-format instrument files**

### 5.1 Rationale

Option D achieves the highest weighted score in the decision matrix (4.19) and is the only option that adequately addresses all of the top three decision drivers simultaneously.

**Why Claude as primary over OpenAI:**
Claude 3.5 Sonnet and GPT-4o are comparable in extraction accuracy for structured data tasks. Claude is selected as the primary provider for three reasons:

1. **Data Privacy**: Anthropic's DPA terms and EU data processing commitments are currently more straightforward than OpenAI's standard API terms for GDPR-compliant configurations. Claude's API offers EU API endpoint options without requiring a separate Azure relationship.
2. **Context Window**: Claude's 200K context window (vs. GPT-4o's 128K) is advantageous for large multi-page dissolution or HPLC batch reports that may contain dozens of sample rows, run metadata, and calibration data in a single file.
3. **Instruction Following**: Claude's Constitutional AI training and tool use implementation has demonstrated strong instruction-following fidelity in structured extraction tasks, which is directly relevant to schema compliance.

OpenAI GPT-4o is retained as the secondary provider because it is equally capable, offers a different failure domain from Claude, and ensures BioNexus is not entirely dependent on a single AI vendor.

**Why not Option C (Self-Hosted):**
The engineering cost to operate reliable GPU infrastructure on GCP, combined with lower extraction accuracy for complex instrument files and the GxP validation burden of treating the model itself as a validated component, makes self-hosting unviable at BioNexus's current scale and engineering capacity. This option should be re-evaluated when monthly extraction volumes exceed 50,000 files/month or when regulatory requirements from a specific large customer make cloud AI processing untenable.

**Why not Option E (Rule-Based Only):**
Rule-based parsing is not viable as the sole strategy for a multi-vendor, multi-instrument product. It is retained as a component of Option D for known, high-volume fixed-format files where deterministic parsing is both possible and more reliable than AI.

### 5.2 Implementation Architecture

```
┌────────────────────────────────────────────────────────────┐
│  ParsingService.parse_file() — existing implementation      │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│  AIExtractionOrchestrator                                   │
│  - Selects extraction strategy based on file type           │
│  - Invokes primary, fallback, or rule-based client          │
│  - Returns: ai_extracted_data: dict                         │
└──────────────────────────┬─────────────────────────────────┘
                           │
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
│ ClaudeClient    │  │ OpenAIClient │  │ RuleBasedParser  │
│ (primary)       │  │ (secondary)  │  │ (fixed formats)  │
│ Sonnet 3.5      │  │ GPT-4o       │  │ CSV templates    │
└─────────────────┘  └──────────────┘  └──────────────────┘
```

Both AI clients implement the same `BaseExtractionClient` interface:

```python
class BaseExtractionClient(ABC):
    @abstractmethod
    def extract(
        self,
        file_content: str,
        file_type: str,
        schema_hint: str,
    ) -> dict:
        """Returns raw dict matching BatchExtractionResult schema."""
        ...
```

Provider selection and failover logic:

```python
EXTRACTION_PRIMARY_PROVIDER = env("EXTRACTION_PRIMARY_PROVIDER", default="claude")
EXTRACTION_FALLBACK_PROVIDER = env("EXTRACTION_FALLBACK_PROVIDER", default="openai")
EXTRACTION_TIMEOUT_SECONDS = int(env("EXTRACTION_TIMEOUT_SECONDS", default=60))
EXTRACTION_MAX_RETRIES = int(env("EXTRACTION_MAX_RETRIES", default=2))
```

---

## 6. Data Privacy Assessment

### 6.1 What Data Is Sent to the AI Provider

When a file is submitted for AI extraction, the following data is transmitted to the external AI API:

| Data Element | Description | Sensitivity |
|--------------|-------------|-------------|
| File text content | The raw text of the instrument output file, PDF converted to text | Low — contains equipment IDs, sample IDs (pseudonymized), measurement values, timestamps |
| System prompt | BioNexus's extraction prompt describing the schema and instructions | Non-sensitive |
| Tool/function schema | The JSON Schema derived from Pydantic models | Non-sensitive |
| Tenant identifier | Not included in the prompt; only used internally for audit trail | Not transmitted |
| User identity | Not included in the API call payload | Not transmitted |

**Key Data Characteristics:**
- Instrument output files contain **no PII** under BioNexus's No PII Policy. Sample IDs are pseudonymized identifiers (e.g., `SMP-2026-0042`), not patient names, dates of birth, or other personal data.
- Equipment IDs and lab location strings may constitute organizational data about the customer, but are not personal data under GDPR.
- In the event a customer uploads a file that inadvertently contains personal data (e.g., a technician's name in a notes column), the Pydantic schema's `extra="forbid"` configuration will cause schema validation to fail if the field is not in the schema. If the data appears within a permitted text field (e.g., `notes`), it would be transmitted. This risk is addressed in Section 6.4.

### 6.2 GDPR Compliance Assessment

**Applicable Framework:** GDPR Regulation (EU) 2016/679

**Data Controller:** The BioNexus customer (the pharmaceutical or biotech company operating the lab)

**Data Processor:** BioNexus GmbH (or relevant legal entity)

**Sub-Processor:** Anthropic (primary) and OpenAI (secondary)

**Article 28 Requirements:**

GDPR Article 28 requires that a Data Controller only use Data Processors that provide "sufficient guarantees" to implement appropriate technical and organizational measures, and that processing is governed by a Data Processing Agreement (DPA).

| Requirement | Anthropic | OpenAI | Status |
|-------------|-----------|--------|--------|
| DPA available | Yes — Anthropic DPA available on request | Yes — OpenAI DPA available | Required before production use with EU customers |
| Sub-processor list | Published and maintained | Published and maintained | Acceptable |
| Data deletion on request | Supported; prompts not retained for training on API | Supported with Zero Data Retention option | Must be configured |
| EU data residency | EU endpoints available (api.eu.anthropic.com region routing) | EU via Azure OpenAI Service | Must be configured for EU customers |
| International transfer mechanism | Standard Contractual Clauses (SCCs) | Standard Contractual Clauses (SCCs) | SCCs must be executed |
| Security certifications | SOC 2 Type II, ISO 27001 | SOC 2 Type II, ISO 27001 | Acceptable |

**Data Transfer:**
- For EU customers, API calls must be routed to EU-region endpoints to avoid transfers to the US without an adequate transfer mechanism.
- Standard Contractual Clauses (SCCs, Module 2 — Controller to Processor) must be executed with each AI provider.
- BioNexus must include Anthropic and OpenAI in its sub-processor register maintained for customer DPAs.

**Retention:**
- Anthropic API: prompts are not used for model training and are subject to a 30-day transient retention period for safety monitoring unless a zero-retention arrangement is negotiated.
- OpenAI API: prompts on the standard API are retained for up to 30 days for abuse monitoring; Zero Data Retention (ZDR) is available under an enterprise agreement.
- **Recommendation**: Negotiate Zero Data Retention terms with both providers before EU production launch.

**Data Minimization (Art. 5(1)(c)):**
- Only the text content of the file is transmitted; no tenant metadata, user identifiers, or system internals are included in the API payload.
- Where possible, file content should be stripped of any free-text fields before transmission (to be evaluated per instrument type).

### 6.3 21 CFR Part 11 Implications

21 CFR Part 11 governs electronic records and electronic signatures in FDA-regulated environments.

**Key Considerations:**

1. **Electronic Records Processed Externally**: The raw file content (which may be an electronic record) is transmitted to an external processor. The original record (with SHA-256 hash) remains in BioNexus's immutable `RawFile` table. The AI service processes a copy, not the original. The original electronic record is never modified by the AI service.

2. **Audit Trail Completeness**: The `extraction_model` field in `ParsedData` records which AI model was used. This creates a traceable link between the AI extraction and the source file, which is sufficient for audit trail purposes. The model version used is part of the audit record.

3. **AI Output Is Not an Electronic Record Until Validated**: Under BioNexus's architecture, `ParsedData.parsed_json` (raw AI output) has state `PENDING` and is explicitly not accepted into the system until human review sets state to `VALIDATED`. The human reviewer, not the AI, is the named individual responsible for the data per 21 CFR Part 11.

4. **System Access Controls**: Access to the AI provider APIs is controlled via API keys managed in environment variables, not hardcoded. Key rotation, access logging, and restriction to authorized service accounts must be implemented.

5. **Validation of the AI Component**: An AI model is a non-deterministic system component. Section 7 addresses the GxP validation strategy for this component.

### 6.4 Mitigation Measures

| Risk | Mitigation |
|------|------------|
| PII inadvertently in instrument file | Pydantic `extra="forbid"` rejects unknown fields; human reviewer is the last gate; customer training on No PII Policy |
| Data transmitted to US infrastructure | EU-region API endpoint configuration; SCCs executed; DPA in place |
| AI provider retains prompt data | Zero Data Retention negotiated; DPA includes sub-processor obligations on data deletion |
| Provider sub-processor change without notice | DPA includes requirement for advance notification of sub-processor changes |
| AI provider service breach | Data transmitted is pseudonymized and non-PII; impact assessment reflects low severity |
| Audit trail gap for external processing | `extraction_model`, `extracted_at`, and source file hash are all recorded in `ParsedData` |

---

## 7. GxP Validation Considerations

### 7.1 Classification of the AI Component Under GAMP5

Under GAMP5 (Good Automated Manufacturing Practice, 5th Edition), software components are classified by category:

| Category | Description | Examples |
|----------|-------------|---------|
| Category 1 | Infrastructure software | Operating systems, networks |
| Category 3 | Non-configured products | Commercial off-the-shelf software with no configuration |
| Category 4 | Configured products | COTS software with configuration (e.g., LIMS) |
| Category 5 | Custom software | Bespoke applications |

**AI Provider Classification:**
Anthropic Claude and OpenAI GPT-4o, accessed via API, are classified as **Category 3 — Non-Configured Products** under GAMP5. They are commercial AI services used without modification of the underlying model. BioNexus's system prompt and schema definitions are configuration, making the integration as a whole **Category 4**.

**Implications of Category 3/4 Classification:**
- BioNexus does not validate the internal mechanics of the AI model.
- BioNexus validates the **output behavior** of the AI model against defined acceptance criteria.
- Validation testing must demonstrate that the configured AI extraction produces acceptable output for a representative sample of instrument file types.
- The supplier (Anthropic or OpenAI) is assessed as a supplier under GAMP5 Section 7 (see Section 12 of this ADR).

### 7.2 Non-Determinism and GxP Validation

The fundamental challenge of AI in GxP environments is that AI models are non-deterministic: the same input may produce slightly different output on different invocations (due to temperature sampling in the model). This is in direct tension with the GxP expectation of reproducibility.

**BioNexus's resolution of this tension:**

1. **AI output is a proposal, not a record**: The AI extraction is stored as `parsed_json` in state `PENDING`. It is not an electronic record until a human reviews and confirms it. The non-determinism of the AI does not affect the integrity of the confirmed data because the confirmed data is the human's decision, not the AI's raw output.

2. **Schema enforcement creates a deterministic gate**: Regardless of what the AI outputs, the Pydantic validation with `extra="forbid"` applies a deterministic pass/fail criterion. A validation failure is consistent and reproducible.

3. **Temperature configuration**: AI API calls should be made with `temperature=0` (or the minimum available setting) to minimize stochastic variation in output. This does not eliminate non-determinism entirely but reduces it significantly for structured extraction tasks.

4. **Accuracy testing is distributional, not individual**: Rather than validating that every invocation produces identical output, validation testing verifies that extraction accuracy across a representative test set meets a defined acceptance criterion (e.g., "field-level accuracy ≥ 95% across 100 test files per instrument type").

### 7.3 Validation Test Strategy

**Validation Documentation Required:**
- `BNX-AI-IQ-001`: Installation Qualification — verify API connection, authentication, response format
- `BNX-AI-OQ-001`: Operational Qualification — verify extraction accuracy against test set
- `BNX-AI-PQ-001`: Performance Qualification — verify extraction performance under production-representative load

**Test Set Requirements:**
The AI extraction IQ/OQ test suite must include:

| Test Category | Minimum Count | Purpose |
|---------------|--------------|---------|
| Known-good files (golden set) | 50 per supported instrument type | Establish baseline accuracy |
| Edge case files | 20 per instrument type | Validate handling of unusual formats |
| Malformed/corrupt files | 10 per instrument type | Verify graceful failure behavior |
| Files with no extractable data | 5 per instrument type | Verify empty result handling |
| Files that intentionally exceed schema | 10 | Verify `extra="forbid"` rejects hallucinated fields |

**Acceptance Criteria:**
- Field-level extraction accuracy: >= 95% on golden test set per instrument type
- Schema validation pass rate on valid files: >= 99%
- False hallucination rate (extra fields accepted): 0% (enforced by Pydantic; this is a binary test)
- Extraction latency at P95: <= 30 seconds per file under normal load

### 7.4 Change Control for AI Model Updates

AI providers release updated model versions on their own schedules. A model update is a change to a validated component and must be managed through BioNexus's change control process.

**Trigger for Change Control:**
- AI provider announces deprecation of a model version currently in production use
- AI provider releases a new major model version (e.g., Claude 4, GPT-5)
- Performance drift is detected (see Section 10.3)

**Change Control Process for AI Model Updates:**
1. Identify new model version and obtain change notification from provider
2. Execute extraction accuracy regression test suite against new model version
3. Compare accuracy metrics to current production baseline
4. If accuracy regression > 2% on any instrument type, investigate before proceeding
5. If accuracy is maintained or improved, raise a Change Control Record (CCR)
6. Document: old model version, new model version, test results, approval chain
7. Update `extraction_model` default in settings; deploy; verify in production sample
8. Close CCR with production verification evidence

**Model Version Pinning:**
To avoid uncontrolled model updates, API calls must specify the exact model version string (e.g., `claude-sonnet-4-5` rather than `claude-sonnet-latest`). Provider-side model updates that change behavior under a pinned model ID are a provider SLA violation and must be raised with the provider.

### 7.5 Human-in-the-Loop as the Primary GxP Control

The most important GxP control for AI extraction is not technical — it is procedural: no AI-extracted data enters the batch record without explicit human authorization.

This is enforced architecturally:
- `ParsedData.state` starts as `PENDING` and cannot be read by downstream services until `VALIDATED`
- `validate_and_confirm()` requires a `validator_user` with the `audit:validate` permission
- The `validated_by_id` and `validated_at` fields are recorded in the audit trail with the validator's identity
- The validator can accept, modify, or reject the AI output; they are responsible for the accuracy of the confirmed data

This means that in any regulatory inspection, BioNexus can demonstrate that a named, authorized individual reviewed and approved each data extraction, making the AI system's non-determinism a secondary concern from a GxP perspective.

---

## 8. Cost Analysis

The following analysis uses the following assumptions:
- Primary provider: Claude 3.5 Sonnet
- Average instrument file: 5KB text (approximately 2,000 input tokens after prompt overhead, 800 output tokens)
- Total tokens per extraction: ~2,800 input tokens + ~800 output tokens
- Claude 3.5 Sonnet pricing: $3.00 / 1M input tokens, $15.00 / 1M output tokens

### 8.1 Per-File Cost Breakdown

| Token Type | Tokens per File | Cost per File |
|------------|-----------------|---------------|
| Input (prompt + file content) | ~2,000 | $0.006 |
| Output (structured JSON) | ~800 | $0.012 |
| **Total (Claude Sonnet)** | **~2,800** | **~$0.018** |

For GPT-4o comparison ($2.50/1M input, $10.00/1M output):
- Input: ~$0.005, Output: ~$0.008, Total: **~$0.013**

For Claude Haiku (low-cost option, $0.25/1M input, $1.25/1M output):
- Input: ~$0.0005, Output: ~$0.001, Total: **~$0.0015**

### 8.2 Monthly Cost at Different Scales

| Volume (files/month) | Claude Sonnet | OpenAI GPT-4o | Claude Haiku | Self-Hosted (GCP A100) |
|----------------------|---------------|---------------|--------------|------------------------|
| 100 | $1.80 | $1.30 | $0.15 | $2,200 (infra fixed) |
| 1,000 | $18.00 | $13.00 | $1.50 | $2,200 (infra fixed) |
| 5,000 | $90.00 | $65.00 | $7.50 | $2,200 (infra fixed) |
| 10,000 | $180.00 | $130.00 | $15.00 | $2,500 (with autoscaling) |
| 50,000 | $900.00 | $650.00 | $75.00 | $4,000–$6,000 |
| 100,000 | $1,800.00 | $1,300.00 | $150.00 | $6,000–$8,000 |

**Notes:**
- Self-hosted costs are dominated by infrastructure fixed costs; per-file costs decrease at high volume.
- The self-hosted break-even against Claude Sonnet is approximately 130,000 files/month.
- Claude Haiku is a viable option for simple, well-structured CSV files; Sonnet or Opus should be used for complex PDFs or ambiguous formats. A tiered routing strategy (simple files to Haiku, complex files to Sonnet) can reduce average per-file cost by 30–50%.
- These are variable costs only; they do not include engineering time for implementation or ongoing maintenance.

### 8.3 Cost Governance Recommendations

- Implement per-tenant monthly extraction budget limits to prevent unexpected cost spikes
- Add token count logging to `ParsedData` records for cost attribution and auditability
- Set provider-level spending alerts (Anthropic and OpenAI both support this)
- Evaluate Haiku/mini-tier models monthly against accuracy benchmarks; promote to primary if accuracy is acceptable

---

## 9. Fallback Strategy

### 9.1 Failure Modes and Responses

The extraction pipeline must handle three categories of failure without blocking lab operations:

| Failure Mode | Trigger | Response |
|--------------|---------|---------|
| Transient API error | HTTP 5xx, timeout, rate limit | Retry with exponential backoff (up to 3 attempts, max 90 seconds total) |
| Primary provider outage | Consecutive failures over 5 minutes | Automatic failover to secondary provider (OpenAI GPT-4o) |
| Both providers unavailable | Both primary and secondary fail | Queue extraction request; notify reviewer; offer manual entry path |
| Schema validation failure | AI output does not conform to schema | Return error to reviewer with details; file stays in `PENDING`; reviewer can trigger re-extraction or use manual entry |

### 9.2 Extraction Queue

When both AI providers are unavailable, extraction requests are placed in a persistent queue (Celery + Redis, as recommended in the `PARSING_ARCHITECTURE.md` production checklist):

```
Upload File → RawFile created → Queue extraction task
                                 └── On worker pickup: attempt extraction
                                     └── On provider recovery: process queue
```

Files in the queue are visible in the reviewer dashboard with status "Extraction Pending — Queued". Lab operations are not blocked: the file is captured and hashed immediately; only the AI extraction step is deferred.

### 9.3 Rule-Based Fallback for Known Formats

For instrument types with fixed, documented output formats (e.g., a specific Agilent HPLC model running a fixed software version), a deterministic rule-based parser is maintained as a permanent fallback:

- If the rule-based parser successfully produces schema-valid output: use it directly (bypassing AI, saving cost and latency)
- If the rule-based parser fails (format changed, unexpected layout): escalate to AI extraction
- The parser used (`ai_claude_sonnet`, `ai_openai_gpt4o`, `rule_based_v2`, etc.) is recorded in `extraction_model` for auditability

### 9.4 Manual Entry Path

When neither AI nor rule-based extraction is available, or when a reviewer rejects an extraction as unusable, the system must provide a manual data entry path:

- Reviewer opens the `RawFile` content in the UI (read-only viewer)
- Reviewer manually enters values into a form backed by the same Pydantic schema
- On submission, `ParsingService.parse_file()` is called with the manually entered dict and `model_name="manual_entry"`
- The human reviewer then immediately validates their own entry
- The audit trail records both the entry and the validation as separate events with the same user

This path is compliant because the data still passes schema validation and receives human authorization before entering the system.

---

## 10. Monitoring and Quality

### 10.1 Extraction Metrics to Capture

Every extraction event should record the following metrics to `ParsedData` or a separate metrics store:

| Metric | Storage | Purpose |
|--------|---------|---------|
| Extraction model name + version | `ParsedData.extraction_model` | Change control, provider audit |
| Extraction confidence score | `ParsedData.extraction_confidence` | Quality trending |
| Total input tokens used | `ParsedData.tokens_input` | Cost attribution |
| Total output tokens used | `ParsedData.tokens_output` | Cost attribution |
| Extraction latency (ms) | `ParsedData.extraction_latency_ms` | SLA monitoring |
| Schema validation result | `ParsedData` audit log | Accuracy tracking |
| Human review outcome | `ParsedData.state`, `validation_notes` | Accuracy ground truth |
| Correction rate | Derived: confirmed_json differs from parsed_json | Accuracy KPI |
| Rejection rate | Derived: state = REJECTED / total | Accuracy KPI |

### 10.2 Key Performance Indicators

| KPI | Target | Alert Threshold |
|-----|--------|-----------------|
| Field-level accuracy (auto-accepted + corrected / total validated) | >= 95% | < 90% triggers review |
| Correction rate (human modified AI output) | < 10% | > 20% triggers investigation |
| Rejection rate (reviewer rejected extraction) | < 3% | > 8% triggers investigation |
| Schema validation failure rate | < 2% | > 5% triggers model review |
| P95 extraction latency | < 30 seconds | > 60 seconds triggers alert |
| Provider availability | >= 99.5% | < 99% in any 30-day period |
| Monthly extraction cost | Within budget | > 120% of budget triggers alert |

### 10.3 Accuracy Drift Detection

Model providers update their models periodically; even under a pinned model version, subtle behavior changes can occur. Drift in extraction accuracy is detected through:

1. **Weekly accuracy report**: Automated report computing the correction rate and rejection rate for the past 7 days, segmented by instrument type. Published to the engineering and quality dashboard.
2. **Regression on golden test set**: Monthly re-execution of the OQ test suite against the production model to detect performance changes. Any drop of > 2% on any instrument type triggers a root cause investigation.
3. **Anomaly alerting**: If the correction rate for any single reviewer exceeds 3x their personal baseline in a 24-hour period, trigger a review (may indicate a format change in a specific instrument's output, or a model behavior change).

### 10.4 Quality Dashboard

The BioNexus admin dashboard should include an AI Extraction Quality panel displaying:

- Rolling 30-day accuracy, correction, and rejection rates per instrument type
- Provider availability and latency trends
- Monthly cost vs. budget
- Files currently in the extraction queue (if applicable)
- Recent schema validation failures with error details
- Change log for model version updates

---

## 11. AI Hallucination Prevention

### 11.1 Definition in This Context

In the BioNexus context, an "AI hallucination" is defined as any instance where the AI model produces output that:

1. Invents data fields not present in the source file
2. Fabricates values for fields that could not be inferred from the file content
3. Produces structurally invalid output (wrong data types, invalid enum values)
4. Creates plausible-looking but incorrect data (e.g., inventing a serial number)

### 11.2 Technical Safeguards (Defense in Depth)

Hallucination prevention is implemented as multiple independent layers:

**Layer 1: Pydantic Schema with `extra="forbid"`**
```python
model_config = {
    "extra": "forbid",  # Any field not in schema -> ValidationError
    "str_strip_whitespace": True,
    "validate_assignment": True,
}
```
This is the primary technical safeguard. If the AI invents a field not in the schema (e.g., `"warranty_expiry"`, `"patient_name"`, `"regulatory_status"`), the Pydantic validation raises a `ValidationError` immediately. The extraction is flagged as schema-invalid and does not proceed to human review until re-extracted.

**Layer 2: Enum Validation via Regex Patterns**
```python
equipment_type: str = Field(
    ...,
    pattern="^(centrifuge|spectrophotometer|incubator|microscope|pcr_machine|freezer|other)$",
)
```
The AI cannot invent a new equipment type. Any value not in the defined enum pattern fails validation. This prevents the AI from normalizing instrument names in unexpected ways (e.g., returning `"high_performance_liquid_chromatograph"` when the schema only accepts `"other"` for HPLC).

**Layer 3: Date and Timestamp Format Validation**
```python
@field_validator("purchase_date", "last_maintenance", mode="before")
def validate_dates(cls, v):
    datetime.fromisoformat(v)  # Raises ValueError for non-ISO dates
```
Prevents fabricated or malformatted dates from entering the system.

**Layer 4: AI Tool Use / Function Calling**
When invoking the Claude or OpenAI API, the request uses function calling (tool use) with a JSON Schema derived from the Pydantic models. This instructs the model at the API level to produce only schema-conformant output, reducing (but not eliminating) the likelihood of schema violations before the Pydantic gate.

**Layer 5: Structured Prompt Design**
The system prompt explicitly instructs the AI:
- Only extract fields that are explicitly present in the source file
- Do not infer, calculate, or estimate values not directly stated in the file
- Use `null` for fields that are not present; do not fabricate placeholder values
- Include any ambiguous or uncertain fields in `extraction_warnings` rather than the data records

**Layer 6: Human Review Gate**
Even if a hallucinated value passes all technical validation (e.g., the AI invents a valid-format serial number), the human reviewer comparing the extraction against the source file will detect the discrepancy. The human review gate is the final and definitive safeguard.

**Layer 7: Known-Value Validation (Future Enhancement)**
For instrument types where certain field values are known in advance (e.g., all HPLC systems registered in the `Equipment` table with known serial numbers), implement a post-extraction cross-reference check that flags any extracted value that does not match a known registered value. This will catch cases where the AI extracts a slightly wrong serial number with high confidence.

### 11.3 Hallucination Monitoring

- **Schema validation failure rate** is a proxy metric for hallucination attempts: a spike in validation failures may indicate the AI is generating more out-of-schema content, possibly due to a model behavior change.
- **Human correction rate** tracks instances where reviewers correct AI output; a sustained high correction rate for a specific field type (e.g., `equipment_type`) may indicate the AI is misclassifying consistently.
- **Hallucination incident log**: Any confirmed instance where a hallucinated value passed schema validation and was caught only in human review is logged as a quality event and triggers a review of the prompt and schema.

---

## 12. Vendor Assessment Under GAMP5

### 12.1 Classification of AI Providers as Suppliers

Under GAMP5 Section 7 (Supplier Assessment), regulated companies must assess suppliers of software that forms part of a validated computerized system. Anthropic and OpenAI are suppliers of a service component (the AI extraction API) integrated into BioNexus's validated system.

They are classified as **infrastructure software suppliers** (analogous to a cloud provider), not as software product suppliers, because:
- BioNexus does not receive source code or a deployable artifact
- The service is consumed via a standard API with documented behavior
- The supplier maintains the infrastructure and model; BioNexus configures usage

### 12.2 Supplier Assessment Criteria

| Assessment Area | Anthropic | OpenAI | Acceptable? |
|----------------|-----------|--------|-------------|
| Security certifications | SOC 2 Type II, ISO 27001 | SOC 2 Type II, ISO 27001 | Yes |
| GDPR DPA availability | Yes | Yes | Yes — must be executed |
| Penetration testing and security disclosure | Annual third-party pentest; HackerOne bug bounty | Annual third-party pentest; bug bounty program | Yes |
| API SLA | 99.5% uptime SLA (enterprise plans) | 99.9% uptime SLA | Yes |
| Data handling policy | Prompts not used for training; zero-retention available | ZDR available on enterprise | Yes — must configure |
| Documented incident response | Yes — security incident notification clauses in DPA | Yes | Yes |
| Financial stability | Well-capitalized; Series C+ | Well-capitalized; significant Microsoft investment | Acceptable — monitor |
| Model versioning and deprecation policy | Published model lifecycle; advance deprecation notice | Published lifecycle; advance notice | Yes |
| Change notification | Provider changelog; model deprecation notices | Provider changelog | Yes — subscribe to notifications |
| Regulatory compliance references | No specific FDA track record | No specific FDA track record | Acceptable given human-in-the-loop architecture |

### 12.3 Supplier Qualification Evidence Package

For each AI provider used in production, the following evidence must be maintained in the BioNexus supplier qualification file:

- Copy of executed DPA and SCCs
- Provider's most recent SOC 2 Type II report (obtained under NDA if required)
- Provider's security whitepaper
- Confirmation of zero data retention configuration
- Model version in use and pinned version string
- Annual review date for supplier re-assessment

### 12.4 Ongoing Supplier Monitoring

- Subscribe to provider status pages (status.anthropic.com, status.openai.com) for incident notifications
- Subscribe to provider developer newsletters for model deprecation and terms-of-service changes
- Annual supplier re-assessment review: confirm SOC 2 renewal, review any material changes to DPA or data handling policy
- Any material change to provider data handling terms triggers an immediate re-assessment and potential re-evaluation of the provider decision

---

## 13. Consequences

### 13.1 What This Decision Enables

- **Scalable instrument onboarding**: New instrument types can be supported by updating extraction prompts and schema definitions rather than building new code parsers. This is BioNexus's key competitive differentiator.
- **Reduced manual data entry burden**: Lab technicians spend time on review rather than transcription. Estimated 80% reduction in data entry time per file for supported instrument types.
- **Compliance-by-design audit trail**: Every extraction is attributed, timestamped, and linked to an immutable source file hash. This evidence package is suitable for 21 CFR Part 11 and EU Annex 11 inspection readiness.
- **Flexible provider architecture**: The `BaseExtractionClient` abstraction allows BioNexus to switch, add, or compare AI providers without changing the core parsing pipeline.
- **Cost predictability**: Per-file token costs are predictable and can be attributed to specific tenants and instrument types.

### 13.2 Risks That Remain

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AI provider increases pricing materially | Medium | Medium — affects unit economics | Hybrid architecture allows rapid provider switch; rule-based fallback for high-volume simple files |
| AI provider deprecates model version | High (certainty over 12–18 months) | Low — managed via change control | Model version pinning; change control process; regression test suite |
| AI provider suffers a significant data breach | Low | Medium — instrument data is non-PII but customer-confidential | DPA, ZDR, EU endpoints reduce impact; incident response plan required |
| Regulatory guidance explicitly prohibits external AI processing of GxP data | Low (no current indication) | High | Human-in-the-loop architecture provides strong defense; monitor FDA and EMA guidance actively |
| Extraction accuracy insufficient for complex instrument types | Medium | Medium | Accuracy testing in OQ; instrument-type-specific escalation to Opus/GPT-4o; human review catches residual errors |
| Provider terms-of-service change unfavorably | Medium | Low-Medium | Annual DPA review; hybrid architecture limits lock-in |
| Customer objects to cloud AI processing of their data | Low-Medium | Medium | Configurable provider architecture; rule-based or self-hosted option can be offered as a premium tier |

### 13.3 Architecture Changes Required

To implement this decision, the following changes are required to the current codebase:

1. Create `bionexus-platform/backend/core/ai_extraction/` package with:
   - `base_client.py`: `BaseExtractionClient` abstract interface
   - `claude_client.py`: Anthropic Claude implementation
   - `openai_client.py`: OpenAI GPT-4o implementation
   - `rule_based_client.py`: Deterministic template parser
   - `orchestrator.py`: Provider selection, retry, and failover logic

2. Extend `ParsedData` model with:
   - `tokens_input: IntegerField(null=True)` — for cost attribution
   - `tokens_output: IntegerField(null=True)` — for cost attribution
   - `extraction_latency_ms: IntegerField(null=True)` — for SLA monitoring

3. Add Django settings:
   - `EXTRACTION_PRIMARY_PROVIDER`
   - `EXTRACTION_FALLBACK_PROVIDER`
   - `EXTRACTION_TIMEOUT_SECONDS`
   - `EXTRACTION_MAX_RETRIES`
   - `ANTHROPIC_API_KEY` (from environment variable)
   - `OPENAI_API_KEY` (from environment variable)

4. Extend extraction queue:
   - Celery task: `tasks/extraction_task.py`
   - Queue configuration in `settings.py`

5. Update `ParsingService.parse_file()` to call `AIExtractionOrchestrator.extract()` internally rather than accepting pre-computed `ai_extracted_data` as a parameter (or provide both calling conventions for backward compatibility with tests).

6. Create `docs/AI_EXTRACTION_QUALITY_RUNBOOK.md` documenting:
   - How to run the regression test suite
   - How to process a model change control
   - How to investigate accuracy drift alerts
   - How to execute provider failover manually

---

## 14. Review Triggers

This ADR should be formally reviewed and updated when any of the following events occur:

| Trigger | Action |
|---------|--------|
| A major new model release from Anthropic or OpenAI (e.g., Claude 4, GPT-5) | Execute regression test suite against new model; update recommended primary provider if materially better; raise Change Control Record |
| Either provider changes pricing by more than 30% | Re-run cost analysis; evaluate whether provider hierarchy should change; evaluate rule-based fallback expansion |
| Either provider changes DPA terms materially | Legal review of new terms; re-assess GDPR compliance posture; consider provider switch if terms are unacceptable |
| FDA or EMA issues specific guidance on AI/ML in GxP data management | Assess guidance against current architecture; update validation strategy and compliance documentation accordingly |
| Monthly extraction volume exceeds 50,000 files | Re-evaluate self-hosted option (Option C) against cloud costs; assess whether rule-based fallback scope should be expanded |
| Extraction accuracy KPI falls below 90% on any instrument type for two consecutive weeks | Immediate investigation; potential model change or prompt engineering update; raise as a quality event |
| A significant security incident at either AI provider | Assess impact; review ZDR configuration; consider temporary provider suspension if data handling is in question |
| BioNexus acquires a customer with explicit on-premises or air-gapped requirements | Evaluate Option C (self-hosted) or a hybrid cloud/on-premises deployment; may require this ADR to be superseded |
| Annual review (no specific trigger) | Review all sections for continued accuracy; re-assess supplier qualification evidence; confirm DPAs are current |

---

**Document Prepared by:** BioNexus Engineering & Regulatory Team
**Review Partner:** GMP4U (Johannes Eberhardt) — CSV/Qualification Specialist
**Next Formal Review:** 2027-02-28 (annual) or upon trigger event, whichever is earlier

---

*This document is an Architecture Decision Record. It captures the context, options evaluated, rationale, and consequences of a significant architectural decision. It does not supersede the System Validation Plan (BNX-VAL-001) or the GxP Compliance Master Document (BNX-COMP-001), both of which must be updated to reflect the implemented architecture upon completion of implementation.*
