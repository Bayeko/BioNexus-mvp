# GCP Cloud Architecture & Deployment Guide
## BioNexus Platform — Infrastructure Reference

---

**Document ID:** BNX-INFRA-001
**Version:** 1.0
**Status:** Approved for Engineering Use
**Date:** 2026-02-28
**Prepared by:** BioNexus Engineering Team
**Classification:** Internal — Engineering Reference

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Compute: Cloud Run](#3-compute-cloud-run)
4. [Database: Cloud SQL (PostgreSQL)](#4-database-cloud-sql-postgresql)
5. [Storage: Cloud Storage (GCS)](#5-storage-cloud-storage-gcs)
6. [Networking](#6-networking)
7. [Identity & Access: IAM](#7-identity--access-iam)
8. [Secrets Management: Secret Manager](#8-secrets-management-secret-manager)
9. [CI/CD Pipeline](#9-cicd-pipeline)
10. [Monitoring & Observability](#10-monitoring--observability)
11. [Async Processing: Cloud Tasks / Pub/Sub](#11-async-processing-cloud-tasks--pubsub)
12. [CDN & Frontend: Firebase Hosting](#12-cdn--frontend-firebase-hosting)
13. [Data Residency & EU Compliance](#13-data-residency--eu-compliance)
14. [Disaster Recovery & Business Continuity](#14-disaster-recovery--business-continuity)
15. [Cost Estimation](#15-cost-estimation)
16. [Environment Strategy](#16-environment-strategy)
17. [GxP Compliance in Cloud](#17-gxp-compliance-in-cloud)

---

## 1. Overview

### 1.1 Why Google Cloud Platform

BioNexus runs on Google Cloud Platform (GCP) for the following reasons, each directly supporting regulatory and operational requirements:

**Regulatory Compliance Certifications**
GCP holds SOC 1/2/3, ISO 27001, ISO 27017, ISO 27018, HITRUST CSF, and FedRAMP High authorizations. These certifications are directly referenceable in BioNexus Computer System Validation (CSV) documentation and supplier assessments as required by GAMP5 Chapter 9 (Supplier Assessment).

**Data Residency Control**
GCP's `europe-west` region family (Frankfurt: `europe-west3`, Belgium: `europe-west1`) enables data residency choices that satisfy EU Annex 11 and GDPR data sovereignty requirements for EU-based pharma customers. Region pinning is enforced at the project and resource level.

**Managed Services Reduce Validation Scope**
Using GCP-managed services (Cloud SQL, Cloud Run, Secret Manager) reduces the surface area of infrastructure that BioNexus must validate under IQ/OQ/PQ, as these services operate on GCP's pre-qualified infrastructure. Operational Qualification effort is focused on configuration, not underlying platform mechanics.

**Serverless Scaling for SMB Economics**
Cloud Run's consumption-based billing model means early-stage costs (2 tenants) are near-zero during off-hours while scaling automatically during peak lab activity windows (08:00–18:00 local time). This matches the revenue profile of pharma SMB customers.

**BioNexus Box Compatibility**
GCP's global anycast load balancing and Cloud Armor WAF can terminate TLS at the edge closest to the BioNexus Box device in the lab, minimizing latency for instrument data uploads from European and North American sites.

### 1.2 High-Level Architecture Summary

```
[Lab Site]                          [GCP — europe-west3 (Frankfurt)]
─────────────────                   ──────────────────────────────────────────────
BioNexus Box ──HTTPS/TLS──► Cloud Load Balancer ──► Cloud Armor (WAF)
Lab Browser  ──HTTPS/TLS──►        │
                                   │
                          Firebase Hosting (React SPA)
                                   │
                          Cloud Run (Django API)
                                   │
                    ┌──────────────┼──────────────────┐
                    │              │                  │
             Cloud SQL        Cloud Storage     Secret Manager
           (PostgreSQL)     (GCS Buckets)    (Secrets/Keys)
                    │
           Cloud Tasks / Pub/Sub (async jobs)
                    │
           Cloud Monitoring + Cloud Logging
```

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LAB SITE                                            │
│                                                                             │
│  ┌──────────────┐    RS232/USB    ┌───────────────────────────────────┐    │
│  │ Lab Analyzer │ ─────────────► │         BioNexus Box              │    │
│  │  (HPLC, GC,  │                │  - Serial data capture             │    │
│  │   Balances)  │                │  - Local buffering (8h)            │    │
│  └──────────────┘                │  - HTTPS upload with mTLS          │    │
│                                  └──────────────────┬────────────────┘    │
│                                                     │ HTTPS/TLS 1.3       │
│  ┌──────────────────┐                               │                     │
│  │ Lab Browser/PC   │ ─────────────────────────────┤                     │
│  │ (React SPA)      │              HTTPS/TLS 1.3    │                     │
│  └──────────────────┘                               │                     │
└────────────────────────────────────────────────────┼────────────────────┘
                                                      │
                                    ┌─────────────────▼─────────────────────┐
                                    │     GCP — europe-west3 (Frankfurt)    │
                                    │                                        │
                        ┌───────────▼───────────┐                           │
                        │  Cloud Load Balancer   │  ◄── Global Anycast IP   │
                        │  (HTTPS + TLS Termination) │                      │
                        └───────────┬───────────┘                           │
                                    │                                        │
                        ┌───────────▼───────────┐                           │
                        │     Cloud Armor        │  WAF, DDoS, IP Allow-    │
                        │     (WAF + DDoS)       │  list for BioNexus Box   │
                        └────────┬──────┬────────┘                          │
                                 │      │                                    │
                     ┌───────────▼─┐  ┌─▼──────────────────────┐           │
                     │  Firebase   │  │     Cloud Run           │           │
                     │  Hosting    │  │  (Django REST API)      │           │
                     │  (React SPA)│  │  - Min instances: 1     │           │
                     └─────────────┘  │  - Max instances: 20    │           │
                                      │  - Concurrency: 80      │           │
                                      │  - CPU: 2 vCPU          │           │
                                      │  - Memory: 2Gi          │           │
                                      └──────┬──────────────────┘           │
                                             │                               │
              ┌──────────────────────────────┼───────────────────────┐      │
              │                              │                        │      │
  ┌───────────▼──────────┐  ┌───────────────▼───────┐  ┌────────────▼───┐  │
  │    Cloud SQL          │  │  Cloud Storage (GCS)  │  │ Secret Manager │  │
  │  PostgreSQL 15        │  │                       │  │                │  │
  │  - Primary (HA)       │  │  bionexus-raw-data    │  │ DJANGO_SECRET  │  │
  │  - Read Replica       │  │  bionexus-audit-export│  │ DB_PASSWORD    │  │
  │  - Automated backups  │  │  bionexus-backups     │  │ JWT_SIGNING_KEY│  │
  │  - PITR 7 days        │  │  - Versioning ON      │  │ API_KEYS       │  │
  │  - Private IP only    │  │  - Lifecycle rules    │  └────────────────┘  │
  └──────────────────────┘  └───────────────────────┘                      │
              │                                                              │
  ┌───────────▼──────────────────────────────────────────────┐              │
  │                  Cloud Tasks / Pub/Sub                    │              │
  │  - AI parsing job queue                                   │              │
  │  - BioNexus Box ingestion queue                           │              │
  │  - Retry with exponential backoff                         │              │
  └───────────────────────────────────────────────────────────┘             │
              │                                                              │
  ┌───────────▼──────────────────────────────────────────────┐              │
  │           Cloud Monitoring + Cloud Logging                │              │
  │  - Uptime checks (API health endpoints)                   │              │
  │  - Custom metrics (audit trail integrity, API latency)    │              │
  │  - Error Reporting (Django exceptions)                    │              │
  │  - Alerting (PagerDuty / email)                           │              │
  └──────────────────────────────────────────────────────────┘              │
                                                                             │
  ┌──────────────────────────────────────────────────────────┐              │
  │       VPC: bionexus-vpc (10.0.0.0/16)                    │              │
  │  - Subnet: private-backend (10.0.1.0/24)                 │              │
  │  - Subnet: private-db (10.0.2.0/24)                      │              │
  │  - Cloud NAT (outbound-only for Cloud Run)               │              │
  │  - No public IPs on Cloud SQL or internal services        │              │
  └──────────────────────────────────────────────────────────┘              │
                                                                             │
  ┌──────────────────────────────────────────────────────────┐              │
  │   Disaster Recovery: europe-west4 (Netherlands)          │              │
  │  - Cloud SQL cross-region replica (RPO ≤ 1h)             │              │
  │  - GCS dual-region bucket (eur4)                         │              │
  │  - Cloud Run: deployable in <15 min                      │              │
  └──────────────────────────────────────────────────────────┘              │
                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                    CI/CD PIPELINE                                         │
│                                                                           │
│  GitHub (main branch)                                                    │
│       │                                                                  │
│       ▼ push / PR merge                                                  │
│  GitHub Actions ──► Cloud Build ──► Artifact Registry (Docker images)   │
│       │                    │                                              │
│       │           Run Django tests                                       │
│       │           Run migrate --check                                    │
│       │                    │                                              │
│       ▼                    ▼                                              │
│  Deploy to staging ──► Smoke tests ──► Deploy to production             │
│  (bionexus-staging)                   (bionexus-prod)                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Compute: Cloud Run

### 3.1 Why Cloud Run

Cloud Run (managed) provides serverless container execution with no cluster management overhead. Django apps run as stateless containers, which aligns with the 12-factor app model. Cloud Run handles TLS termination, autoscaling, and rolling deployments natively. It integrates with Workload Identity Federation to eliminate service account key files.

### 3.2 Container Configuration

The Django backend is packaged as a Docker image and pushed to Artifact Registry. The base image is `python:3.12-slim`.

**Dockerfile (production)**

```dockerfile
FROM python:3.12-slim

# Create non-root user for GxP principle of least privilege
RUN groupadd -r bionexus && useradd -r -g bionexus bionexus

WORKDIR /app

# Install system dependencies (psycopg2 needs libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY --chown=bionexus:bionexus . .

# Collect static files
RUN python manage.py collectstatic --noinput

USER bionexus

# Cloud Run expects the app to listen on PORT (default 8080)
CMD exec gunicorn core.wsgi:application \
    --bind "0.0.0.0:${PORT:-8080}" \
    --workers 2 \
    --threads 4 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

### 3.3 Cloud Run Service Configuration

```yaml
# cloud-run-service.yaml (used by gcloud run services replace)
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: bionexus-api
  namespace: bionexus-prod
  annotations:
    run.googleapis.com/ingress: internal-and-cloud-load-balancing
spec:
  template:
    metadata:
      annotations:
        # Scaling configuration
        autoscaling.knative.dev/minScale: "1"        # Prevent cold starts in production
        autoscaling.knative.dev/maxScale: "20"
        # Cloud SQL connection via Cloud SQL Auth Proxy (Unix socket)
        run.googleapis.com/cloudsql-instances: "bionexus-prod:europe-west3:bionexus-db-prod"
        # VPC connector for private Cloud SQL access
        run.googleapis.com/vpc-access-connector: "bionexus-connector"
        run.googleapis.com/vpc-access-egress: "private-ranges-only"
        # Startup probe — wait for Django to be ready
        run.googleapis.com/startup-cpu-boost: "true"
    spec:
      containerConcurrency: 80         # Gunicorn workers handle this via threads
      timeoutSeconds: 60
      serviceAccountName: bionexus-api-sa@bionexus-prod.iam.gserviceaccount.com
      containers:
        - image: europe-west3-docker.pkg.dev/bionexus-prod/bionexus/api:latest
          ports:
            - name: http1
              containerPort: 8080
          resources:
            limits:
              cpu: "2"
              memory: "2Gi"
          env:
            - name: DJANGO_SETTINGS_MODULE
              value: core.settings.production
            - name: GOOGLE_CLOUD_PROJECT
              value: bionexus-prod
          # Secrets mounted from Secret Manager
          envFrom:
            - secretRef:
                name: bionexus-django-secrets
          startupProbe:
            httpGet:
              path: /api/health/
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 12       # 60s total startup window
          livenessProbe:
            httpGet:
              path: /api/health/
              port: 8080
            periodSeconds: 30
```

### 3.4 Cold Start Mitigation

Cold start latency for Django containers is typically 2–5 seconds due to module imports. The following measures minimize impact:

| Technique | Configuration | Effect |
|-----------|---------------|--------|
| **Min instances = 1** | `autoscaling.knative.dev/minScale: "1"` | Zero cold starts during business hours |
| **Startup CPU boost** | `run.googleapis.com/startup-cpu-boost: "true"` | Allocates 2x CPU during container init |
| **Slim base image** | `python:3.12-slim` | Reduces image pull time by ~60% vs full image |
| **Layer caching** | Requirements layer before source copy | Dockerfile layer cache exploited in CI |
| **Gunicorn preloading** | `--preload` flag | Workers share memory after fork |

For staging, `minScale: "0"` is acceptable to reduce cost. Cold starts in staging are tolerable.

### 3.5 Terraform: Cloud Run Service

```hcl
# terraform/modules/cloud_run/main.tf

resource "google_cloud_run_service" "bionexus_api" {
  name     = "bionexus-api"
  location = var.region  # "europe-west3"

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"          = var.min_instances
        "autoscaling.knative.dev/maxScale"          = "20"
        "run.googleapis.com/cloudsql-instances"     = google_sql_database_instance.main.connection_name
        "run.googleapis.com/vpc-access-connector"   = google_vpc_access_connector.connector.name
        "run.googleapis.com/vpc-access-egress"      = "private-ranges-only"
        "run.googleapis.com/startup-cpu-boost"      = "true"
      }
    }

    spec {
      container_concurrency = 80
      timeout_seconds       = 60
      service_account_name  = google_service_account.api_sa.email

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/bionexus/api:${var.image_tag}"

        resources {
          limits = {
            cpu    = "2000m"
            memory = "2Gi"
          }
        }

        env {
          name  = "DJANGO_SETTINGS_MODULE"
          value = "core.settings.production"
        }

        dynamic "env" {
          for_each = var.secret_env_vars
          content {
            name = env.value.name
            value_from {
              secret_key_ref {
                name = env.value.secret_name
                key  = "latest"
              }
            }
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true
}
```

---

## 4. Database: Cloud SQL (PostgreSQL)

### 4.1 Instance Sizing

**Production (bionexus-prod)**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Engine | PostgreSQL 15 | Matches local Docker development environment |
| Tier | `db-custom-2-7680` (2 vCPU, 7.5 GB RAM) | Handles 30 concurrent tenants with connection pooling |
| Storage | 100 GB SSD, auto-grow enabled | GxP audit tables grow continuously; auto-grow prevents downtime |
| Storage max | 500 GB | Upper bound for cost control |
| Region | `europe-west3` (Frankfurt) | EU data residency |
| Availability | Regional (HA with standby) | Automatic failover < 60s |
| Backup retention | 7 days | PITR coverage; matches DR RPO target |
| Maintenance window | Sunday 02:00–04:00 UTC | Minimizes impact on EU lab hours |

**Staging (bionexus-staging)**

| Parameter | Value |
|-----------|-------|
| Tier | `db-custom-1-3840` (1 vCPU, 3.75 GB RAM) |
| Storage | 50 GB SSD |
| Availability | Zonal (no HA — cost optimization) |
| Backup retention | 3 days |

### 4.2 High Availability Configuration

Cloud SQL HA uses a regional persistent disk with synchronous replication to a standby instance in a different zone within `europe-west3`. Failover is automatic and transparent to the application.

```hcl
# terraform/modules/cloud_sql/main.tf

resource "google_sql_database_instance" "main" {
  name             = "bionexus-db-${var.environment}"
  region           = "europe-west3"
  database_version = "POSTGRES_15"

  deletion_protection = true  # Prevent accidental deletion

  settings {
    tier              = var.db_tier  # "db-custom-2-7680" for prod
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"   # UTC — off-peak for Europe
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7   # Sunday
      hour         = 2   # 02:00 UTC
      update_track = "stable"
    }

    ip_configuration {
      ipv4_enabled    = false      # No public IP — private VPC only
      private_network = google_compute_network.vpc.id
      require_ssl     = true
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }
    database_flags {
      name  = "log_connections"
      value = "on"
    }
    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
    database_flags {
      name  = "log_lock_waits"
      value = "on"
    }
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"   # Log queries taking > 1s
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false   # GDPR: do not log client IPs
    }

    disk_size             = 100
    disk_type             = "PD_SSD"
    disk_autoresize       = true
    disk_autoresize_limit = 500

    user_labels = {
      environment = var.environment
      service     = "bionexus-database"
      compliance  = "gxp"
    }
  }
}

# Cross-region read replica for DR
resource "google_sql_database_instance" "replica" {
  count                = var.environment == "prod" ? 1 : 0
  name                 = "bionexus-db-prod-replica"
  region               = "europe-west4"   # Netherlands (DR region)
  database_version     = "POSTGRES_15"
  master_instance_name = google_sql_database_instance.main.name

  replica_configuration {
    failover_target = false   # Manual promotion only — protects audit trail
  }

  settings {
    tier              = "db-custom-2-7680"
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc_dr.id
      require_ssl     = true
    }
  }
}
```

### 4.3 Connection Pooling: Cloud SQL Auth Proxy

The Cloud SQL Auth Proxy handles IAM-based authentication and encrypted connections without embedding database credentials in the application. Cloud Run integrates the proxy natively via the `run.googleapis.com/cloudsql-instances` annotation, which mounts a Unix socket at `/cloudsql/<connection-name>/.s.PGSQL.5432`.

**Django database settings (production)**

```python
# core/settings/production.py
import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        # Cloud Run: use Unix socket via Cloud SQL Auth Proxy
        "HOST": f"/cloudsql/{os.environ['CLOUD_SQL_CONNECTION_NAME']}",
        "PORT": "",
        # Connection pool settings
        "CONN_MAX_AGE": 60,         # Reuse connections for 60 seconds
        "CONN_HEALTH_CHECKS": True,  # Validate connection before reuse
        "OPTIONS": {
            "sslmode": "disable",   # Auth Proxy handles encryption
            "connect_timeout": 5,
            "options": "-c statement_timeout=30000",  # 30s query timeout
        },
    }
}
```

For external access (e.g., from local development or Cloud Build migration steps), the proxy is invoked as:

```bash
# Local development — download proxy binary
cloud-sql-proxy \
  --credentials-file=service-account-key.json \
  --port=5432 \
  bionexus-prod:europe-west3:bionexus-db-prod
```

**Django migrations in CI/CD**

Migrations run as a Cloud Build step using the proxy sidecar pattern:

```yaml
# In Cloud Build config — see Section 9
- name: gcr.io/cloud-sql-connectors/cloud-sql-proxy:latest
  args:
    - "--port=5432"
    - "--credentials-file=/root/.config/gcloud/application_default_credentials.json"
    - "bionexus-prod:europe-west3:bionexus-db-prod"
  waitFor: ["-"]   # Start immediately in background
  id: "cloud-sql-proxy"

- name: "europe-west3-docker.pkg.dev/bionexus-prod/bionexus/api:$SHORT_SHA"
  entrypoint: python
  args: ["manage.py", "migrate", "--noinput"]
  env:
    - "DATABASE_URL=postgres://$_DB_USER:$_DB_PASS@localhost:5432/$_DB_NAME"
  waitFor: ["cloud-sql-proxy"]
  id: "run-migrations"
```

### 4.4 GxP Considerations for Cloud SQL

- **Audit log flags**: `log_connections`, `log_disconnections`, and `log_lock_waits` are enabled. These PostgreSQL logs feed into Cloud Logging and are retained for 365 days.
- **Deletion protection**: `deletion_protection = true` in Terraform prevents accidental database deletion. Requires Terraform state modification to remove.
- **No direct public access**: Cloud SQL has no public IP. All connections go through the Auth Proxy or VPC peering.
- **SSL enforcement**: `ssl_mode = "ENCRYPTED_ONLY"` — plaintext connections are rejected at the Cloud SQL level.
- **Immutable audit tables**: PostgreSQL row-level security (RLS) is applied to the `audit_log` table so that no application user can `UPDATE` or `DELETE` audit records, even if application code is compromised.

```sql
-- Applied during initial schema setup (run once by DBA)
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Policy: only INSERT is permitted via application role
CREATE POLICY audit_insert_only ON audit_log
    FOR INSERT
    TO bionexus_app_user
    WITH CHECK (true);

-- No UPDATE or DELETE policies are defined — they are implicitly denied
```

---

## 5. Storage: Cloud Storage (GCS)

### 5.1 Bucket Structure

BioNexus uses three GCS buckets with distinct purposes, retention policies, and access controls:

| Bucket Name | Purpose | Storage Class | Region |
|-------------|---------|--------------|--------|
| `bionexus-raw-data-prod` | Raw instrument data files uploaded by BioNexus Box | STANDARD | `europe-west3` |
| `bionexus-audit-exports-prod` | Certified audit export JSON/PDF files | NEARLINE | `europe-west3` |
| `bionexus-backups-prod` | Database dumps, Terraform state | COLDLINE | dual-region `eur4` |

### 5.2 Bucket Configuration (Terraform)

```hcl
# terraform/modules/storage/main.tf

resource "google_storage_bucket" "raw_data" {
  name          = "bionexus-raw-data-${var.environment}"
  location      = "europe-west3"
  storage_class = "STANDARD"

  # GxP: versioning is mandatory — preserves all versions of instrument data files
  versioning {
    enabled = true
  }

  # Prevent public access at bucket level
  uniform_bucket_level_access = true

  # Object lifecycle — keep current version indefinitely, expire non-current after 90 days
  lifecycle_rule {
    condition {
      age                = 90
      with_state         = "NONCURRENT"
    }
    action {
      type = "Delete"
    }
  }

  # Move objects older than 365 days to cheaper storage
  lifecycle_rule {
    condition {
      age        = 365
      with_state = "LIVE"
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age        = 1825   # 5 years
      with_state = "LIVE"
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  # Retention policy: GxP requires minimum 5 years for QC data
  retention_policy {
    retention_period = 157680000   # 5 years in seconds
    is_locked        = false       # Lock after validation is complete
  }

  labels = {
    environment = var.environment
    compliance  = "gxp"
    data-type   = "raw-instrument-data"
  }
}

resource "google_storage_bucket" "audit_exports" {
  name          = "bionexus-audit-exports-${var.environment}"
  location      = "europe-west3"
  storage_class = "NEARLINE"

  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true

  # Audit exports are write-once by design
  retention_policy {
    retention_period = 220752000   # 7 years in seconds (EU pharma standard)
  }

  labels = {
    environment = var.environment
    compliance  = "gxp"
    data-type   = "audit-export"
  }
}

resource "google_storage_bucket" "backups" {
  name          = "bionexus-backups-${var.environment}"
  location      = "eur4"          # Dual-region: europe-west3 + europe-west4
  storage_class = "COLDLINE"

  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }
}
```

### 5.3 GxP Compliance Features for GCS

**Object Versioning**: Every file written to `bionexus-raw-data-prod` is versioned. If an object is overwritten, the previous version is retained. This satisfies EU Annex 11 §7.1 (data should be protected against accidental deletion or modification).

**Retention Policies**: The `retention_policy` block prevents objects from being deleted before the retention period expires, even by bucket owners. After the validation phase, `is_locked = true` should be applied via `gcloud storage buckets update --lock-retention-policy` to make the policy irrevocable. This is a WORM (Write Once, Read Many) guarantee enforced at the storage infrastructure level.

**Signed URLs for BioNexus Box Uploads**: The BioNexus Box generates signed upload URLs via the Django API rather than holding long-term GCS credentials. The Django service account generates a signed URL with a 15-minute expiry:

```python
# modules/instruments/services/upload_service.py
from google.cloud import storage
from datetime import timedelta
import datetime
import os

def generate_upload_url(
    instrument_id: str,
    tenant_id: int,
    filename: str,
) -> str:
    """
    Generate a signed GCS upload URL for BioNexus Box data submission.
    The signed URL is scoped to a tenant-specific path and expires in 15 minutes.
    """
    client = storage.Client()
    bucket = client.bucket(os.environ["GCS_RAW_DATA_BUCKET"])

    # Tenant-scoped path enforces data isolation at the storage layer
    object_name = f"tenants/{tenant_id}/instruments/{instrument_id}/{filename}"
    blob = bucket.blob(object_name)

    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=15),
        method="PUT",
        content_type="application/octet-stream",
    )
    return url
```

---

## 6. Networking

### 6.1 VPC Design

BioNexus uses a custom VPC with private subnets. No GCP resources have public IP addresses except the Global Load Balancer frontend.

```hcl
# terraform/modules/networking/vpc.tf

resource "google_compute_network" "vpc" {
  name                    = "bionexus-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "private_backend" {
  name          = "private-backend"
  ip_cidr_range = "10.0.1.0/24"
  region        = "europe-west3"
  network       = google_compute_network.vpc.id

  # Enable Private Google Access so Cloud Run can reach GCP APIs without NAT
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "private_db" {
  name          = "private-db"
  ip_cidr_range = "10.0.2.0/24"
  region        = "europe-west3"
  network       = google_compute_network.vpc.id

  private_ip_google_access = true
}

# Cloud NAT — allows Cloud Run and Cloud SQL outbound internet access
# (for package downloads in CI; not needed in runtime for production)
resource "google_compute_router" "router" {
  name    = "bionexus-router"
  region  = "europe-west3"
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "bionexus-nat"
  router                             = google_compute_router.router.name
  region                             = "europe-west3"
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# VPC Connector — required for Cloud Run to access VPC resources (Cloud SQL)
resource "google_vpc_access_connector" "connector" {
  name          = "bionexus-connector"
  region        = "europe-west3"
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc.name
  machine_type  = "e2-micro"
  min_instances = 2
  max_instances = 10
}
```

### 6.2 Load Balancer Configuration

BioNexus uses an HTTPS Global Load Balancer with a single anycast IP, routing traffic to Cloud Run (API) and Firebase Hosting (React SPA).

```hcl
# terraform/modules/networking/load_balancer.tf

# Reserve a static global IP
resource "google_compute_global_address" "lb_ip" {
  name = "bionexus-lb-ip"
}

# Managed SSL certificate — automatically renewed
resource "google_compute_managed_ssl_certificate" "cert" {
  name = "bionexus-ssl-cert"
  managed {
    domains = [
      "api.bionexus.io",
      "app.bionexus.io",
    ]
  }
}

# Backend service pointing to Cloud Run
resource "google_compute_backend_service" "api_backend" {
  name                  = "bionexus-api-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  timeout_sec           = 60
  security_policy       = google_compute_security_policy.armor.id

  backend {
    group = google_compute_region_network_endpoint_group.cloud_run_neg.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0   # Log 100% of requests for compliance
  }
}

# Network Endpoint Group for Cloud Run
resource "google_compute_region_network_endpoint_group" "cloud_run_neg" {
  name                  = "bionexus-api-neg"
  network_endpoint_type = "SERVERLESS"
  region                = "europe-west3"

  cloud_run {
    service = google_cloud_run_service.bionexus_api.name
  }
}

# HTTPS Proxy
resource "google_compute_target_https_proxy" "https_proxy" {
  name             = "bionexus-https-proxy"
  url_map          = google_compute_url_map.url_map.id
  ssl_certificates = [google_compute_managed_ssl_certificate.cert.id]
  ssl_policy       = google_compute_ssl_policy.ssl_policy.id
}

# TLS policy: TLS 1.2+ only, modern cipher suites
resource "google_compute_ssl_policy" "ssl_policy" {
  name            = "bionexus-ssl-policy"
  profile         = "MODERN"
  min_tls_version = "TLS_1_2"
}

# HTTP → HTTPS redirect
resource "google_compute_url_map" "http_redirect" {
  name = "bionexus-http-redirect"
  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}
```

### 6.3 Cloud Armor (WAF)

Cloud Armor protects the API from common web attacks and enforces IP allowlisting for BioNexus Box devices during the registration phase.

```hcl
# terraform/modules/networking/cloud_armor.tf

resource "google_compute_security_policy" "armor" {
  name        = "bionexus-waf-policy"
  description = "WAF policy for BioNexus API — GxP environment"

  # Rule 1000: OWASP Top 10 — SQL injection
  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('sqli-v33-stable', {'sensitivity': 2})"
      }
    }
    description = "Block SQL injection attempts"
  }

  # Rule 1001: OWASP Top 10 — XSS
  rule {
    action   = "deny(403)"
    priority = 1001
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('xss-v33-stable', {'sensitivity': 2})"
      }
    }
    description = "Block XSS attempts"
  }

  # Rule 1002: Rate limiting — 100 req/min per IP for API endpoints
  rule {
    action   = "throttle"
    priority = 1002
    match {
      expr {
        expression = "request.path.matches('/api/') && !request.path.matches('/api/health/')"
      }
    }
    rate_limit_options {
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
    }
    description = "Rate limit API endpoints"
  }

  # Rule 1003: BioNexus Box IP allowlist for /api/ingestion/ endpoint
  # Update with actual registered device IP ranges
  rule {
    action   = "allow"
    priority = 900
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = var.bionexus_box_ip_ranges   # e.g., ["203.0.113.0/24"]
      }
    }
    description = "Allowlist BioNexus Box devices for ingestion endpoint"
  }

  # Default: allow all other traffic (WAF rules above will deny bad requests)
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }
}
```

### 6.4 Custom Domain Setup

```bash
# DNS configuration (performed in your DNS registrar / Cloud DNS)
# After Terraform applies and global IP is assigned:

# Create Cloud DNS zone
gcloud dns managed-zones create bionexus-zone \
  --dns-name="bionexus.io." \
  --description="BioNexus production DNS zone" \
  --dnssec-state=on

# Add A record for API
gcloud dns record-sets transaction start --zone=bionexus-zone
gcloud dns record-sets transaction add \
  $(gcloud compute addresses describe bionexus-lb-ip --global --format='value(address)') \
  --name="api.bionexus.io." \
  --ttl=300 \
  --type=A \
  --zone=bionexus-zone
gcloud dns record-sets transaction execute --zone=bionexus-zone

# DNSSEC is enabled — nameserver records are returned with cryptographic signatures
# Update registrar NS records to point to Cloud DNS nameservers
```

---

## 7. Identity & Access: IAM

### 7.1 Service Account Architecture

BioNexus follows the principle of least privilege. Each GCP service has a dedicated service account with only the permissions it requires.

| Service Account | Used By | Roles |
|----------------|---------|-------|
| `bionexus-api-sa` | Cloud Run (Django API) | `roles/cloudsql.client`, `roles/secretmanager.secretAccessor`, `roles/storage.objectCreator` (raw-data bucket), `roles/cloudtasks.enqueuer`, `roles/logging.logWriter`, `roles/monitoring.metricWriter` |
| `bionexus-cloudbuild-sa` | Cloud Build (CI/CD) | `roles/run.developer`, `roles/artifactregistry.writer`, `roles/cloudsql.client`, `roles/secretmanager.secretAccessor` |
| `bionexus-migration-sa` | Migration Cloud Build step | `roles/cloudsql.client`, `roles/secretmanager.secretAccessor` |
| `bionexus-audit-reader-sa` | Read-only audit access for compliance team | `roles/cloudsql.viewer`, `roles/storage.objectViewer` (audit-exports bucket) |
| `bionexus-backup-sa` | Automated backup scripts | `roles/cloudsql.admin` (limited to backup operations), `roles/storage.objectAdmin` (backups bucket only) |

### 7.2 Workload Identity for Cloud Run

Workload Identity eliminates the need for service account key files. Cloud Run containers automatically obtain short-lived credentials bound to `bionexus-api-sa`.

```hcl
# terraform/modules/iam/workload_identity.tf

resource "google_service_account" "api_sa" {
  account_id   = "bionexus-api-sa"
  display_name = "BioNexus API Service Account"
  description  = "Service account for Cloud Run Django API"
}

# Grant Cloud Run the ability to act as this service account
resource "google_cloud_run_service_iam_member" "run_sa_binding" {
  location = var.region
  service  = google_cloud_run_service.bionexus_api.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.api_sa.email}"
}

# Grant the API service account access to Cloud SQL
resource "google_project_iam_member" "api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

# Grant access to Secret Manager secrets (scoped to specific secrets, not project-wide)
resource "google_secret_manager_secret_iam_member" "api_django_secret" {
  secret_id = google_secret_manager_secret.django_secret_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_sa.email}"
}

# Grant write access to raw-data bucket ONLY
resource "google_storage_bucket_iam_member" "api_raw_data_writer" {
  bucket = google_storage_bucket.raw_data.name
  role   = "roles/storage.objectCreator"   # Create only — cannot delete or overwrite
  member = "serviceAccount:${google_service_account.api_sa.email}"
}
```

### 7.3 IAM Best Practices Applied

- **No owner/editor roles**: No service account holds `roles/owner` or `roles/editor`. All bindings use predefined or custom roles.
- **No service account keys**: All authentication uses Workload Identity or ADC (Application Default Credentials) in Cloud Build.
- **Resource-scoped bindings**: IAM bindings are applied at the resource level (e.g., specific bucket, specific secret) rather than the project level wherever possible.
- **IAM Conditions**: Time-bound access for break-glass scenarios.

```hcl
# Break-glass: temporary elevated access with time condition
resource "google_project_iam_member" "break_glass" {
  project = var.project_id
  role    = "roles/cloudsql.admin"
  member  = "user:oncall-engineer@bionexus.io"

  condition {
    title       = "temporary-access"
    description = "Break-glass access valid for 4 hours"
    expression  = "request.time < timestamp('2026-03-01T06:00:00Z')"
  }
}
```

---

## 8. Secrets Management: Secret Manager

### 8.1 Secrets Inventory

All application secrets are stored in GCP Secret Manager. No secrets appear in source code, environment files checked into git, or Docker image layers.

| Secret Name | Description | Rotation Schedule |
|-------------|-------------|------------------|
| `bionexus-django-secret-key` | Django `SECRET_KEY` — used for JWT signing and session security | Annually or on suspected compromise |
| `bionexus-db-password` | PostgreSQL application user password | Quarterly |
| `bionexus-db-user` | PostgreSQL application username | With password rotation |
| `bionexus-jwt-signing-key` | Additional JWT signing key (if using RS256 in future) | Annually |
| `bionexus-gcs-hmac-key` | HMAC key for signed URL generation | Annually |
| `bionexus-sendgrid-api-key` | Email delivery for alerts/reports | On provider recommendation |
| `bionexus-box-device-psk` | Pre-shared key for BioNexus Box initial registration | Per device, rotated on RMA |

### 8.2 Secret Creation and Access

```bash
# Create secrets (one-time setup, performed by infrastructure admin)
echo -n "$(python -c 'import secrets; print(secrets.token_urlsafe(64))')" | \
  gcloud secrets create bionexus-django-secret-key \
    --data-file=- \
    --replication-policy=user-managed \
    --locations=europe-west3 \
    --labels=environment=prod,service=bionexus-api,compliance=gxp

# Add a new version (rotation)
echo -n "new-secret-value" | \
  gcloud secrets versions add bionexus-django-secret-key --data-file=-

# Disable old version after rotation (keep for 30 days for audit)
gcloud secrets versions disable 1 --secret=bionexus-django-secret-key
```

### 8.3 Django Integration

```python
# core/settings/production.py
# Secrets are injected as environment variables by Cloud Run at container startup.
# Cloud Run reads from Secret Manager using the service account's IAM binding.
# No explicit Python Secret Manager SDK calls are needed for app secrets.

import os

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]           # From Secret Manager
DATABASES = {
    "default": {
        "PASSWORD": os.environ["DB_PASSWORD"],         # From Secret Manager
    }
}
```

**Secret Manager → Cloud Run injection (Terraform)**

```hcl
# terraform/modules/cloud_run/secrets.tf

resource "google_secret_manager_secret" "django_secret_key" {
  secret_id = "bionexus-django-secret-key"
  replication {
    user_managed {
      replicas {
        location = "europe-west3"
      }
    }
  }
  labels = {
    environment = var.environment
    compliance  = "gxp"
  }
}

# Reference in Cloud Run service (in cloud_run/main.tf env block)
# env {
#   name = "DJANGO_SECRET_KEY"
#   value_from {
#     secret_key_ref {
#       name = google_secret_manager_secret.django_secret_key.secret_id
#       key  = "latest"
#     }
#   }
# }
```

### 8.4 Audit Logging for Secret Access

Secret Manager access is automatically logged to Cloud Audit Logs. Enable data access audit logs to capture every `AccessSecretVersion` call:

```bash
# Enable data access audit logging for Secret Manager
gcloud projects get-iam-policy bionexus-prod --format=json > policy.json
# Add auditLogConfig for secretmanager.googleapis.com with DATA_READ log type
# Then:
gcloud projects set-iam-policy bionexus-prod policy.json
```

---

## 9. CI/CD Pipeline

### 9.1 Pipeline Overview

```
Developer pushes to GitHub
        │
        ▼
GitHub Actions (trigger)
        │
        ├── Run unit tests (pytest)
        ├── Run linter (ruff / flake8)
        ├── Run type checker (mypy)
        │
        ▼
Cloud Build (build & deploy)
        │
        ├── docker build → push to Artifact Registry
        ├── Run database migrations (via Cloud SQL Auth Proxy)
        ├── Deploy to Cloud Run (staging)
        │
        ▼
GitHub Actions (smoke tests against staging)
        │
        ├── /api/health/ → 200
        ├── /api/auth/login → 200
        ├── Audit trail integrity check
        │
        ▼
Manual approval gate (production)
        │
        ▼
Cloud Build (production deploy)
        │
        ├── Deploy to Cloud Run (production) — traffic split 0% → 100%
        └── Run post-deploy health check
```

### 9.2 GitHub Actions Workflow

```yaml
# .github/workflows/ci-cd.yml

name: BioNexus CI/CD

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main]

