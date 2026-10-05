import re
from datetime import datetime

import pandas as pd

COMPANY_SUFFIX = re.compile(
    r"^(.*?\b(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Limited|Ltd\.?|LLP|LLC|Inc\.?|Corp\.?))\s*(.*)$",
    re.I | re.S,
)


# ---------- helpers ----------
def split_sections(md: str) -> list[tuple[str, str]]:
    """Split markdown into [(heading, body)] on '#' headings."""
    sections, heading, buf = [], "_preamble", []
    for line in md.splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if m:
            sections.append((heading, "\n".join(buf).strip()))
            heading, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    sections.append((heading, "\n".join(buf).strip()))
    return sections


def parse_md_table(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or re.fullmatch(r"\|[\s:|\-]+\|", line):
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
    if not rows:
        return pd.DataFrame()
    header, body = rows[0], rows[1:]
    header = [snake(h) or "label" for h in header]
    return pd.DataFrame(body, columns=header)


def snake(s: str) -> str:
    s = s.strip().lower().replace("%", " pct")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def to_num(v):
    if not isinstance(v, str):
        return v
    s = re.sub(r"(INR|Rs\.?|₹|,|%)", "", v, flags=re.I).strip().rstrip(".")
    if s == "":
        return None
    try:
        f = float(s)
        return int(f) if re.fullmatch(r"-?\d+", s) else f
    except ValueError:
        return v


def numeric_cleanup(
    df: pd.DataFrame, skip=("description", "um", "label")
) -> pd.DataFrame:
    for col in df.columns:
        if col in skip:
            continue
        converted = df[col].map(to_num)
        # only accept if every non-empty cell became a number
        if all(isinstance(x, (int, float)) or x is None for x in converted):
            df[col] = converted
    return df


def parse_party(body: str) -> dict:
    """Name + address line, plus 'Key: value' lines (Tax Id, GSTIN, ...)."""
    out, text_lines = {}, []
    for line in filter(None, (l.strip() for l in body.splitlines())):
        m = re.match(r"^([A-Za-z][A-Za-z .]{1,25}):\s*(.+)$", line)
        if m:
            out[snake(m.group(1))] = m.group(2).strip()
        else:
            text_lines.append(line)
    blob = " ".join(text_lines)
    m = COMPANY_SUFFIX.match(blob)
    out["name"], out["address"] = (
        (m.group(1).strip(), m.group(2).strip()) if m else (None, blob)
    )
    return out


def parse_date(s: str, dayfirst=True):
    fmt = "%d/%m/%Y" if dayfirst else "%m/%d/%Y"
    try:
        return datetime.strptime(s, fmt).date().isoformat()
    except ValueError:
        return s


# ---------- main parser ----------
def parse_invoice_markdown(md: str, dayfirst: bool = True) -> dict[str, pd.DataFrame]:
    invoice_no = None
    m = re.search(r"Invoice\s*no\.?\s*:?\s*#?\s*([A-Za-z0-9\-/]+)", md, re.I)
    if m:
        invoice_no = m.group(1)

    date = None
    m = re.search(r"Date\s+of\s+issue\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", md, re.I)
    if m:
        date = parse_date(m.group(1), dayfirst)

    parties, tables = {}, {}
    for heading, body in split_sections(md):
        key = snake(heading)
        if "|" in body and key not in ("_preamble",):
            tables[key] = parse_md_table(body)
        elif key in ("seller", "client", "buyer", "bill_to", "ship_to", "vendor"):
            parties[key] = parse_party(body)

    header = {"invoice_no": invoice_no, "date_of_issue": date}
    for role, p in parties.items():
        for k, v in p.items():
            header[f"{role}_{k}"] = v

    result = {"invoice_header": pd.DataFrame([header])}
    for name, df in tables.items():
        df = numeric_cleanup(df)
        df.insert(0, "invoice_no", invoice_no)  # foreign key
        result[f"invoice_{name}"] = df
    return result


def validate(dfs: dict[str, pd.DataFrame]) -> list[str]:
    """Cross-check line items against the summary total."""
    issues = []
    items, summary = dfs.get("invoice_items"), dfs.get("invoice_summary")
    if items is None or summary is None:
        return ["items or summary table missing"]
    total = summary[summary["label"].str.lower() == "total"]
    if total.empty:
        return ["no 'Total' row in summary"]
    for col in ("net_worth", "gross_worth"):
        if col in items and col in total:
            if abs(items[col].sum() - total.iloc[0][col]) > 0.01:
                issues.append(
                    f"{col}: items={items[col].sum()} vs total={total.iloc[0][col]}"
                )
    return issues


# ---------- Docling wrapper ----------
def extract_invoice(file_path: str) -> dict[str, pd.DataFrame]:
    from docling.document_converter import DocumentConverter

    md = DocumentConverter().convert(file_path).document.export_to_markdown()
    return parse_invoice_markdown(md)


# ---------- optional: write to DB ----------
def save_to_db(dfs: dict[str, pd.DataFrame], conn_str: str):
    from sqlalchemy import create_engine

    engine = create_engine(conn_str)
    for table, df in dfs.items():
        df.to_sql(table, engine, if_exists="append", index=False)
