#!/usr/bin/env node
/**
 * BioNexus Docs — Markdown → DOCX converter + Google Drive uploader.
 *
 * Converts all 11 .md files in docs/ to professionally formatted .docx,
 * then uploads each to the correct Google Drive folder (replacing any
 * existing raw-markdown copies).
 *
 * Usage:
 *   node convert_to_docx.js              # convert + upload
 *   node convert_to_docx.js --local-only # convert only, no upload
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  PageBreak, TableOfContents, Footer, Header, Tab, TabStopType,
  TabStopPosition, convertInchesToTwip, LevelFormat,
  SectionType, PageNumber, NumberFormat,
} = require("docx");
const { google } = require("googleapis");

// ── Config ─────────────────────────────────────────────────────────────────

const DOCS_DIR = __dirname;
const OUT_DIR = path.join(DOCS_DIR, "docx_output");

const DARK_BLUE   = "1B2A4A";
const MED_BLUE    = "2B4A7A";
const LIGHT_BLUE  = "3B6EA6";
const WHITE       = "FFFFFF";
const BODY_TEXT   = "333333";
const MUTED       = "777777";
const CODE_BG     = "F0F2F5";
const CODE_BORDER = "D0D5DD";
const TBL_ALT     = "F5F7FA";
const ACCENT_RED  = "CC3333";

// Drive folder mapping
const FOLDER_MAP = {
  TECHNICAL: "1b6rv9OiSze6ITeGNiovZeo-32vYeZ8QJ",
  STRATEGY:  "1Up8Ak9wSpNA2Frcv3Et04ZAsKaxlEseD",
  BUSINESS:  "1JTed4VbxMpqTMXENLV4ZXOjSe28TMJmw",
};

const FILE_ROUTING = {
  "PRODUCT_ROADMAP":           "STRATEGY",
  "CUSTOMER_ONBOARDING_GUIDE": "BUSINESS",
  "DATA_RETENTION_DR_POLICY":  "BUSINESS",
  // All others → TECHNICAL
};

function getFolderId(baseName) {
  const key = baseName.replace(/\.md$/, "");
  return FOLDER_MAP[FILE_ROUTING[key] || "TECHNICAL"];
}

// ── Markdown parser ────────────────────────────────────────────────────────

function parseMd(text) {
  const lines = text.split("\n");
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const s = line.trim();

    // Blank line
    if (!s) { i++; continue; }

    // Horizontal rule
    if (/^---+$/.test(s)) { i++; continue; }

    // Code block
    if (s.startsWith("```")) {
      const lang = s.slice(3).trim();
      i++;
      const codeLines = [];
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      blocks.push({ type: "code", content: codeLines.join("\n"), lang });
      continue;
    }

    // Table
    if (s.startsWith("|") && i + 1 < lines.length && /^\|[\s\-:|]+\|/.test(lines[i + 1]?.trim())) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i].trim());
        i++;
      }
      blocks.push({ type: "table", rows: parseTable(tableLines) });
      continue;
    }

    // Headings
    const hMatch = s.match(/^(#{1,4})\s+(.+)/);
    if (hMatch) {
      blocks.push({ type: "heading", level: hMatch[1].length, text: stripLinks(hMatch[2]) });
      i++; continue;
    }

    // Checklist
    const clMatch = s.match(/^- \[[ x]\] (.+)/);
    if (clMatch) {
      blocks.push({ type: "checklist", text: clMatch[1] });
      i++; continue;
    }

    // Bullet
    const bMatch = line.match(/^(\s*)-\s+(.+)/);
    if (bMatch) {
      const level = Math.min(Math.floor(bMatch[1].length / 2), 2);
      blocks.push({ type: "bullet", text: bMatch[2], level });
      i++; continue;
    }

    // Numbered list
    const nMatch = s.match(/^(\d+)\.\s+(.+)/);
    if (nMatch) {
      blocks.push({ type: "numbered", num: nMatch[1], text: nMatch[2] });
      i++; continue;
    }

    // Regular paragraph
    blocks.push({ type: "paragraph", text: s });
    i++;
  }

  return blocks;
}

function parseTable(lines) {
  const rows = [];
  for (const ln of lines) {
    if (/^\|[\s\-:|]+\|$/.test(ln)) continue; // separator
    const cells = ln.split("|").slice(1, -1).map(c => c.trim());
    rows.push(cells);
  }
  return rows;
}

function stripLinks(text) {
  return text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
}

// ── Inline formatting → TextRun[] ──────────────────────────────────────────

function inlineRuns(text, baseOpts = {}) {
  const runs = [];
  const pattern = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`|([^*`]+))/g;
  let m;
  while ((m = pattern.exec(text)) !== null) {
    if (m[2]) { // bold
      runs.push(new TextRun({ text: m[2], bold: true, font: "Arial", size: 20, color: BODY_TEXT, ...baseOpts }));
    } else if (m[3]) { // italic
      runs.push(new TextRun({ text: m[3], italics: true, font: "Arial", size: 20, color: BODY_TEXT, ...baseOpts }));
    } else if (m[4]) { // inline code
      runs.push(new TextRun({ text: m[4], font: "Courier New", size: 18, color: "1A1A2E",
        shading: { type: ShadingType.CLEAR, fill: "E8EBF0" } }));
    } else if (m[5]) { // plain
      runs.push(new TextRun({ text: m[5], font: "Arial", size: 20, color: BODY_TEXT, ...baseOpts }));
    }
  }
  return runs.length ? runs : [new TextRun({ text, font: "Arial", size: 20, color: BODY_TEXT, ...baseOpts })];
}

// ── Document metadata extraction ───────────────────────────────────────────

function extractMeta(text) {
  const meta = {};
  const patterns = [
    [/\*\*Document ID:\*\*\s*(.+)/i, "docId"],
    [/\*\*Version:\*\*\s*(.+)/i, "version"],
    [/\*\*Status:\*\*\s*(.+)/i, "status"],
    [/\*\*Date:\*\*\s*(.+)/i, "date"],
    [/\*\*Prepared by:\*\*\s*(.+)/i, "author"],
    [/\*\*Review Partner:\*\*\s*(.+)/i, "reviewer"],
    [/\*\*Classification:\*\*\s*(.+)/i, "classification"],
    [/\*\*Audience:\*\*\s*(.+)/i, "audience"],
    [/\*\*Decision Makers:\*\*\s*(.+)/i, "decisionMakers"],
    [/\*\*Horizon:\*\*\s*(.+)/i, "horizon"],
  ];
  for (const [rx, key] of patterns) {
    const m = text.match(rx);
    if (m) meta[key] = m[1].trim();
  }
  // Try table-based meta (CUSTOMER_ONBOARDING_GUIDE style)
  const tblMatch = text.match(/\| Field \| Value \|[\s\S]*?\n\n/);
  if (tblMatch) {
    for (const line of tblMatch[0].split("\n")) {
      const cells = line.split("|").map(c => c.trim()).filter(Boolean);
      if (cells.length === 2 && cells[0] !== "Field") {
        const key = cells[0].toLowerCase().replace(/\s+/g, "_");
        if (key === "document_id") meta.docId = cells[1];
        if (key === "version") meta.version = cells[1];
        if (key === "date") meta.date = cells[1];
        if (key === "audience") meta.audience = cells[1];
        if (key === "classification") meta.classification = cells[1];
      }
    }
  }
  return meta;
}

function extractTitle(text) {
  const m = text.match(/^#\s+(.+)/m);
  return m ? stripLinks(m[1]) : "BioNexus Document";
}

function extractSubtitle(text) {
  // Look for a second line under the title or a **For ...** line
  const m = text.match(/^#\s+.+\n+(?:##\s+(.+)|(\*\*For .+\*\*))/m);
  if (m) return stripLinks((m[1] || m[2] || "").replace(/\*\*/g, ""));
  return "";
}