env:
  PROJECT_ID: bionexus-prod
  REGION: europe-west3
  ARTIFACT_REGISTRY: europe-west3-docker.pkg.dev/bionexus-prod/bionexus

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: bionexus-platform/backend

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: bionexus_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run linter
        run: |
          pip install ruff
          ruff check .

      - name: Run type checker
        run: |
          pip install mypy django-stubs
          mypy . --ignore-missing-imports

      - name: Run Django tests
        env:
          DATABASE_URL: postgres://postgres:test_password@localhost:5432/bionexus_test
          DJANGO_SECRET_KEY: ci-test-secret-key-not-for-production
          DJANGO_DEBUG: "false"
        run: python manage.py test --verbosity=2

      - name: Check for pending migrations
        env:
          DATABASE_URL: postgres://postgres:test_password@localhost:5432/bionexus_test
          DJANGO_SECRET_KEY: ci-test-secret-key-not-for-production
        run: python manage.py migrate --check

  build-and-deploy-staging:
    name: Build & Deploy (Staging)
    needs: test
    if: github.ref == 'refs/heads/staging'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write   # Required for Workload Identity Federation

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: bionexus-cloudbuild-sa@bionexus-staging.iam.gserviceaccount.com

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Trigger Cloud Build (staging)
        run: |
          gcloud builds submit \
            --config=cloudbuild-staging.yaml \
            --substitutions=SHORT_SHA=${{ github.sha }} \
            .

  deploy-production:
    name: Deploy (Production)
    needs: build-and-deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production   # Requires manual approval in GitHub Environments
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER_PROD }}
          service_account: bionexus-cloudbuild-sa@bionexus-prod.iam.gserviceaccount.com

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Trigger Cloud Build (production)
        run: |
          gcloud builds submit \
            --config=cloudbuild-production.yaml \
            --substitutions=SHORT_SHA=${{ github.sha }} \
            .
