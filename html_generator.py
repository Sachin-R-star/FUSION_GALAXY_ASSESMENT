"""
html_generator.py - Premium HTML Claim Report Generator

Generates a standalone, beautifully styled HTML claim report using Jinja2.
Includes responsive layout, dark/light modern palette, visual audit badges,
source comparison table, line items table, and mismatch analysis.
"""

from typing import Dict, Any
from jinja2 import Template
from claim_parser import ClaimData, format_currency, format_percent, NOT_AVAILABLE
from audit_engine import AuditReport, run_claim_audit

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claim Audit Report - {{ claim.formatted_claim_ref }}</title>
    <style>
        :root {
            --bg-main: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-purple: #a855f7;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --border-color: #334155;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
        }

        body {
            background-color: var(--bg-main);
            color: var(--text-main);
            padding: 30px 20px;
            line-height: 1.5;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
        }

        /* Header Banner */
        .header {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e293b 100%);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }

        .header-title h1 {
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: #ffffff;
            margin-bottom: 6px;
        }

        .header-title p {
            color: var(--text-muted);
            font-size: 14px;
        }

        .header-badges {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .badge {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .badge-purple { background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }
        .badge-blue { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }
        .badge-rose { background: rgba(244, 63, 94, 0.2); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.4); }
        .badge-emerald { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
        .badge-amber { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }

        /* Status Alert Card */
        .status-alert {
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }
        .status-alert.critical {
            background: rgba(244, 63, 94, 0.12);
            border: 1px solid rgba(244, 63, 94, 0.35);
        }
        .status-alert.verified {
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.35);
        }
        .status-alert-content h3 {
            font-size: 18px;
            margin-bottom: 4px;
        }
        .status-alert.critical h3 { color: #f43f5e; }
        .status-alert.verified h3 { color: #10b981; }

        /* Card Section */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 12px;
        }

        .card-title {
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Key Value Grids */
        .kv-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }

        .kv-item {
            background: rgba(15, 23, 42, 0.6);
            padding: 14px 16px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .kv-label {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .kv-value {
            font-size: 15px;
            font-weight: 600;
            color: #f1f5f9;
            word-break: break-word;
        }

        .not-available {
            color: #64748b;
            font-style: italic;
            font-weight: 400;
        }

        /* Tables */
        .table-responsive {
            width: 100%;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 14px;
        }

        th {
            background-color: #0f172a;
            color: var(--text-muted);
            font-weight: 600;
            padding: 12px 14px;
            border-bottom: 2px solid var(--border-color);
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.6px;
        }

        td {
            padding: 12px 14px;
            border-bottom: 1px solid var(--border-color);
            color: #e2e8f0;
        }

        tbody tr:hover {
            background-color: rgba(255, 255, 255, 0.03);
        }

        .number-col {
            text-align: right;
            font-family: 'Consolas', 'Courier New', monospace;
        }

        .center-col {
            text-align: center;
        }

        /* Check cards / list */
        .check-item {
            background: rgba(15, 23, 42, 0.5);
            border-left: 4px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }
        .check-item.MISMATCH { border-left-color: var(--accent-rose); }
        .check-item.MATCH { border-left-color: var(--accent-emerald); }
        .check-item.INFO { border-left-color: var(--accent-blue); }

        .check-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .check-title {
            font-weight: 600;
            font-size: 15px;
        }

        .check-desc {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 6px;
        }

        .footer {
            text-align: center;
            padding: 24px;
            color: var(--text-muted);
            font-size: 12px;
            border-top: 1px solid var(--border-color);
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-title">
                <h1>Claim Audit Report: {{ claim.formatted_claim_ref }}</h1>
                <p>Comprehensive Insurance Claim Reconciliation & Line Item Analysis</p>
            </div>
            <div class="header-badges">
                <span class="badge badge-purple">Vehicle: {{ claim.formatted_vehicle }}</span>
                <span class="badge badge-blue">Loss Date: {{ claim.formatted_loss_date }}</span>
                <span class="badge badge-amber">Mode: {{ claim.formatted_payment_mode }}</span>
            </div>
        </div>

        <!-- Audit Alert Banner -->
        <div class="status-alert {% if audit.total_mismatches_count > 0 %}critical{% else %}verified{% endif %}">
            <div class="status-alert-content">
                <h3>Audit Status: {{ audit.overall_status }}</h3>
                <p>Identified {{ audit.total_mismatches_count }} total mismatch discrepancies and {{ audit.missing_fields_count }} null/missing data fields across sources.</p>
            </div>
            <div>
                {% if audit.total_mismatches_count > 0 %}
                <span class="badge badge-rose">{{ audit.total_mismatches_count }} Mismatches Found</span>
                {% else %}
                <span class="badge badge-emerald">Verified Consistent</span>
                {% endif %}
            </div>
        </div>

        <!-- Claim Summary Grid -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">📋 Claim Summary</div>
            </div>
            <div class="kv-grid">
                <div class="kv-item">
                    <div class="kv-label">Claim Reference</div>
                    <div class="kv-value">{{ claim.formatted_claim_ref }}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Vehicle Details</div>
                    <div class="kv-value">{{ claim.formatted_vehicle }}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Date of Loss</div>
                    <div class="kv-value">{{ claim.formatted_loss_date }}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Nature of Loss</div>
                    <div class="kv-value">{{ claim.formatted_nature_of_loss }}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Payment Mode</div>
                    <div class="kv-value">{{ claim.formatted_payment_mode }}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Vehicle Age Depreciation</div>
                    <div class="kv-value">{{ claim.parsed_estimate.vehicle_age_depreciation_pct | format_percent }}</div>
                </div>
            </div>
            <div style="margin-top: 16px;">
                <div class="kv-item">
                    <div class="kv-label">Loss Summary Description</div>
                    <div class="kv-value" style="font-weight: 400; color: #cbd5e1;">{{ claim.formatted_loss_summary }}</div>
                </div>
            </div>
            {% if claim.parsed_estimate.parsed_damage_parts_from_photos %}
            <div style="margin-top: 16px;">
                <div class="kv-label" style="margin-bottom: 8px;">Damage Parts Detected in Photos</div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    {% for photo in claim.parsed_estimate.parsed_damage_parts_from_photos %}
                    <span class="badge badge-blue">📷 {{ photo.parts_name }} ({{ photo.damage_type }})</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </div>

        <!-- Totals & Data Sources Comparison -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">📊 Claim Totals Reconciliation Across Data Sources</div>
            </div>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Total Description</th>
                            <th>Data Source</th>
                            <th class="number-col">Stated Amount (INR)</th>
                            <th>Audit Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for src in audit.sources_summary %}
                        <tr>
                            <td style="font-weight: 600;">{{ src.label }}</td>
                            <td style="color: var(--text-muted); font-size: 13px;">{{ src.source }}</td>
                            <td class="number-col" style="font-weight: 700; color: #38bdf8;">
                                {% if src.amount is none %}<span class="not-available">not available</span>{% else %}{{ src.formatted_amount }}{% endif %}
                            </td>
                            <td style="font-size: 13px; color: #cbd5e1;">{{ src.notes }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Discrepancy & Check Analysis -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">🔍 "Check" Section - Audit Discrepancy Log</div>
            </div>
            <div>
                {% for check in audit.checks %}
                <div class="check-item {{ check.status }}">
                    <div class="check-header">
                        <div class="check-title">
                            [{{ check.check_id }}] {{ check.title }}
                        </div>
                        <div>
                            {% if check.status == 'MISMATCH' %}
                            <span class="badge badge-rose">MISMATCH ({{ check.diff_percent | round(2) }}%)</span>
                            {% elif check.status == 'MATCH' %}
                            <span class="badge badge-emerald">MATCH</span>
                            {% else %}
                            <span class="badge badge-blue">INFO</span>
                            {% endif %}
                        </div>
                    </div>
                    <div style="font-size: 13px; display: flex; gap: 20px; color: #e2e8f0; margin-bottom: 6px;">
                        <span><strong>{{ check.source_a_label }}:</strong> {{ check.val_a | format_currency }}</span>
                        <span><strong>{{ check.source_b_label }}:</strong> {{ check.val_b | format_currency }}</span>
                        {% if check.diff_amount is not none and check.diff_amount > 0 %}
                        <span style="color: #fb7185;"><strong>Variance:</strong> {{ check.diff_amount | format_currency }}</span>
                        {% endif %}
                    </div>
                    <div class="check-desc">{{ check.description }}</div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Itemized Estimate Lines Table -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">🔧 Itemized Estimate Line Items</div>
                <span class="badge badge-blue">{{ claim.parsed_estimate.lines | length }} Line Items</span>
            </div>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th class="center-col">#</th>
                            <th>Part / Description</th>
                            <th>Type</th>
                            <th class="center-col">Qty</th>
                            <th class="number-col">Stated Unit/Base Amount</th>
                            <th class="center-col">Dep %</th>
                            <th class="center-col">GST %</th>
                            <th class="number-col">Calculated / Final Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for line in claim.parsed_estimate.lines %}
                        <tr>
                            <td class="center-col" style="color: var(--text-muted);">{{ loop.index }}</td>
                            <td style="font-weight: 600;">{{ line.part_name }}</td>
                            <td style="font-size: 12px; color: #94a3b8;">{{ line.part_type }}</td>
                            <td class="center-col">{{ line.formatted_quantity }}</td>
                            <td class="number-col">
                                {% if line.part_total is none %}<span class="not-available">not available</span>{% else %}{{ line.formatted_part_total }}{% endif %}
                            </td>
                            <td class="center-col">
                                {% if line.part_dep_perc is none %}<span class="not-available">not available</span>{% else %}{{ line.formatted_dep_perc }}{% endif %}
                            </td>
                            <td class="center-col">
                                {% if line.part_gst_perc is none %}<span class="not-available">not available</span>{% else %}{{ line.formatted_gst_perc }}{% endif %}
                            </td>
                            <td class="number-col" style="font-weight: 600; color: #34d399;">
                                {% if line.total_final_amt is not none %}
                                    {{ line.total_final_amt | format_currency }}
                                {% elif line.calculated_final_amt is not none %}
                                    {{ line.calculated_final_amt | format_currency }} <span style="font-size:10px; color:#94a3b8;">(calc)</span>
                                {% else %}
                                    <span class="not-available">not available</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="8" class="center-col not-available" style="padding: 20px;">No estimate line items recorded.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Generated by <strong>Claim Report Generator v1.0</strong> | Source Note: {{ claim.source_note }}</p>
            <p style="margin-top: 4px;">Notice: Black boxes in original estimate scans are intentional redactions. Numbers verified across multiple source records.</p>
        </div>
    </div>
</body>
</html>
"""

from jinja2 import Environment

def generate_html_report(claim: ClaimData, audit: AuditReport) -> str:
    """Renders HTML report string for given claim and audit report."""
    env = Environment()
    env.filters['format_currency'] = format_currency
    env.filters['format_percent'] = format_percent
    template = env.from_string(HTML_TEMPLATE)
    return template.render(claim=claim, audit=audit)