// ── Cover page ─────────────────────────────────────────────────────────────

function buildCover(title, subtitle, meta) {
  const children = [];

  // Spacer
  for (let k = 0; k < 6; k++) {
    children.push(new Paragraph({ spacing: { after: 200 } }));
  }

  // Title banner — dark blue table cell
  children.push(
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [
        new TableRow({
          children: [
            new TableCell({
              shading: { type: ShadingType.CLEAR, fill: DARK_BLUE },
              borders: noBorders(),
              width: { size: 100, type: WidthType.PERCENTAGE },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  spacing: { before: 300, after: 100 },
                  children: [new TextRun({ text: title, bold: true, color: WHITE, size: 56, font: "Arial" })],
                }),
                ...(subtitle ? [new Paragraph({
                  alignment: AlignmentType.CENTER,
                  spacing: { after: 300 },
                  children: [new TextRun({ text: subtitle, color: "AACCEE", size: 28, font: "Arial" })],
                })] : [new Paragraph({ spacing: { after: 200 } })]),
              ],
            }),
          ],
        }),
      ],
    })
  );

  children.push(new Paragraph({ spacing: { after: 300 } }));

  // Meta table
  const metaRows = [];
  const labels = [
    ["docId", "Document ID"], ["version", "Version"], ["status", "Status"],
    ["date", "Date"], ["author", "Prepared by"], ["reviewer", "Review Partner"],
    ["classification", "Classification"], ["audience", "Audience"],
    ["horizon", "Horizon"], ["decisionMakers", "Decision Makers"],
  ];
  for (const [key, label] of labels) {
    if (meta[key]) metaRows.push([label, meta[key]]);
  }

  if (metaRows.length) {
    children.push(
      new Table({
        width: { size: 80, type: WidthType.PERCENTAGE },
        alignment: AlignmentType.CENTER,
        rows: metaRows.map(([lbl, val], idx) =>
          new TableRow({
            children: [
              new TableCell({
                width: { size: 30, type: WidthType.PERCENTAGE },
                shading: { type: ShadingType.CLEAR, fill: idx % 2 === 0 ? "FFFFFF" : "F9FAFB" },
                borders: thinBorders("DDDDDD"),
                children: [new Paragraph({
                  alignment: AlignmentType.RIGHT,
                  spacing: { before: 40, after: 40 },
                  children: [new TextRun({ text: lbl, bold: true, color: DARK_BLUE, size: 20, font: "Arial" })],
                })],
              }),
              new TableCell({
                width: { size: 70, type: WidthType.PERCENTAGE },
                shading: { type: ShadingType.CLEAR, fill: idx % 2 === 0 ? "FFFFFF" : "F9FAFB" },
                borders: thinBorders("DDDDDD"),
                children: [new Paragraph({
                  spacing: { before: 40, after: 40 },
                  children: [new TextRun({ text: val, color: BODY_TEXT, size: 20, font: "Arial" })],
                })],
              }),
            ],
          })
        ),
      })
    );
  }

  // Spacers + confidential
  children.push(new Paragraph({ spacing: { after: 400 } }));
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "CONFIDENTIAL", bold: true, color: ACCENT_RED, size: 24, font: "Arial" })],
  }));
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 100 },
    children: [new TextRun({
      text: "This document contains proprietary information of BioNexus GmbH.\nDistribution is restricted to authorized personnel and review partners.",
      color: MUTED, size: 18, font: "Arial",
    })],
  }));

  // Page break
  children.push(new Paragraph({ children: [new PageBreak()] }));

  return children;
}