```

### 9.3 Cloud Build Configuration

```yaml
# cloudbuild-production.yaml

steps:
  # Step 1: Build Docker image
  - name: "gcr.io/cloud-builders/docker"
    args:
      - build
      - --tag
      - "europe-west3-docker.pkg.dev/$PROJECT_ID/bionexus/api:$SHORT_SHA"
      - --tag
      - "europe-west3-docker.pkg.dev/$PROJECT_ID/bionexus/api:latest"
      - --cache-from
      - "europe-west3-docker.pkg.dev/$PROJECT_ID/bionexus/api:latest"
      - --build-arg
      - BUILDKIT_INLINE_CACHE=1
      - --file
      - bionexus-platform/backend/Dockerfile.prod
      - bionexus-platform/backend
    id: "build-image"

  # Step 2: Push to Artifact Registry
  - name: "gcr.io/cloud-builders/docker"
    args:
      - push
      - "--all-tags"
      - "europe-west3-docker.pkg.dev/$PROJECT_ID/bionexus/api"
    id: "push-image"
    waitFor: ["build-image"]

  # Step 3: Start Cloud SQL Auth Proxy (background)
  - name: "gcr.io/cloud-sql-connectors/cloud-sql-proxy:2"
    args:
      - "--port=5432"
      - "--credentials-file=/root/.config/gcloud/application_default_credentials.json"
      - "${_CLOUD_SQL_INSTANCE}"
    id: "start-proxy"
    waitFor: ["push-image"]

  # Step 4: Run database migrations
  - name: "europe-west3-docker.pkg.dev/$PROJECT_ID/bionexus/api:$SHORT_SHA"
    entrypoint: "python"
    args: ["manage.py", "migrate", "--noinput"]
    env:
      - "DATABASE_URL=postgres://$_DB_USER:$_DB_PASS@localhost:5432/$_DB_NAME"
      - "DJANGO_SECRET_KEY=$$DJANGO_SECRET_KEY"
      - "DJANGO_SETTINGS_MODULE=core.settings.production"
    secretEnv: ["DJANGO_SECRET_KEY"]
    waitFor: ["start-proxy"]
    id: "run-migrations"

  # Step 5: Deploy to Cloud Run (0% traffic initially)
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    args:
      - gcloud
      - run
      - deploy
      - bionexus-api
      - "--image=europe-west3-docker.pkg.dev/$PROJECT_ID/bionexus/api:$SHORT_SHA"
      - "--region=europe-west3"
      - "--no-traffic"   # Deploy new revision without routing traffic
      - "--tag=candidate"
    id: "deploy-no-traffic"
    waitFor: ["run-migrations"]

  # Step 6: Run smoke tests against the tagged revision
  - name: "gcr.io/cloud-builders/curl"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        REVISION_URL=$(gcloud run services describe bionexus-api \
          --region=europe-west3 \
          --format='value(status.traffic[0].url)' \
          --tag=candidate)
        curl -sf "$REVISION_URL/api/health/" || exit 1
        echo "Smoke test passed"
    id: "smoke-test"
    waitFor: ["deploy-no-traffic"]

  # Step 7: Migrate 100% traffic to new revision
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    args:
      - gcloud
      - run
      - services
      - update-traffic
      - bionexus-api
      - "--region=europe-west3"
      - "--to-latest"
    id: "migrate-traffic"
    waitFor: ["smoke-test"]

availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/bionexus-django-secret-key/versions/latest
      env: "DJANGO_SECRET_KEY"

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: E2_HIGHCPU_8
  env:
    - "DOCKER_BUILDKIT=1"

timeout: "1200s"
```

### 9.4 Migration Strategy

Database migrations in a GxP environment require controlled execution:

1. **Forward-only migrations**: Reversible migrations (`migrations.RunSQL` with a reverse SQL) are required for all schema changes so rollback is possible.
2. **Zero-downtime migrations**: Large table alterations use a multi-step approach:
   - Add new column as nullable → deploy → backfill data → add constraint → deploy.
   - Never drop a column in the same deployment that stops using it.
3. **Migration validation**: `python manage.py migrate --check` runs in CI to detect unapplied migrations before build.
4. **Pre-production test**: Migrations run against staging database before production.
5. **Audit record**: Cloud Build logs capture the exact migration step output, providing a traceable record of schema changes for the GxP change control log.

---

## 10. Monitoring & Observability

### 10.1 Cloud Monitoring Setup

```hcl
# terraform/modules/monitoring/main.tf

# Uptime check: API health endpoint
resource "google_monitoring_uptime_check_config" "api_health" {
  display_name = "BioNexus API Health Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/api/health/"
    port         = 443
    use_ssl      = true
    validate_ssl = true
    accepted_response_status_codes {
      status_class = "STATUS_CLASS_2XX"
    }
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "api.bionexus.io"
    }
  }

  checker_type = "STATIC_IP_CHECKERS"
  selected_regions = [
    "EUROPE",
    "USA",
  ]
}

