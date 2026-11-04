"""HTML/CSS for the Streamlit UI. Every dynamic value passes through esc():
plan text and model output are untrusted and are rendered with st.html."""
import html

STATUS_META = {
    "potential_conflict": ("Potential conflict", "conflict"),
    "evidence_found": ("Evidence found", "evidence"),
    "needs_information": ("Needs information", "needs"),
    "not_located": ("Not located", "notloc"),
}

CARD_DISCLAIMER = "Not legal advice or a compliance determination."


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
/* Inspection sheet: steel-grey ground, white work surfaces, status shown as
   equipment tags (ANSI Z535 / OSHA 1910.145 colors), one hi-vis barrier stripe. */
:root {
  --ground: #eef1f4; --surface: #ffffff; --surface-2: #f5f7f9; --ink: #121a22; --ink-2: #3b4753;
  --muted: #66727e; --line: #d9dfe5; --line-2: #c3ccd5; --band: #121a22; --band-ink: #f2f5f8; --band-muted: #93a1ae;
  --accent: #d9480f;
  --danger: #c92a2a; --danger-soft: #fff1f1; --danger-line: #ffc9c9;
  --caution: #fcc419; --caution-ink: #2b2100; --caution-soft: #fff9db; --caution-line: #ffe066;
  --safe: #2b8a3e; --safe-soft: #ebfbee; --safe-line: #b2f2bb;
  --neutral: #5f6b76; --neutral-soft: #f1f3f5; --neutral-line: #ced4da;
  --display: 'Archivo', 'Arial Narrow', Arial, sans-serif;
  --sans: 'IBM Plex Sans', 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif;
  --mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
html, body, [data-testid="stAppViewContainer"], .stApp { background: var(--ground) !important; }
.stApp, .stApp p, .stApp label, .stApp button, .stApp textarea { font-family: var(--sans) !important; }
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer, [data-testid="stDecoration"] { display: none !important; }
[data-testid="stMainBlockContainer"] { max-width: 1200px; padding-top: 1.25rem; padding-bottom: 4rem; }
[data-testid="stTextArea"] textarea { background: var(--surface) !important; border-radius: 8px !important; font-size: .92rem !important; line-height: 1.65 !important; }
[data-testid="stFileUploaderDropzone"] { background: var(--surface); border: 1.5px dashed var(--line-2); border-radius: 8px; }
.stButton > button, [data-testid^="stBaseButton"] { border-radius: 6px !important; font-weight: 600 !important; }

.cg-brand { display: flex; align-items: center; gap: 14px; padding: 14px 18px; background: var(--band); border-radius: 10px 10px 0 0;
  color: var(--band-ink); flex-wrap: wrap; }
.cg-stripe { height: 7px; border-radius: 0 0 10px 10px; margin-bottom: 18px;
  background: repeating-linear-gradient(-45deg, var(--accent) 0 12px, var(--band) 12px 24px); }
.cg-logo { flex: none; }
.cg-shield { width: 34px; height: 38px; background: var(--accent); color: #fff; display: grid; place-items: center; font-weight: 800;
  clip-path: polygon(50% 0, 100% 15%, 100% 55%, 50% 100%, 0 55%, 0 15%); }
.cg-name { font: 800 1.3rem/1.1 var(--display); letter-spacing: -0.01em; }
.cg-tag { color: var(--band-muted); font-size: .84rem; margin-top: 2px; }
.cg-mode { margin-left: auto; font: 500 .74rem/1 var(--mono); padding: 8px 11px; border-radius: 999px; border: 1px solid rgba(255,255,255,.2); white-space: nowrap; }
.cg-mode i { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 7px; vertical-align: 1px; }
.cg-mode--live i { background: #51cf66; } .cg-mode--stub i { background: var(--caution); }

.cg-steps { display: flex; gap: 6px; margin: 0 0 16px; flex-wrap: wrap; }
.cg-step { display: flex; align-items: center; gap: 8px; padding: 6px 12px 6px 6px; border-radius: 999px; font-size: .84rem;
  font-weight: 600; color: var(--muted); background: var(--surface); border: 1px solid var(--line); }
.cg-step b { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; font: 500 .72rem var(--mono);
  background: var(--surface-2); color: var(--muted); }
.cg-step--on { color: var(--ink); border-color: var(--ink); } .cg-step--on b { background: var(--ink); color: #fff; }
.cg-step--done b { background: var(--safe); color: #fff; }

.cg-panel { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 20px 22px; margin-bottom: 14px; }
.cg-h { font: 700 1.3rem/1.25 var(--display); color: var(--ink); margin: 0 0 6px; text-wrap: balance; }
.cg-p { color: var(--ink-2); font-size: .94rem; line-height: 1.6; margin: 0 0 10px; max-width: 70ch; }
.cg-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.cg-chip { font-size: .78rem; padding: 3px 9px; border-radius: 4px; background: var(--surface-2); color: var(--muted); border: 1px solid var(--line); }
.cg-chip--x { text-decoration: line-through; text-decoration-color: var(--line-2); }
.cg-eyebrow { font: 600 .7rem/1.3 var(--sans); letter-spacing: .09em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }
.cg-cite { text-transform: none; letter-spacing: 0; font: 500 .74rem var(--mono); color: var(--ink-2); }

.cg-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 6px 0 12px; }
.cg-stat { background: var(--surface-2); border-radius: 6px; padding: 10px 12px; }
.cg-stat b { display: block; font: 700 1.45rem/1.1 var(--display); color: var(--ink); font-variant-numeric: tabular-nums; }
.cg-stat span { font-size: .76rem; color: var(--muted); }
.cg-kv { font: .74rem/1.75 var(--mono); color: var(--muted); overflow-wrap: anywhere; }
.cg-kv b { color: var(--ink-2); font-weight: 500; }
.cg-ready, .cg-incomplete { font-size: .84rem; font-weight: 600; padding: 8px 10px; border-radius: 6px; margin-top: 12px; }
.cg-ready { background: var(--safe-soft); color: var(--safe); }
.cg-incomplete { background: var(--caution-soft); color: var(--ink); border: 1px solid var(--caution-line); }

.cg-banner { display: flex; gap: 14px; align-items: flex-start; border-radius: 8px; padding: 14px 16px; margin: 8px 0 12px; border: 1px solid; color: var(--ink); }
.cg-banner-icon { width: 30px; height: 30px; border-radius: 6px; display: grid; place-items: center; flex: none; font-weight: 800; }
.cg-banner-title { font: 800 1.02rem/1.3 var(--display); letter-spacing: .01em; }
.cg-banner-body { font-size: .9rem; margin-top: 3px; line-height: 1.5; }
.cg-banner ul { margin: 6px 0 0 18px; padding: 0; font-size: .85rem; }
.cg-banner--incomplete { background: var(--danger-soft); border-color: var(--danger-line); }
.cg-banner--incomplete .cg-banner-icon { background: var(--danger); color: #fff; } .cg-banner--incomplete .cg-banner-title { color: var(--danger); }
.cg-banner--open { background: var(--caution-soft); border-color: var(--caution-line); }
.cg-banner--open .cg-banner-icon { background: var(--caution); color: var(--caution-ink); }
.cg-banner--clean { background: var(--safe-soft); border-color: var(--safe-line); }
.cg-banner--clean .cg-banner-icon { background: var(--safe); color: #fff; }

.cg-tally { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }
.cg-tally > div { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; display: flex; align-items: center; gap: 10px; }
.cg-tally b { font: 800 1.6rem/1 var(--display); font-variant-numeric: tabular-nums; color: var(--ink); }
@media (max-width: 720px) { .cg-tally { grid-template-columns: repeat(2, minmax(0, 1fr)); } }

.cg-stamp { font: .72rem/1.8 var(--mono); color: var(--muted); background: var(--surface); border: 1px solid var(--line);
  border-radius: 8px; padding: 8px 12px; margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 2px 16px; overflow-wrap: anywhere; }
.cg-stamp b { color: var(--ink-2); font-weight: 500; }

.cg-card { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px 18px 12px; margin-bottom: 12px; }
.cg-card--invalid { border-color: var(--danger-line); box-shadow: 0 0 0 1px var(--danger-line); }
.cg-card-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.cg-id { font: 500 .74rem/1 var(--mono); color: var(--muted); }
.cg-badge { display: inline-flex; align-items: center; position: relative; font: 700 .72rem/1 var(--sans); letter-spacing: .04em;
  text-transform: uppercase; padding: 6px 10px 6px 21px; border-radius: 0 4px 4px 0; white-space: nowrap;
  clip-path: polygon(10px 0, 100% 0, 100% 100%, 10px 100%, 0 50%); }
.cg-badge::before { content: ""; position: absolute; left: 9px; top: 50%; width: 6px; height: 6px; margin-top: -3px; border-radius: 50%; background: var(--surface); }
.cg-badge--conflict { background: var(--danger); color: #fff; }
.cg-badge--evidence { background: var(--safe); color: #fff; }
.cg-badge--needs { background: var(--caution); color: var(--caution-ink); }
.cg-badge--notloc { background: var(--neutral); color: #fff; }
.cg-badge--invalid { background: var(--ink); color: #fff; }
.cg-q { font: 600 1rem/1.4 var(--sans); color: var(--ink); margin: 8px 0 12px; }
.cg-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 10px; }
@media (max-width: 860px) { .cg-grid { grid-template-columns: minmax(0, 1fr); } }
.cg-box { border-radius: 6px; padding: 11px 13px; font-size: .88rem; line-height: 1.55; min-width: 0; color: var(--ink); }
.cg-box--reg { background: var(--surface-2); color: var(--ink-2); }
.cg-box--conflict { background: var(--danger-soft); border: 1px solid var(--danger-line); }
.cg-box--evidence { background: var(--safe-soft); border: 1px solid var(--safe-line); }
.cg-box--needs { background: var(--caution-soft); border: 1px solid var(--caution-line); }
.cg-box--notloc { background: var(--neutral-soft); border: 1px dashed var(--neutral-line); }
.cg-quote { margin: 0; }
.cg-quote::before { content: '\\201C'; } .cg-quote::after { content: '\\201D'; }
.cg-meta { font: .7rem/1.6 var(--mono); color: var(--muted); margin-top: 8px; overflow-wrap: anywhere; }
.cg-meta a { color: var(--muted); }
.cg-nowrap { white-space: nowrap; }
.cg-interp { margin-top: 10px; font-size: .88rem; color: var(--ink-2); line-height: 1.55; }
.cg-interp b { color: var(--ink); }
.cg-fail { margin-top: 8px; background: var(--danger-soft); color: var(--danger); border: 1px solid var(--danger-line);
  border-radius: 6px; padding: 7px 10px; font-size: .84rem; font-weight: 600; }
.cg-card-foot { margin-top: 10px; padding-top: 9px; border-top: 1px solid var(--line); font-size: .74rem; color: var(--muted);
  display: flex; justify-content: space-between; gap: 6px 12px; flex-wrap: wrap; }
.cg-card-foot--bad { color: var(--danger); font-weight: 600; }

[data-testid="stLayoutWrapper"]:has(> .st-key-planview) { position: sticky; top: 16px; align-self: flex-start; }
.cg-planview { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px 18px; }
.cg-planview pre { white-space: pre-wrap; overflow-wrap: anywhere; font: .87rem/1.8 var(--sans); color: var(--ink-2); margin: 0; }
.cg-hl { border-radius: 3px; padding: 1px 2px; color: var(--ink); }
.cg-hl--potential_conflict { background: #ffe0e0; box-shadow: inset 0 -2px 0 var(--danger); }
.cg-hl--evidence_found { background: #d8f5df; box-shadow: inset 0 -2px 0 var(--safe); }
.cg-hl-tag { font: 600 .6rem/1 var(--mono); margin-left: 3px; color: var(--muted); }
.cg-legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: .75rem; color: var(--muted); margin-top: 12px; }
.cg-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }

.cg-stale { background: var(--caution-soft); color: var(--ink); border: 1px solid var(--caution-line); border-radius: 8px;
  padding: 12px 16px; font-size: .9rem; font-weight: 600; margin: 8px 0; }
.cg-footer { margin-top: 28px; padding-top: 14px; border-top: 1px solid var(--line); font-size: .78rem; color: var(--muted);
  display: flex; justify-content: space-between; gap: 8px 16px; flex-wrap: wrap; }
</style>
"""

LOGO_MARK = '<span class="cg-shield" aria-hidden="true">&#10003;</span>'


def brand_bar(live: bool, model_label: str) -> str:
    mode = (
        f'<div class="cg-mode cg-mode--live"><i></i>LIVE &middot; {esc(model_label)}</div>'
        if live
        else '<div class="cg-mode cg-mode--stub"><i></i>STUB MODE &middot; recorded JSON</div>'
    )
    return (
        f'<div class="cg-brand"><div class="cg-logo">{LOGO_MARK}</div>'
        '<div><div class="cg-name">ClauseGuard</div>'
        '<div class="cg-tag">Fall arrest plan precheck &middot; 29 CFR 1926.502 &amp; 1926.503</div></div>'
        f'{mode}</div><div class="cg-stripe"></div>'
    )


def stepper(current: int) -> str:
    labels = ["Confirm scenario", "Plan text", "Review"]
    out = []
    for i, label in enumerate(labels, start=1):
        cls = "cg-step--on" if i == current else ("cg-step--done" if i < current else "")
        mark = "&#10003;" if i < current else str(i)
        out.append(f'<div class="cg-step {cls}"><b>{mark}</b>{label}</div>')
    return f'<div class="cg-steps">{"".join(out)}</div>'


def scenario_panel() -> str:
    excluded = ["Guardrails", "Safety nets", "Covers", "Roofing alternatives", "§ 1926.502(k) fall protection plan"]
    chips = "".join(f'<span class="cg-chip cg-chip--x">{esc(x)}</span>' for x in excluded)
    return (
        '<div class="cg-panel"><div class="cg-eyebrow">Step 1 &middot; Applicability</div>'
        '<div class="cg-h">Does this plan use conventional personal fall arrest?</div>'
        '<p class="cg-p">ClauseGuard supports exactly one scenario: work protected by a <b>conventional personal '
        "fall arrest system</b> (body harness, connector, anchorage) on a construction site. All six checks apply "
        "by construction. Anything else stops here instead of producing a review that doesn't fit.</p>"
        f'<div class="cg-eyebrow" style="margin-top:12px">Not supported</div><div class="cg-chips">{chips}</div></div>'
    )


def unsupported_panel() -> str:
    return (
        '<div class="cg-banner cg-banner--incomplete"><div class="cg-banner-icon">!</div><div>'
        '<div class="cg-banner-title">This scenario is not supported</div>'
        '<div class="cg-banner-body">ClauseGuard only reviews conventional PFAS plans against its six checks. '
        "It has no applicability logic for guardrails, nets, covers, roofing alternatives, or a "
        "§ 1926.502(k) fall protection plan, so it stops rather than guessing.</div></div></div>"
    )


def preview_panel(lines: int, chars: int, source: str, plan_hash: str | None, ready: bool, min_chars: int) -> str:
    status = (
        '<div class="cg-ready">Ready to analyze</div>'
        if ready
        else f'<div class="cg-incomplete">INCOMPLETE &middot; paste at least {min_chars} characters</div>'
    )
    hash_row = f"<div><b>sha256</b> {esc(plan_hash[:16])}&hellip;</div>" if plan_hash else ""
    return (
        '<div class="cg-panel"><div class="cg-eyebrow">Extraction preview</div>'
        f'<div class="cg-stats"><div class="cg-stat"><b>{lines}</b><span>lines</span></div>'
        f'<div class="cg-stat"><b>{chars:,}</b><span>characters</span></div></div>'
        f'<div class="cg-kv"><div><b>source</b> {esc(source)}</div>{hash_row}</div>{status}</div>'
    )


def banner(kind: str, title: str, body: str, items: list[str] | None = None) -> str:
    icon = {"incomplete": "!", "open": "&#8226;", "clean": "&#10003;"}[kind]
    lis = "".join(f"<li>{esc(i)}</li>" for i in (items or []))
    return (
        f'<div class="cg-banner cg-banner--{kind}"><div class="cg-banner-icon">{icon}</div><div>'
        f'<div class="cg-banner-title">{esc(title)}</div><div class="cg-banner-body">{esc(body)}</div>'
        f'{f"<ul>{lis}</ul>" if lis else ""}</div></div>'
    )


def tally(counts: dict[str, int]) -> str:
    cells = []
    for status, (label, short) in STATUS_META.items():
        cells.append(
            f'<div><b>{counts.get(status, 0)}</b><span class="cg-badge cg-badge--{short}">{label}</span></div>'
        )
    return f'<div class="cg-tally">{"".join(cells)}</div>'


def stamp(plan_hash: str, index_version: str, model_id: str, schema_mode: str, ts: str) -> str:
    return (
        '<div class="cg-stamp">'
        f"<span><b>plan</b> sha256:{esc(plan_hash[:16])}&hellip;</span>"
        f"<span><b>index</b> {esc(index_version)}</span>"
        f"<span><b>model</b> {esc(model_id)}</span>"
        f"<span><b>schema</b> {esc(schema_mode)}</span>"
        f"<span><b>at</b> {esc(ts)}</span></div>"
    )


def check_card(check: dict, card, analyzed_lines: int, analyzed_chars: int) -> str:
    reg = (
        '<div class="cg-box cg-box--reg">'
        f'<div class="cg-eyebrow">Regulation &middot; <span class="cg-cite">{esc(check["cfr_paragraph"])}</span></div>'
        f'<p class="cg-quote">{esc(check["verbatim_text"])}</p>'
        f'<div class="cg-meta">pinned index &middot; <a href="{esc(check["ecfr_url"])}" target="_blank" '
        f'rel="noopener">eCFR</a> &middot; <span class="cg-nowrap">retrieved {esc(check["retrieval_date"])}</span> &middot; '
        f'sha256 {esc(check["sha256"][:12])}&hellip;</div></div>'
    )

    if card is None:
        return (
            f'<article class="cg-card cg-card--invalid"><div class="cg-card-head"><span class="cg-id">{esc(check["check_id"])}</span>'
            '<span class="cg-badge cg-badge--invalid">No result returned</span></div>'
            f'<div class="cg-q">{esc(check["question"])}</div><div class="cg-grid">{reg}'
            '<div class="cg-box cg-box--notloc"><div class="cg-eyebrow">Plan</div>The model returned no result for '
            "this check, so it is unreviewed.</div></div>"
            '<div class="cg-card-foot cg-card-foot--bad"><span>REVIEW INCOMPLETE &middot; rerun the analysis</span>'
            f"<span>{CARD_DISCLAIMER}</span></div></article>"
        )

    label, short = STATUS_META.get(card.status, ("Invalid status", "invalid"))
    if not card.valid:
        short_cls = "invalid"
    else:
        short_cls = short

    if card.status in ("potential_conflict", "evidence_found") and card.plan_span:
        plan = (
            f'<div class="cg-box cg-box--{short}"><div class="cg-eyebrow">Plan says</div>'
            f'<p class="cg-quote">{esc(card.plan_span)}</p></div>'
        )
    elif card.status == "not_located":
        plan = (
            '<div class="cg-box cg-box--notloc"><div class="cg-eyebrow">Plan</div>'
            f"<b>Not located in the supplied text ({analyzed_lines} lines, {analyzed_chars:,} characters).</b>"
            f'<div style="margin-top:8px"><b>What to add:</b> {esc(card.evidence_request)}</div></div>'
        )
    elif card.status == "needs_information":
        plan = (
            '<div class="cg-box cg-box--needs"><div class="cg-eyebrow">Needs information</div>'
            f"{esc(card.evidence_request)}</div>"
        )
    else:
        plan = (
            '<div class="cg-box cg-box--notloc"><div class="cg-eyebrow">Plan</div>'
            f"Returned status: <code>{esc(card.status)}</code></div>"
        )

    fails = "".join(f'<div class="cg-fail">Validation failure: {esc(e)}</div>' for e in card.errors)
    foot = (
        f'<div class="cg-card-foot"><span>Source matched; interpretation requires review.</span><span>{CARD_DISCLAIMER}</span></div>'
        if card.valid
        else '<div class="cg-card-foot cg-card-foot--bad"><span>Validation failed &middot; do not rely on this card</span>'
        f"<span>{CARD_DISCLAIMER}</span></div>"
    )
    badge = f'<span class="cg-badge cg-badge--{short_cls}">{esc(label)}</span>'
    return (
        f'<article class="cg-card cg-card--{short_cls}" data-check="{esc(check["check_id"])}">'
        f'<div class="cg-card-head"><span class="cg-id">{esc(check["check_id"])}</span>{badge}</div>'
        f'<div class="cg-q">{esc(check["question"])}</div>'
        f'<div class="cg-grid">{reg}{plan}</div>'
        f'<div class="cg-interp"><b>Model interpretation.</b> {esc(card.interpretation)}</div>'
        f"{fails}{foot}</article>"
    )


def plan_view(highlighted_html: str) -> str:
    return (
        '<div class="cg-planview"><div class="cg-eyebrow">Plan text &middot; quoted evidence</div>'
        f"<pre>{highlighted_html}</pre>"
        '<div class="cg-legend"><span><i style="background:#ffe0e0;box-shadow:inset 0 -2px 0 var(--danger)"></i>Potential conflict</span>'
        '<span><i style="background:#d8f5df;box-shadow:inset 0 -2px 0 var(--safe)"></i>Evidence found</span></div></div>'
    )


def stale_note(hidden: bool) -> str:
    style = ' style="display:none" data-start-hidden="1"' if hidden else ""
    return (
        f'<div id="cg-stale" class="cg-stale"{style}>Plan text changed, so the previous results were cleared. '
        "Run the analysis again.</div>"
    )


def footer(disclaimer: str) -> str:
    return (
        f'<div class="cg-footer"><span>{esc(disclaimer)}</span>'
        "<span>No accuracy figure is claimed. No safety professional has reviewed this output.</span></div>"
    )