// ── Static TOC ─────────────────────────────────────────────────────────────

function buildToc(blocks) {
  const children = [];
  children.push(new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 200, after: 200 },
    children: [new TextRun({ text: "Table of Contents", bold: true, color: DARK_BLUE, size: 36, font: "Arial" })],
  }));

  let tocNum = 0;
  for (const b of blocks) {
    if (b.type === "heading" && (b.level === 1 || b.level === 2)) {
      tocNum++;
      const isH1 = b.level === 1;
      children.push(new Paragraph({
        spacing: { before: isH1 ? 80 : 20, after: 20 },
        indent: { left: isH1 ? 0 : 400 },
        children: [new TextRun({
          text: b.text,
          bold: isH1,
          color: isH1 ? DARK_BLUE : MED_BLUE,
          size: isH1 ? 22 : 20,
          font: "Arial",
        })],
      }));
    }
  }

  children.push(new Paragraph({ children: [new PageBreak()] }));
  return children;
}

// ── Table builder ──────────────────────────────────────────────────────────

function buildTable(rows) {
  if (!rows.length) return [];
  const ncols = Math.max(...rows.map(r => r.length));

  return [
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: rows.map((cells, ri) =>
        new TableRow({
          children: Array.from({ length: ncols }, (_, ci) => {
            const txt = stripLinks(cells[ci] || "");
            const isHeader = ri === 0;
            const fill = isHeader ? DARK_BLUE : (ri % 2 === 0 ? TBL_ALT : WHITE);
            const color = isHeader ? WHITE : BODY_TEXT;

            return new TableCell({
              shading: { type: ShadingType.CLEAR, fill },
              borders: thinBorders("C0C6D0"),
              children: [
                new Paragraph({
                  spacing: { before: 40, after: 40 },
                  children: isHeader
                    ? [new TextRun({ text: txt.replace(/\*\*/g, ""), bold: true, color, size: 19, font: "Arial" })]
                    : inlineRuns(txt, { color, size: 19 }),
                }),
              ],
            });
          }),
        })
      ),
    }),
    new Paragraph({ spacing: { after: 120 } }),
  ];
}