# Alert policy: uptime check failure
resource "google_monitoring_alert_policy" "uptime_failure" {
  display_name = "BioNexus API Down"
  combiner     = "OR"
  conditions {
    display_name = "Uptime check failure"
    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\""
      duration        = "120s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_NEXT_OLDER"
        group_by_fields    = ["resource.label.host"]
      }
    }
  }
  notification_channels = [
    google_monitoring_notification_channel.pagerduty.id,
    google_monitoring_notification_channel.email.id,
  ]
  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert: API p99 latency > 2 seconds
resource "google_monitoring_alert_policy" "high_latency" {
  display_name = "BioNexus API High Latency"
  combiner     = "OR"
  conditions {
    display_name = "p99 latency > 2s"
    condition_threshold {
      filter     = "metric.type=\"run.googleapis.com/request_latencies\" AND resource.label.service_name=\"bionexus-api\""
      duration   = "300s"
      comparison = "COMPARISON_GT"
      threshold_value = 2000   # milliseconds
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_99"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.email.id]
}
```

### 10.2 Custom Metrics for GxP

BioNexus publishes custom metrics to Cloud Monitoring for compliance-critical operations:

```python
# core/monitoring.py

from google.cloud import monitoring_v3
import time
import os

def emit_audit_integrity_metric(
    tenant_id: int,
    chain_intact: bool,
    records_verified: int,
) -> None:
    """
    Emit a custom metric for audit trail integrity verification.
    Triggered after each certified audit export.
    """
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}"

    series = monitoring_v3.TimeSeries()
    series.metric.type = "custom.googleapis.com/bionexus/audit_chain_intact"
    series.metric.labels["tenant_id"] = str(tenant_id)
    series.resource.type = "global"

    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10**9)
    interval = monitoring_v3.TimeInterval(
        {"end_time": {"seconds": seconds, "nanos": nanos}}
    )
    point = monitoring_v3.Point(
        {"interval": interval, "value": {"bool_value": chain_intact}}
    )
    series.points = [point]

    client.create_time_series(name=project_name, time_series=[series])


def emit_ingestion_latency_metric(
    tenant_id: int,
    instrument_id: str,
    latency_ms: float,
) -> None:
    """
    Emit latency metric for BioNexus Box data ingestion.
    Tracks time from HTTP receipt to database write + GCS upload.
    """
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}"

    series = monitoring_v3.TimeSeries()
    series.metric.type = "custom.googleapis.com/bionexus/ingestion_latency_ms"
    series.metric.labels["tenant_id"] = str(tenant_id)
    series.metric.labels["instrument_id"] = instrument_id
    series.resource.type = "global"

    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10**9)
    interval = monitoring_v3.TimeInterval(
        {"end_time": {"seconds": seconds, "nanos": nanos}}
    )
    point = monitoring_v3.Point(
        {"interval": interval, "value": {"double_value": latency_ms}}
    )
    series.points = [point]

    client.create_time_series(name=project_name, time_series=[series])
```

### 10.3 Cloud Logging Configuration

```python
# core/logging_config.py
# Django logging configuration for Cloud Logging structured output

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "cloud_logging": {
            "class": "google.cloud.logging.handlers.CloudLoggingHandler",
            "formatter": "json",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["cloud_logging"],
            "level": "WARNING",
            "propagate": False,
        },
        "bionexus": {
            "handlers": ["cloud_logging"],
            "level": "INFO",
            "propagate": False,
        },
        "bionexus.audit": {
            "handlers": ["cloud_logging"],
            "level": "DEBUG",    # Full audit event logging
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["cloud_logging"],
        "level": "WARNING",
    },
}
```

**Log retention policy (GxP)**

```bash
# Set log retention to 365 days for GxP audit requirements
gcloud logging buckets update _Default \
  --location=global \
  --retention-days=365

# Create a dedicated log bucket for audit logs with 7-year retention
gcloud logging buckets create bionexus-audit-logs \
  --location=europe-west3 \
  --retention-days=2555 \
  --description="BioNexus GxP audit log bucket — 7 year retention"

# Route audit-related Django logs to the dedicated bucket
gcloud logging sinks create bionexus-audit-sink \
  logging.googleapis.com/projects/bionexus-prod/locations/europe-west3/buckets/bionexus-audit-logs \
  --log-filter='jsonPayload.logger="bionexus.audit"'
```

### 10.4 Error Reporting

Cloud Error Reporting automatically groups exceptions from Cloud Logging entries. Django exceptions are structured-logged and automatically captured:

```python
# core/middleware/error_reporting.py

import google.cloud.error_reporting as error_reporting

