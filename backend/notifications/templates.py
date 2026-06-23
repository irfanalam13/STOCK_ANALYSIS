"""Alert message rendering: structured subject + HTML/text bodies.

A single ``AlertPayload`` is rendered into all representations a transport might
need. The HTML body is self-contained (inline styles) so it survives email
clients; the text body is the mandatory plain-text fallback.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AlertPayload:
    symbol: str
    company_name: str
    alert_type: str
    reason: str          # human-readable trigger explanation from the evaluator
    price: float
    change_percent: float
    volume: int
    timestamp: str       # ISO-8601 string
    label: str | None = None


def subject(p: AlertPayload) -> str:
    tag = f" [{p.label}]" if p.label else ""
    arrow = "▲" if p.change_percent >= 0 else "▼"
    return f"{arrow} {p.symbol} alert{tag}: {p.reason}"


def text_body(p: AlertPayload) -> str:
    """Plain-text fallback (required for non-HTML clients)."""
    return (
        f"NEPSE AI — Market Alert\n"
        f"========================\n\n"
        f"{p.company_name} ({p.symbol})\n"
        f"Condition: {p.reason}\n\n"
        f"Current price : NPR {p.price:,.2f}\n"
        f"Change        : {p.change_percent:+.2f}%\n"
        f"Volume        : {p.volume:,}\n"
        f"Triggered at  : {p.timestamp}\n\n"
        f"Alert type    : {p.alert_type}\n"
        f"--\nYou are receiving this because you set an alert on {p.symbol}.\n"
    )


def digest(rows: list[dict]) -> tuple[str, str, str]:
    """Render a daily digest from per-alert summary rows.

    Each row: {symbol, label, alert_type, condition, threshold_value,
    trigger_count, last_triggered_at}. Returns (subject, html, text).
    """
    subject = f"NEPSE AI — Daily alert digest ({len(rows)} active alert(s))"

    lines = ["NEPSE AI — Daily Alert Digest", "=============================", ""]
    for r in rows:
        label = f" [{r['label']}]" if r.get("label") else ""
        last = r.get("last_triggered_at") or "never"
        lines.append(
            f"- {r['symbol']}{label}: {r['alert_type']} "
            f"{r['condition']} {r['threshold_value']} "
            f"(triggered {r['trigger_count']}×, last: {last})"
        )
    text = "\n".join(lines) + "\n"

    items = "".join(
        f"<tr><td style='padding:6px 0'>{r['symbol']}"
        f"{(' <span style=color:#94a3b8>[' + r['label'] + ']</span>') if r.get('label') else ''}"
        f"</td><td style='padding:6px 0;color:#64748b'>{r['alert_type']} "
        f"{r['condition']} {r['threshold_value']}</td>"
        f"<td style='padding:6px 0;text-align:right'>{r['trigger_count']}×</td></tr>"
        for r in rows
    )
    html = f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;
            max-width:560px;margin:0 auto;border:1px solid #e5e7eb;
            border-radius:12px;overflow:hidden">
  <div style="background:#0f172a;color:#fff;padding:16px 20px">
    <div style="font-size:13px;letter-spacing:.08em;opacity:.7">NEPSE AI</div>
    <div style="font-size:18px;font-weight:600">Daily Alert Digest</div>
  </div>
  <div style="padding:20px">
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <tr style="border-bottom:1px solid #e5e7eb;color:#94a3b8;font-size:12px">
        <td style="padding:6px 0">Symbol</td><td>Condition</td>
        <td style="text-align:right">Triggers</td></tr>
      {items}
    </table>
  </div>
</div>"""
    return subject, html, text


def html_body(p: AlertPayload) -> str:
    """Self-contained HTML email (inline styles for client compatibility)."""
    color = "#16a34a" if p.change_percent >= 0 else "#dc2626"
    return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;
            max-width:520px;margin:0 auto;border:1px solid #e5e7eb;
            border-radius:12px;overflow:hidden">
  <div style="background:#0f172a;color:#fff;padding:16px 20px">
    <div style="font-size:13px;letter-spacing:.08em;opacity:.7">NEPSE AI</div>
    <div style="font-size:18px;font-weight:600">Market Alert Triggered</div>
  </div>
  <div style="padding:20px">
    <div style="font-size:20px;font-weight:700">{p.symbol}
      <span style="font-size:14px;font-weight:400;color:#64748b">
        {p.company_name}</span></div>
    <div style="margin:12px 0;padding:12px;background:#f8fafc;border-radius:8px;
                font-size:14px;color:#334155">{p.reason}</div>
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <tr><td style="padding:6px 0;color:#64748b">Current price</td>
          <td style="padding:6px 0;text-align:right;font-weight:600">
            NPR {p.price:,.2f}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b">Change</td>
          <td style="padding:6px 0;text-align:right;font-weight:600;
                     color:{color}">{p.change_percent:+.2f}%</td></tr>
      <tr><td style="padding:6px 0;color:#64748b">Volume</td>
          <td style="padding:6px 0;text-align:right;font-weight:600">
            {p.volume:,}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b">Triggered</td>
          <td style="padding:6px 0;text-align:right">{p.timestamp}</td></tr>
    </table>
  </div>
  <div style="padding:12px 20px;background:#f1f5f9;font-size:12px;color:#94a3b8">
    You set an alert on {p.symbol}. Manage alerts in your NEPSE AI dashboard.
  </div>
</div>"""