// ── Code block builder ─────────────────────────────────────────────────────

function buildCodeBlock(content) {
  return [
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [
        new TableRow({
          children: [
            new TableCell({
              shading: { type: ShadingType.CLEAR, fill: CODE_BG },
              borders: thinBorders(CODE_BORDER),
              children: [
                new Paragraph({
                  spacing: { before: 60, after: 60, line: 260 },
                  children: [new TextRun({
                    text: content,
                    font: "Courier New",
                    size: 16,
                    color: "1A1A2E",
                  })],
                }),
              ],
            }),
          ],
        }),
      ],
    }),
    new Paragraph({ spacing: { after: 100 } }),
  ];
}

// ── Border helpers ─────────────────────────────────────────────────────────

function noBorders() {
  const none = { style: BorderStyle.NONE, size: 0, color: WHITE };
  return { top: none, bottom: none, left: none, right: none };
}

function thinBorders(color) {
  const b = { style: BorderStyle.SINGLE, size: 1, color };
  return { top: b, bottom: b, left: b, right: b };
}

// ── Build full document ────────────────────────────────────────────────────

function buildDocx(mdText, fileName) {
  const title = extractTitle(mdText);
  const subtitle = extractSubtitle(mdText);
  const meta = extractMeta(mdText);
  const blocks = parseMd(mdText);

  // Skip front-matter blocks (everything before first ## heading with a number or first real heading)
  let startIdx = 0;
  for (let k = 0; k < blocks.length; k++) {
    if (blocks[k].type === "heading" && /^\d+\./.test(blocks[k].text)) {
      startIdx = k;
      break;
    }
    // If no numbered heading, start at first H2
    if (blocks[k].type === "heading" && blocks[k].level <= 2 &&
        k > 3 && blocks[k].text !== "Document Information" &&
        blocks[k].text !== "Table of Contents" &&
        !blocks[k].text.startsWith("BioNexus")) {
      startIdx = k;
      break;
    }
  }
  // Fallback: if we never found a good start, skip nothing
  if (startIdx === 0 && blocks.length > 10) {
    // Try to find first "## \d" or "## " that isn't meta
    for (let k = 0; k < blocks.length; k++) {
      if (blocks[k].type === "heading" && blocks[k].level === 2 &&
          !["Document Information", "Table of Contents"].includes(blocks[k].text) &&
          !blocks[k].text.startsWith("BioNexus")) {
        startIdx = k;
        break;
      }
    }
  }

  const contentBlocks = blocks.slice(startIdx);

  // Build cover
  const coverChildren = buildCover(title, subtitle, meta);
  // Build TOC
  const tocChildren = buildToc(contentBlocks);

  // Build body
  const bodyChildren = [];
  let firstH1 = true;

  for (const b of contentBlocks) {
    switch (b.type) {
      case "heading": {
        // Page break before H1 (except first one, since cover already has page break)
        // but after TOC the first H1 needs no extra break
        if (b.level === 1 && !firstH1) {
          bodyChildren.push(new Paragraph({ children: [new PageBreak()] }));
        }
        if (b.level === 1) firstH1 = false;

        const hLevel = [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2,
                         HeadingLevel.HEADING_3, HeadingLevel.HEADING_4][b.level - 1] || HeadingLevel.HEADING_4;
        const hSize = [36, 28, 24, 22][b.level - 1] || 22;
        const hColor = [DARK_BLUE, MED_BLUE, LIGHT_BLUE, MED_BLUE][b.level - 1] || MED_BLUE;
        const spaceBefore = [400, 300, 240, 200][b.level - 1] || 200;

        bodyChildren.push(new Paragraph({
          heading: hLevel,
          spacing: { before: spaceBefore, after: 120 },
          ...(b.level === 1 ? {
            border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: DARK_BLUE } },
          } : {}),
          children: [new TextRun({
            text: b.text, bold: true, color: hColor, size: hSize, font: "Arial",
          })],
        }));
        break;
      }

      case "paragraph":
        bodyChildren.push(new Paragraph({
          spacing: { before: 40, after: 80 },
          children: inlineRuns(stripLinks(b.text)),
        }));
        break;

      case "bullet":
        bodyChildren.push(new Paragraph({
          spacing: { before: 20, after: 20 },
          indent: { left: 400 + b.level * 300 },
          children: [
            new TextRun({ text: "•  ", color: DARK_BLUE, size: 20, font: "Arial" }),
            ...inlineRuns(stripLinks(b.text)),
          ],
        }));
        break;

      case "numbered":
        bodyChildren.push(new Paragraph({
          spacing: { before: 20, after: 20 },
          indent: { left: 400 },
          children: [
            new TextRun({ text: `${b.num}. `, bold: true, color: DARK_BLUE, size: 20, font: "Arial" }),
            ...inlineRuns(stripLinks(b.text)),
          ],
        }));
        break;

      case "checklist":
        bodyChildren.push(new Paragraph({
          spacing: { before: 20, after: 20 },
          indent: { left: 400 },
          children: [
            new TextRun({ text: "☐  ", color: LIGHT_BLUE, size: 22, font: "Arial" }),
            ...inlineRuns(stripLinks(b.text)),
          ],
        }));
        break;

      case "table":
        bodyChildren.push(...buildTable(b.rows));
        break;

      case "code":
        bodyChildren.push(...buildCodeBlock(b.content));
        break;
    }
  }

  // End block
  bodyChildren.push(new Paragraph({ spacing: { after: 300 } }));
  bodyChildren.push(
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [new TableRow({
        height: { value: 60, rule: "exact" },
        children: [new TableCell({
          shading: { type: ShadingType.CLEAR, fill: DARK_BLUE },
          borders: noBorders(),
          children: [new Paragraph("")],
        })],
      })],
    })
  );
  bodyChildren.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 200 },
    children: [new TextRun({
      text: `${meta.docId || "BioNexus"}  ·  ${meta.status || "Draft"}  ·  ${meta.date || "2026"}`,
      color: MUTED, size: 18, font: "Arial",
    })],
  }));
  bodyChildren.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 60 },
    children: [new TextRun({
      text: "© 2026 BioNexus GmbH — All rights reserved",
      color: MUTED, size: 18, font: "Arial",
    })],
  }));

  const doc = new Document({
    styles: {
      default: {
        document: {
          run: { font: "Arial", size: 20, color: BODY_TEXT },
          paragraph: { spacing: { line: 276 } },
        },
        heading1: {
          run: { font: "Arial", size: 36, bold: true, color: DARK_BLUE },
          paragraph: { spacing: { before: 400, after: 120 } },
        },
        heading2: {
          run: { font: "Arial", size: 28, bold: true, color: MED_BLUE },
          paragraph: { spacing: { before: 300, after: 100 } },
        },
        heading3: {
          run: { font: "Arial", size: 24, bold: true, color: LIGHT_BLUE },
          paragraph: { spacing: { before: 240, after: 80 } },
        },
        heading4: {
          run: { font: "Arial", size: 22, bold: true, color: MED_BLUE, italics: true },
          paragraph: { spacing: { before: 200, after: 60 } },
        },
      },
    },
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 }, // A4
          margin: { top: 1134, bottom: 1134, left: 1418, right: 1418 },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({
              text: `${title}`,
              italics: true, color: MUTED, size: 16, font: "Arial",
            })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({
              text: `${meta.docId || "BioNexus"}  ·  Confidential  ·  BioNexus GmbH`,
              color: MUTED, size: 16, font: "Arial",
            })],
          })],
        }),
      },
      children: [
        ...coverChildren,
        ...tocChildren,
        ...bodyChildren,
      ],
    }],
  });

  return doc;
}