class ErrorReportingMiddleware:
    """
    Report unhandled Django exceptions to Cloud Error Reporting.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.client = error_reporting.Client()

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        self.client.report_exception(
            http_context=error_reporting.HTTPContext(
                method=request.method,
                url=request.build_absolute_uri(),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                response_status_code=500,
            )
        )
        return None   # Let Django's normal exception handling continue
```

---

## 11. Async Processing: Cloud Tasks / Pub/Sub

### 11.1 Architecture Decision

| Use Case | Service | Rationale |
|----------|---------|-----------|
| BioNexus Box data ingestion queue | **Cloud Tasks** | Deterministic delivery, per-task retry control, HTTP target, rate limiting per queue |
| AI parsing jobs (document OCR, data extraction) | **Cloud Tasks** | Same rationale; AI jobs are long-running and benefit from independent retry |
| Real-time events (instrument status changes) | **Pub/Sub** | Fan-out to multiple subscribers (monitoring, alerting, future webhook delivery) |
| Scheduled audit integrity checks | **Cloud Scheduler → Cloud Tasks** | Cron trigger for nightly integrity sweep |

### 11.2 Cloud Tasks Queue Configuration

```hcl
# terraform/modules/tasks/main.tf

resource "google_cloud_tasks_queue" "ingestion_queue" {
  name     = "bionexus-ingestion-queue"
  location = "europe-west3"

  rate_limits {
    max_concurrent_dispatches = 10
    max_dispatches_per_second = 50
  }

  retry_config {
    max_attempts       = 5
    max_retry_duration = "3600s"   # 1 hour total retry window
    min_backoff        = "10s"
    max_backoff        = "300s"    # 5 minutes max between retries
    max_doublings      = 4
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0   # Log all task dispatches for GxP traceability
  }
}

resource "google_cloud_tasks_queue" "ai_parsing_queue" {
  name     = "bionexus-ai-parsing-queue"
  location = "europe-west3"

  rate_limits {
    max_concurrent_dispatches = 5    # Limit AI API concurrency
    max_dispatches_per_second = 2
  }

  retry_config {
    max_attempts       = 3
    min_backoff        = "30s"
    max_backoff        = "600s"
    max_doublings      = 3
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}
```

### 11.3 Django Task Enqueueing

```python
# modules/instruments/services/ingestion_service.py

import json
import os
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2

def enqueue_ingestion_task(
    tenant_id: int,
    instrument_id: str,
    gcs_object_path: str,
    uploaded_by_user_id: int,
) -> str:
    """
    Enqueue a BioNexus Box data ingestion task for async processing.
    Returns the Cloud Tasks task name for audit trail reference.
    """
    client = tasks_v2.CloudTasksClient()

    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = "europe-west3"
    queue = "bionexus-ingestion-queue"
    parent = client.queue_path(project, location, queue)

    task_payload = {
        "tenant_id": tenant_id,
        "instrument_id": instrument_id,
        "gcs_object_path": gcs_object_path,
        "uploaded_by_user_id": uploaded_by_user_id,
    }

    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=f"https://api.bionexus.io/internal/tasks/process-ingestion/",
            headers={"Content-Type": "application/json"},
            body=json.dumps(task_payload).encode(),
            oidc_token=tasks_v2.OidcToken(
                service_account_email=f"bionexus-api-sa@{project}.iam.gserviceaccount.com",
                audience=f"https://api.bionexus.io",
            ),
        )
    )

    response = client.create_task(parent=parent, task=task)
    return response.name
```

### 11.4 Pub/Sub for Instrument Events

```python
# modules/instruments/events.py

import json
import os
from google.cloud import pubsub_v1

def publish_instrument_status_event(
    tenant_id: int,
    instrument_id: str,
    status: str,
    previous_status: str,
) -> None:
    """
    Publish an instrument status change event to Pub/Sub.
    Subscribers include: monitoring dashboards, alert systems, audit trail.
    """
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        os.environ["GOOGLE_CLOUD_PROJECT"],
        "bionexus-instrument-events",
    )

    event_data = {
        "event_type": "INSTRUMENT_STATUS_CHANGED",
        "tenant_id": tenant_id,
        "instrument_id": instrument_id,
        "status": status,
        "previous_status": previous_status,
    }

    future = publisher.publish(
        topic_path,
        data=json.dumps(event_data).encode("utf-8"),
        tenant_id=str(tenant_id),         # Pub/Sub message attribute for filtering
        instrument_id=instrument_id,
    )
    future.result()   # Wait for publish confirmation
```

---

## 12. CDN & Frontend: Firebase Hosting

### 12.1 Why Firebase Hosting

Firebase Hosting provides a globally distributed CDN backed by GCP's edge network with automatic HTTPS, HTTP/2, and Brotli compression. It integrates with the GCP project and IAM, making it the natural choice for hosting the React SPA alongside the Django backend. Deployment is atomic and supports rollback to any previous release.

### 12.2 Firebase Hosting Configuration

```json
// firebase.json (in repo root)
{
  "hosting": {
    "site": "bionexus-app",
    "public": "bionexus-platform/frontend/build",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "headers": [
      {
        "source": "**",
        "headers": [
          {
            "key": "Strict-Transport-Security",
            "value": "max-age=31536000; includeSubDomains; preload"
          },
          {
            "key": "X-Content-Type-Options",
            "value": "nosniff"
          },
          {
            "key": "X-Frame-Options",
            "value": "DENY"
          },
          {
            "key": "Content-Security-Policy",
            "value": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://api.bionexus.io;"
          },
          {
            "key": "Referrer-Policy",
            "value": "strict-origin-when-cross-origin"
          }
        ]
      },
      {
        "source": "/static/**",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      },
      {
        "source": "**/*.html",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "no-cache"
          }
        ]
      }
    ],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "bionexus-api",
          "region": "europe-west3"
        }
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

### 12.3 Cache Strategy

| Asset Type | Cache-Control | Rationale |
|-----------|--------------|-----------|
| `/static/js/*.chunk.js` | `max-age=31536000, immutable` | Content-hashed filenames, safe to cache forever |
| `/static/css/*.chunk.css` | `max-age=31536000, immutable` | Same as JS chunks |
| `/index.html` | `no-cache` | SPA entry point must always be fresh |
| `/favicon.ico`, `/manifest.json` | `max-age=86400` | 1-day cache, infrequently updated |
| `/api/**` | No cache (proxied) | API responses are never cached at CDN layer |

### 12.4 Deployment

```bash
# CI/CD step (in GitHub Actions, after React build)
npm run build

# Deploy to Firebase Hosting (staging)
firebase deploy --only hosting --project bionexus-staging

# Deploy to Firebase Hosting (production)
firebase deploy --only hosting --project bionexus-prod

# Rollback to previous release
firebase hosting:rollback --project bionexus-prod
```

---

## 13. Data Residency & EU Compliance

### 13.1 Region Selection Rationale

**Primary Region: `europe-west3` (Frankfurt, Germany)**

Frankfurt is chosen as the primary region because:
- Located in Germany, which has among the strictest data protection enforcement in the EU (under GDPR via the BDSG).
- GCP's Frankfurt region holds ISO 27001, SOC 2 Type II, and C5 (German BSI Cloud Computing Compliance Criteria Catalogue) certifications.
- Low latency (~5–20ms) to most Western European pharma customers (Switzerland, Belgium, Netherlands, UK).
- Satisfies EU Annex 11 §4.8 requirement for data storage location traceability.

**Disaster Recovery Region: `europe-west4` (Netherlands)**

The DR region is Netherlands because:
- Adjacent to Frankfurt within the EU, maintaining data sovereignty.
- Paired with Frankfurt in GCP's dual-region bucket configurations (`eur4`).
- Sufficient physical separation (>200km) to be unaffected by a regional failure.

### 13.2 Data Sovereignty Enforcement

```hcl
# terraform/main.tf
# Enforce resource location via Organization Policy

resource "google_org_policy_policy" "restrict_resource_locations" {
  name   = "projects/${var.project_id}/policies/gcp.resourceLocations"
  parent = "projects/${var.project_id}"

  spec {
    rules {
      values {
        allowed_values = [
          "in:europe-west3-locations",
          "in:europe-west4-locations",
          "in:europe-locations",     # Covers dual-region resources
        ]
      }
    }
  }
}
```

This Organization Policy prevents any developer or CI/CD pipeline from creating resources outside the approved European regions, even if a misconfigured Terraform module specifies an incorrect region.

### 13.3 GDPR Technical Compliance

| GDPR Requirement | GCP Implementation |
|-----------------|-------------------|
| **Data at rest encryption** | GCP-managed encryption (AES-256) on all Cloud SQL, GCS, and Secret Manager resources by default. Customer-Managed Encryption Keys (CMEK) available for additional control. |
| **Data in transit encryption** | TLS 1.2+ enforced via Cloud Load Balancer SSL policy. Cloud SQL requires SSL. Internal VPC traffic between Cloud Run and Cloud SQL is encrypted via the Auth Proxy. |
| **Right to erasure** | BioNexus implements soft-delete (`is_deleted=True`) with tenant-scoped hard-delete capability for non-audit data. Audit trail records are retained per GxP requirements and cannot be deleted. |
| **Data processor agreement** | Google Cloud DPA available at cloud.google.com/terms/data-processing-addendum. Must be executed before onboarding EU customers. |
| **Sub-processor disclosure** | Google's sub-processor list is publicly maintained. BioNexus maintains a list of all sub-processors in its privacy documentation. |

### 13.4 EU Annex 11 Cloud Considerations

EU Annex 11 §3 (Supplier / System Provider) requires that computerized systems providers can demonstrate their infrastructure meets GxP requirements. BioNexus addresses this through:

1. **GCP Compliance Reports**: Available via the GCP Compliance Reports Manager (`console.cloud.google.com/compliance`). SOC 2 Type II and ISO 27001 reports are downloadable NDA-free for supplier assessment documentation.
2. **Audit Log Completeness**: All GCP control-plane actions (who created/modified which resource) are captured in Cloud Audit Logs (Admin Activity log) and retained for 400 days by default; extended to 365 days via the configuration in Section 10.3.
3. **Change Management**: Infrastructure changes are made exclusively through Terraform (`terraform plan` + `terraform apply`) with plans reviewed in pull requests. No ad-hoc console changes are permitted in production.
4. **Backup Verification**: Cloud SQL automated backups are tested quarterly by restoring to a staging instance and running Django's `check` management command and a sample query set.

---

## 14. Disaster Recovery & Business Continuity

### 14.1 Recovery Objectives

| Tier | Scenario | RTO | RPO |
|------|---------|-----|-----|
| **T1** | Cloud Run revision failure (bad deploy) | < 5 minutes | 0 (traffic rollback) |
| **T2** | Single zone failure within `europe-west3` | < 10 minutes | 0 (Cloud SQL HA automatic failover) |
| **T3** | Full `europe-west3` region outage | < 4 hours | < 1 hour (replication lag) |
| **T4** | Data corruption / ransomware | < 8 hours | < 24 hours (daily backup) |

### 14.2 Backup Strategy

| Data | Backup Method | Frequency | Retention | Location |
|------|---------------|-----------|-----------|----------|
| Cloud SQL (PostgreSQL) | Automated managed backup | Daily at 03:00 UTC | 7 backups | `europe-west3` |
| Cloud SQL (PITR) | Transaction log streaming | Continuous | 7 days | `europe-west3` |
| Cloud SQL (DR replica) | Cross-region replication | Near-real-time (< 1 min lag) | N/A — live replica | `europe-west4` |
| GCS raw data | Object versioning | On every write | 90 days for non-current | `europe-west3` |
| GCS audit exports | Object versioning + retention lock | On every write | 7 years | `europe-west3` |
| GCS backups bucket | Terraform state, manual dumps | Weekly or on change | 365 days | dual-region `eur4` |
| Docker images | Artifact Registry | On every build | 30 most recent tags | `europe-west3` |

### 14.3 Failover Procedures

**T1: Bad deployment rollback (< 5 minutes)**

```bash
# Identify the previous stable revision
gcloud run revisions list \
  --service=bionexus-api \
  --region=europe-west3 \
  --format="table(name,status.conditions[0].status,spec.containerConcurrency)"

# Route all traffic back to previous revision
gcloud run services update-traffic bionexus-api \
  --region=europe-west3 \
  --to-revisions=bionexus-api-PREVIOUS_REVISION_ID=100
```

**T2: Zone failure — Cloud SQL HA (automatic)**

Cloud SQL Regional HA handles this automatically. The standby instance in a different `europe-west3` zone promotes within 60 seconds. No application-level action is required. The Django app will retry connections (governed by `CONN_MAX_AGE = 0` during failover window, then restored).

Monitor via:
```bash
gcloud sql operations list --instance=bionexus-db-prod --filter="operationType=FAILOVER"
```

**T3: Full region failover to `europe-west4` (runbook outline)**

This procedure is documented in full in `docs/DR_RUNBOOK.md` (to be created). Summary:

1. Declare incident. Notify stakeholders. Open incident channel.
2. Confirm `europe-west3` region degradation via GCP Status Dashboard.
3. Promote DR replica in `europe-west4` to standalone primary:
   ```bash
   gcloud sql instances promote-replica bionexus-db-prod-replica
   ```
4. Update Secret Manager `bionexus-cloud-sql-connection` to point to DR instance.
5. Deploy Cloud Run service to `europe-west4` using the last known-good image from Artifact Registry.
6. Update Cloud DNS A record to point to DR Load Balancer IP (pre-provisioned).
7. Validate application health and audit trail integrity.
8. Notify customers of degraded operation and estimated recovery time.
9. After primary region recovers: re-sync data, switch DNS back, decommission DR services.

**T4: Data corruption recovery**

```bash
# Point-in-time recovery to 30 minutes before corruption was detected
gcloud sql instances clone bionexus-db-prod bionexus-db-recovery \
  --point-in-time="2026-02-28T10:00:00Z"

# Validate recovery instance
cloud-sql-proxy bionexus-prod:europe-west3:bionexus-db-recovery &
psql -h localhost -U bionexus -d bionexus -c "SELECT COUNT(*) FROM audit_log;"

# If validated: redirect application to recovery instance, rename as appropriate
```

### 14.4 Business Continuity for BioNexus Box

The BioNexus Box hardware gateway includes a local buffer capable of storing up to 8 hours of instrument data. During a cloud outage, the Box continues collecting data from lab instruments. Data is queued locally and retransmitted once the API endpoint becomes reachable. The retry logic uses exponential backoff with a maximum retry window of 72 hours, after which the lab is alerted to initiate manual data entry procedures.

---

## 15. Cost Estimation

All prices are approximate, based on GCP europe-west3 (Frankfurt) list prices as of early 2026. Committed Use Discounts (CUDs) of 20–30% are available for Cloud SQL and Compute resources with 1-year commitments.

### 15.1 Early Stage — 2 Active Tenants

| Service | Configuration | Monthly Est. |
|---------|--------------|-------------|
| Cloud Run | ~50K requests/day, 128ms avg duration, 2Gi, min 1 instance | ~$25 |
| Cloud SQL | `db-custom-1-3840`, 50 GB SSD, Regional HA | ~$90 |
| Cloud Storage | 20 GB raw data + 5 GB exports, STANDARD | ~$2 |
| Cloud Load Balancer | 1 Global LB, ~50 GB egress | ~$20 |
| Cloud Armor | WAF policy, ~1.5M requests/month | ~$15 |
| Secret Manager | 10 secrets, ~50K access operations | ~$1 |
| Cloud Tasks | ~100K tasks/month | ~$1 |
| Cloud Monitoring | Default metrics + custom metrics, uptime checks | ~$10 |
| Cloud Logging | ~5 GB/month logs | ~$3 |
| Firebase Hosting | ~2 GB hosting, ~10 GB transfer | ~$2 |
| Artifact Registry | ~10 GB Docker image storage | ~$1 |
| VPC + Cloud NAT | ~5 GB NAT egress | ~$3 |
| **Total (estimated)** | | **~$173/month** |

Note: With a minimum Cloud Run instance held warm, cold start costs are eliminated but a baseline compute cost of ~$15–20/month is incurred.

### 15.2 Growth Stage — 30 Active Tenants

| Service | Configuration | Monthly Est. |
|---------|--------------|-------------|
| Cloud Run | ~750K requests/day, 128ms avg, 2Gi, min 2 instances, max 20 | ~$200 |
| Cloud SQL | `db-custom-2-7680`, 200 GB SSD, Regional HA + DR replica | ~$400 |
| Cloud Storage | 500 GB raw data + 100 GB exports, tiered storage | ~$25 |
| Cloud Load Balancer | 1 Global LB, ~500 GB egress | ~$50 |
| Cloud Armor | WAF policy, ~22M requests/month | ~$50 |
| Secret Manager | 15 secrets, ~500K access operations | ~$5 |
| Cloud Tasks | ~2M tasks/month | ~$5 |
| Pub/Sub | ~5M messages/month | ~$3 |
| Cloud Monitoring | Custom dashboards, alerting policies | ~$30 |
| Cloud Logging | ~50 GB/month logs, 7-year audit bucket | ~$40 |
| Firebase Hosting | ~10 GB hosting, ~200 GB transfer | ~$15 |
| Artifact Registry | ~25 GB Docker image storage | ~$2 |
| VPC + Cloud NAT | ~50 GB NAT egress | ~$20 |
| Cloud Scheduler | Nightly integrity check jobs | ~$1 |
| **Total (estimated)** | | **~$846/month** |

### 15.3 Cost Optimization Strategies

- **Committed Use Discounts (CUD)**: 1-year CUD on Cloud SQL and VPC Access Connector reduces DB cost by ~25%.
- **Cloud Run min instances = 0 in staging**: Staging environment costs near-zero outside business hours.
- **GCS lifecycle rules**: Automatic tiering of raw data files to NEARLINE (after 365 days) and COLDLINE (after 5 years) reduces storage costs by 60–80% for historical data.
- **Log-based cost controls**: Exclude `/api/health/` probe logs from Cloud Logging to reduce log ingestion volume.
- **Artifact Registry cleanup**: `gcloud artifacts docker images list-tags` with a policy to retain only the 30 most recent images.

```bash
# Cost optimization: exclude health check logs from ingestion
gcloud logging exclusions create exclude-health-probes \
  --log-filter='resource.type="cloud_run_revision" AND httpRequest.requestUrl=~"/api/health/"' \
  --description="Exclude Cloud Run health probe logs to reduce cost"
```

---

## 16. Environment Strategy

### 16.1 Environment Definitions

| Environment | GCP Project | Purpose | Cloud Run min | Cloud SQL HA | Cost |
|-------------|-------------|---------|---------------|-------------|------|
| `development` | Local Docker Compose | Local development and unit testing | N/A | N/A | $0 |
| `staging` | `bionexus-staging` | Integration testing, pre-production validation, CI/CD smoke tests | 0 (cold starts OK) | Zonal | ~$60/month |
| `production` | `bionexus-prod` | Live customer environment | 1 (warm) | Regional (HA) | See Section 15 |

### 16.2 Infrastructure-as-Code with Terraform

All GCP resources are managed by Terraform. The repository structure is:

```
terraform/
├── environments/
│   ├── staging/
│   │   ├── main.tf          # Calls modules with staging-specific variables
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── production/
│       ├── main.tf          # Calls modules with prod-specific variables
│       ├── variables.tf
│       └── terraform.tfvars
├── modules/
│   ├── cloud_run/           # Cloud Run service definition
│   ├── cloud_sql/           # Cloud SQL instance + replica + IAM
│   ├── storage/             # GCS buckets + lifecycle policies
│   ├── networking/          # VPC, subnets, LB, Cloud Armor, NAT
│   ├── iam/                 # Service accounts, IAM bindings
│   ├── secrets/             # Secret Manager secrets (without values)
│   ├── monitoring/          # Uptime checks, alert policies, dashboards
│   └── tasks/               # Cloud Tasks queues, Pub/Sub topics
└── backend.tf               # Remote state: GCS bucket
```

**Remote state configuration**

```hcl
# terraform/backend.tf
terraform {
  backend "gcs" {
    bucket = "bionexus-terraform-state"
    prefix = "terraform/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  required_version = ">= 1.7.0"
}
```

**Environment-specific variable example**

```hcl
# terraform/environments/production/terraform.tfvars

project_id   = "bionexus-prod"
region       = "europe-west3"
environment  = "prod"

# Cloud Run
min_instances = "1"
image_tag     = "latest"   # Override per deployment via -var flag

# Cloud SQL
db_tier = "db-custom-2-7680"

# Cloud Armor
bionexus_box_ip_ranges = [
  "203.0.113.0/24",   # Lab site A (replace with actual device IP ranges)
  "198.51.100.0/28",  # Lab site B
]
```

### 16.3 Promotion Workflow

```
Code change → PR → CI tests (test environment) → Merge to staging branch
    │
    ▼
Automated deploy to bionexus-staging GCP project
    │
    ▼
QA validation (manual + automated smoke tests)
    │
    ▼
Merge to main branch → Manual approval gate in GitHub Environments
    │
    ▼
Terraform plan reviewed in PR → terraform apply (production)
    │
    ▼
Cloud Run deploy → Traffic migration → Post-deploy health check
```

**Change Control Log for GxP**: Every Terraform plan and apply run is logged in Cloud Build history with the full plan output and the identity of the user or service account that triggered it. This provides an immutable record of infrastructure changes for GxP change management documentation (EU Annex 11 §10, 21 CFR Part 11 §11.10(k)).

---

## 17. GxP Compliance in Cloud

### 17.1 How GCP Meets 21 CFR Part 11 Infrastructure Requirements

21 CFR Part 11 applies to electronic records and electronic signatures maintained by FDA-regulated entities. BioNexus's use of GCP addresses the infrastructure-level requirements as follows:

| 21 CFR Part 11 Section | Requirement | GCP Implementation |
|-----------------------|-------------|-------------------|
| §11.10(a) | Validation — systems validated for accuracy, reliability, consistent performance | GCP services have independent SOC 2 Type II audits. BioNexus IQ/OQ/PQ covers configuration validation (see `docs/SYSTEM_VALIDATION_PLAN.md`). |
| §11.10(b) | Ability to generate accurate and complete copies of records | Cloud SQL PITR enables restoration to any second within the 7-day window. GCS versioning retains all file versions. Cloud Logging captures all API activity. |
| §11.10(c) | Record protection from destruction or unauthorized alteration | Cloud SQL has deletion protection + RLS audit immutability. GCS retention policies prevent premature deletion. Audit log entries cannot be modified by application-level code. |
| §11.10(d) | System access limited to authorized individuals | GCP IAM with least-privilege service accounts. VPC restricts all internal access. Cloud Armor enforces IP allowlists for BioNexus Box devices. |
| §11.10(e) | Audit trails — secure, computer-generated, time-stamped | Audit log records include GCP-sourced UTC timestamps. Cloud Audit Logs provide an independent record of all GCP API calls. SHA-256 chain prevents backdating of application-level audit records. |
| §11.10(f) | Operational system checks | Cloud Monitoring uptime checks and liveness probes enforce that only operational systems process data. |
| §11.10(g) | Device checks to detect valid data input source | BioNexus Box devices authenticate using client certificates (mTLS) and device-specific PSKs validated at the API level. |
| §11.10(h) | Personnel qualification | Enforced through GCP IAM role assignments, two-person review of production changes, and change management documentation. |
| §11.10(k) | System documentation | Terraform state provides a machine-readable record of all infrastructure. Cloud Build history provides an audit log of all deployment activities. |

### 17.2 GCP Compliance Certifications Relevant to BioNexus

| Certification | Relevance to BioNexus/GxP |
|--------------|--------------------------|
| **SOC 2 Type II** | Demonstrates GCP's controls around security, availability, and confidentiality have been independently audited over a 12-month period. Directly citable in BioNexus supplier assessment under GAMP5 Chapter 9. |
| **ISO 27001** | International standard for information security management. Provides assurance that GCP's ISMS is systematically managed. Required by most EU pharma customers as a baseline supplier requirement. |
| **ISO 27017** | Cloud-specific extension of ISO 27001. Addresses responsibilities for cloud service providers and cloud customers (shared responsibility model). Clarifies BioNexus's obligations vs. GCP's obligations. |
| **ISO 27018** | Code of practice for protection of personally identifiable information in public clouds. Supports GDPR Article 28 processor obligations. |
| **C5 (BSI)** | German Federal Office for Information Security Cloud Computing Compliance Criteria Catalogue. Directly relevant for German and EU pharma customers subject to BSI guidance. |
| **HITRUST CSF** | Health Information Trust Alliance Common Security Framework. While not mandatory for pharma QC data (which is not health data under HIPAA), HITRUST certification demonstrates a mature, audited security program. |
| **ISO 9001** | Quality management system certification. Demonstrates GCP's commitment to continuous process improvement — relevant to GAMP5 supplier assessment. |
| **FedRAMP High** | US federal government cloud authorization. Demonstrates the highest tier of US government security controls. Relevant for BioNexus customers with FDA inspection exposure. |

GCP compliance reports are available for download via the GCP Compliance Reports Manager at `console.cloud.google.com/compliance`. These should be downloaded annually and filed in the BioNexus Quality Management System (QMS) as evidence of supplier qualification.

### 17.3 Shared Responsibility Model

In a GxP cloud context, regulatory responsibility does not transfer to the cloud provider. The shared responsibility model for BioNexus is:

**GCP Responsibilities (Infrastructure layer)**
- Physical security of data centers
- Hardware reliability and redundancy
- Hypervisor and host OS security
- Network security within GCP backbone
- Encryption key management for Google-managed keys
- Underlying service availability (per SLA)

**BioNexus Responsibilities (Platform & Application layer)**
- Application security (Django code, API logic)
- Data model design and access control implementation
- Configuration of GCP services (IAM policies, firewall rules, encryption settings)
- Validation of GCP configuration (IQ/OQ for cloud infrastructure)
- Audit trail integrity at the application level (SHA-256 chaining)
- User authentication and authorization (JWT, RBAC)
- Data backup verification (Cloud SQL restore testing)
- Incident response procedures for application-level events
- Change management for infrastructure configuration changes

**Customer (Tenant) Responsibilities**
- User account management (who has access to their tenant)
- Sample and instrument data accuracy
- Electronic signature workflow compliance
- User training and SOPs

### 17.4 GCP Configuration Qualification (IQ/OQ Checklist Outline)

The full IQ/OQ protocol is in `docs/SYSTEM_VALIDATION_PLAN.md`. Cloud infrastructure IQ checks include:

**Installation Qualification (IQ) — Cloud Infrastructure**
- [ ] All Terraform resources deployed successfully in production project
- [ ] Cloud SQL instance created in `europe-west3` with REGIONAL availability type
- [ ] Cloud SQL public IP is disabled; only private VPC IP is accessible
- [ ] SSL mode set to `ENCRYPTED_ONLY` on Cloud SQL
- [ ] GCS buckets have versioning enabled
- [ ] GCS raw-data bucket has retention policy of 157,680,000 seconds (5 years)
- [ ] Cloud Armor WAF policy is attached to the backend service
- [ ] Secret Manager secrets have replication restricted to `europe-west3`
- [ ] Organization policy restricts resource creation to European regions
- [ ] Cloud Run service account has no `roles/editor` or `roles/owner` bindings
- [ ] Cloud Logging retention is set to 365 days for default bucket

**Operational Qualification (OQ) — Cloud Infrastructure**
- [ ] Cloud Run health endpoint returns 200 within 5 seconds from EU and US uptime checkers
- [ ] A simulated zone failure confirms Cloud SQL HA failover occurs within 60 seconds and API recovers within 2 minutes
- [ ] Cloud SQL point-in-time recovery test: restore to T-1h and validate record count matches expected
- [ ] Cloud Armor rate limiting test: >100 requests/min from single IP returns 429
- [ ] Cloud Armor SQL injection test: crafted malicious request returns 403
- [ ] Secret rotation test: update Django secret key, redeploy Cloud Run, confirm JWT tokens issued with old key are rejected, new tokens are accepted
- [ ] Cloud Tasks retry test: simulate ingestion endpoint failure, confirm task retries with exponential backoff and max 5 attempts

---

## Appendix A: GCP CLI Quick Reference

```bash
# Authenticate
gcloud auth login
gcloud config set project bionexus-prod

# Cloud Run
gcloud run services list --region=europe-west3
gcloud run revisions list --service=bionexus-api --region=europe-west3
gcloud run services describe bionexus-api --region=europe-west3

# Cloud SQL
gcloud sql instances list
gcloud sql instances describe bionexus-db-prod
gcloud sql backups list --instance=bionexus-db-prod
gcloud sql operations list --instance=bionexus-db-prod

# Secret Manager
gcloud secrets list
gcloud secrets versions list bionexus-django-secret-key
gcloud secrets versions access latest --secret=bionexus-django-secret-key

# Cloud Storage
gsutil ls gs://bionexus-raw-data-prod/
gsutil versioning get gs://bionexus-raw-data-prod/
gsutil retention get gs://bionexus-raw-data-prod/

# Cloud Tasks
gcloud tasks queues list --location=europe-west3
gcloud tasks queues describe bionexus-ingestion-queue --location=europe-west3

# Monitoring
gcloud monitoring uptime-checks list
gcloud monitoring alert-policies list

# Cloud Build
gcloud builds list --filter="status=FAILURE" --limit=10
gcloud builds log BUILD_ID
```

## Appendix B: Terraform Workflow

```bash
# Initial setup (one-time)
cd terraform/environments/production
terraform init

# Plan and review changes
terraform plan -var-file=terraform.tfvars -out=tfplan
# Review tfplan output carefully before applying

# Apply changes
terraform apply tfplan

# View current state
terraform state list
terraform state show google_cloud_run_service.bionexus_api

# Destroy staging environment (NEVER run on production)
terraform destroy -var-file=terraform.tfvars -target=google_cloud_run_service.bionexus_api
```

---

**Document Version**: 1.0
**Last Updated**: 2026-02-28
**Next Review**: 2026-08-28
**Owner**: BioNexus Engineering Team
**Status**: Approved for Engineering Reference