// ── Google Drive ───────────────────────────────────────────────────────────

function getDriveAuth() {
  // Read .env manually
  const envPath = path.join(__dirname, "..", "orchestrator", ".env");
  const envText = fs.readFileSync(envPath, "utf-8");
  const env = {};
  for (const line of envText.split("\n")) {
    const m = line.match(/^([A-Z_]+)=(.+)/);
    if (m) env[m[1]] = m[2].trim();
  }

  const oauth2 = new google.auth.OAuth2(
    env.GOOGLE_CLIENT_ID,
    env.GOOGLE_CLIENT_SECRET,
  );
  oauth2.setCredentials({ refresh_token: env.GOOGLE_REFRESH_TOKEN });
  return oauth2;
}

async function listFilesInFolder(drive, folderId) {
  const res = await drive.files.list({
    q: `'${folderId}' in parents and trashed=false`,
    fields: "files(id, name, mimeType)",
    pageSize: 100,
  });
  return res.data.files || [];
}

async function deleteFile(drive, fileId, fileName) {
  try {
    await drive.files.delete({ fileId });
    console.log(`    ✗ Deleted old: ${fileName}`);
  } catch (e) {
    console.log(`    ! Could not delete ${fileName}: ${e.message}`);
  }
}

async function uploadFile(drive, localPath, folderId, displayName) {
  const mimeDocx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  const mimeGdoc = "application/vnd.google-apps.document";

  const res = await drive.files.create({
    requestBody: {
      name: displayName,
      parents: [folderId],
      mimeType: mimeGdoc, // Convert to Google Docs
    },
    media: {
      mimeType: mimeDocx,
      body: fs.createReadStream(localPath),
    },
    fields: "id, name, webViewLink",
  });

  return res.data;
}

// ── Display name mapping ───────────────────────────────────────────────────

const DISPLAY_NAMES = {
  "ADR_AI_EXTRACTION_SERVICE":   "ADR — AI Extraction Service",
  "API_REFERENCE":               "API Reference",
  "BIONEXUS_BOX_ARCHITECTURE":   "BioNexus Box — Hardware Gateway Architecture",
  "CUSTOMER_ONBOARDING_GUIDE":   "Customer Onboarding Guide",
  "DATA_RETENTION_DR_POLICY":    "Data Retention & DR Policy",
  "GCP_CLOUD_ARCHITECTURE":      "GCP Cloud Architecture",
  "GxP_COMPLIANCE_MASTER":       "GxP Compliance Master",
  "PRODUCT_ROADMAP":             "Product Roadmap",
  "SECURITY_ASSESSMENT_PLAYBOOK":"Security Assessment Playbook",
  "SYSTEM_VALIDATION_PLAN":      "System Validation Plan",
  "TIER2_AGENT_ARCHITECTURE":    "Tier 2 Agent Architecture",
};

// ── Main ───────────────────────────────────────────────────────────────────

async function main() {
  const localOnly = process.argv.includes("--local-only");

  console.log("");
  console.log("  ╔══════════════════════════════════════════════════════════╗");
  console.log("  ║  BioNexus Docs — Markdown → DOCX → Google Drive        ║");
  console.log("  ╚══════════════════════════════════════════════════════════╝");
  console.log("");

  // Ensure output dir
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR);

  // Find all .md files
  const mdFiles = fs.readdirSync(DOCS_DIR)
    .filter(f => f.endsWith(".md"))
    .sort();

  console.log(`  Found ${mdFiles.length} markdown files\n`);

  // ── Step 1: Convert all ──────────────────────────────────────────────
  console.log("  ── Step 1: Converting to DOCX ─────────────────────────\n");

  const converted = [];

  for (const mdFile of mdFiles) {
    const baseName = mdFile.replace(/\.md$/, "");
    const mdPath = path.join(DOCS_DIR, mdFile);
    const docxPath = path.join(OUT_DIR, baseName + ".docx");

    const mdText = fs.readFileSync(mdPath, "utf-8");
    const doc = buildDocx(mdText, mdFile);
    const buffer = await Packer.toBuffer(doc);
    fs.writeFileSync(docxPath, buffer);

    const sizeKB = Math.round(buffer.length / 1024);
    const displayName = DISPLAY_NAMES[baseName] || baseName;
    const folder = FILE_ROUTING[baseName] || "TECHNICAL";
    console.log(`    ✓ ${displayName.padEnd(45)} ${String(sizeKB).padStart(4)} KB  → ${folder}`);

    converted.push({ baseName, docxPath, displayName, folder });
  }

  console.log(`\n  All ${converted.length} files converted to ${OUT_DIR}\n`);

  if (localOnly) {
    console.log("  --local-only flag set, skipping upload.\n");
    return;
  }

  // ── Step 2: Upload to Drive ──────────────────────────────────────────
  console.log("  ── Step 2: Uploading to Google Drive ──────────────────\n");

  let auth;
  try {
    auth = getDriveAuth();
  } catch (e) {
    console.error("  ✗ Failed to read OAuth credentials:", e.message);
    process.exit(1);
  }

  const drive = google.drive({ version: "v3", auth });

  // Verify access
  try {
    const about = await drive.about.get({ fields: "user" });
    console.log(`    Authenticated as: ${about.data.user.emailAddress}\n`);
  } catch (e) {
    console.error("  ✗ Drive authentication failed:", e.message);
    process.exit(1);
  }

  // ── Step 2a: Delete old files with matching names ────────────────────
  console.log("  ── Cleaning old files... ──\n");

  const allFolderIds = Object.values(FOLDER_MAP);
  const existingFiles = {};
  for (const fid of allFolderIds) {
    const files = await listFilesInFolder(drive, fid);
    for (const f of files) existingFiles[f.id] = f;
  }

  for (const { baseName, displayName } of converted) {
    // Match by display name OR by base name (old raw markdown uploads)
    const matchNames = [
      displayName,
      displayName + ".docx",
      baseName,
      baseName + ".md",
      baseName + ".docx",
      baseName.replace(/_/g, " "),
    ].map(n => n.toLowerCase());

    for (const [fid, f] of Object.entries(existingFiles)) {
      if (matchNames.includes(f.name.toLowerCase()) ||
          matchNames.includes(f.name.replace(/\.docx$|\.md$/i, "").toLowerCase())) {
        await deleteFile(drive, fid, f.name);
        delete existingFiles[fid];
      }
    }
  }

  // ── Step 2b: Upload new files ────────────────────────────────────────
  console.log("\n  ── Uploading formatted documents... ──\n");

  for (const { baseName, docxPath, displayName, folder } of converted) {
    const folderId = FOLDER_MAP[folder];
    try {
      const result = await uploadFile(drive, docxPath, folderId, displayName);
      console.log(`    ✓ ${displayName}`);
      console.log(`      ${result.webViewLink}\n`);
    } catch (e) {
      console.error(`    ✗ ${displayName}: ${e.message}\n`);
    }
  }

  console.log("  ══════════════════════════════════════════════════════════");
  console.log("  ✓ All done! Check your Google Drive BioNexus/ folders.");
  console.log("  ══════════════════════════════════════════════════════════\n");
}

main().catch(e => { console.error("Fatal:", e); process.exit(1); });
