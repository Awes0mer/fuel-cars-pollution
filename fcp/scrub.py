"""Remove people's names from the author fields of downloaded Office files.

Official .xlsx files carry the names of the agency staff who saved them in
docProps/core.xml (dc:creator, cp:lastModifiedBy). This project keeps no
personal data, so those two fields are emptied. Every other part of the file
is copied unchanged, and the CRC-32 of each unchanged part is recorded so a
test can prove the data itself was not touched.

Usage: python -m fcp.scrub   (rewrites the .xlsx files in data/raw in place and
                             updates data/manifest.json)
"""

import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile

from fcp.fetch import MANIFEST, ROOT

SCRUBBED_PART = "docProps/core.xml"
# Author fields by namespace URI and local name, whatever prefix or attributes the file uses.
AUTHOR_FIELDS = {
    ("http://purl.org/dc/elements/1.1/", "creator"),
    ("http://schemas.openxmlformats.org/package/2006/metadata/core-properties", "lastModifiedBy"),
}


def _author_elements(root):
    for el in root.iter():
        if el.tag.startswith("{"):
            ns, local = el.tag[1:].split("}", 1)
            if (ns, local) in AUTHOR_FIELDS:
                yield el


def author_values(core_xml):
    """Non-empty author field values in a docProps/core.xml document."""
    return [el.text.strip() for el in _author_elements(ET.fromstring(core_xml)) if el.text and el.text.strip()]


# One token at a time: CDATA sections, comments and processing instructions are opaque,
# so text inside them is never read as a tag.
_TOKEN = re.compile(
    rb"<!\[CDATA\[.*?\]\]>|<!--.*?-->|<\?.*?\?>|<!DOCTYPE[^>]*>"
    rb"|<(/?)([A-Za-z_][\w.:-]*)((?:\s+[^\s=/>]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))*)\s*(/?)>",
    re.S)
_ATTR = re.compile(rb"([^\s=/>]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")


def _author_content_spans(core_xml):
    """Byte spans of the content of real author elements, resolved by namespace URI."""
    spans = []
    stack = []  # (qname, nsmap)
    nsmap = {}
    author_open = None  # (stack depth, content start)
    for m in _TOKEN.finditer(core_xml):
        if m.group(2) is None:  # CDATA, comment, PI or doctype
            continue
        closing, qname, attrs, selfclose = m.group(1), m.group(2), m.group(3) or b"", m.group(4)
        if closing:
            if stack:
                stack.pop()
                nsmap = stack[-1][1] if stack else {}
            if author_open and author_open[0] == len(stack):
                spans.append((author_open[1], m.start()))
                author_open = None
            continue
        scope = dict(nsmap)
        for name, v1, v2 in _ATTR.findall(attrs):
            value = (v1 or v2 or b"").decode("utf-8", "replace")
            if name == b"xmlns":
                scope[""] = value
            elif name.startswith(b"xmlns:"):
                scope[name[6:].decode()] = value
        prefix, _, local = qname.decode().rpartition(":")
        ns = scope.get(prefix, "")
        if selfclose:
            continue
        if author_open is None and (ns, local) in AUTHOR_FIELDS:
            author_open = (len(stack), m.end())
        stack.append((qname, scope))
        nsmap = scope
    return spans


def clear_authors(core_xml):
    """Empty the content of every real author element (dc:creator, cp:lastModifiedBy by
    namespace URI); everything else, including look-alike text in CDATA or comments and
    same-named elements in other namespaces, is left byte-for-byte as it was."""
    out = core_xml
    for a, b in sorted(_author_content_spans(core_xml), reverse=True):
        out = out[:a] + out[b:]
    if author_values(out):
        raise ValueError("author field left after scrubbing")
    return out


def scrub_bytes(data):
    """Return (new file bytes, {part: crc32 of the original part}) for an .xlsx file."""
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    crcs = {}
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            body = src.read(info.filename)
            crcs[info.filename] = info.CRC
            if info.filename == SCRUBBED_PART:
                body = clear_authors(body)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            dst.writestr(zi, body)
    return out.getvalue(), crcs


def has_author_names(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    if SCRUBBED_PART not in z.namelist():
        return False
    return bool(author_values(z.read(SCRUBBED_PART)))


def scrub_download(data, filename, entry):
    """Bytes to store for a fresh download; records the scrub in the manifest entry."""
    if not filename.endswith(".xlsx") or not has_author_names(data):
        return data
    new, crcs = scrub_bytes(data)
    entry["sha256_as_downloaded"] = hashlib.sha256(data).hexdigest()
    entry["bytes_as_downloaded"] = len(data)
    entry["scrubbed"] = "Author names removed from %s (dc:creator, cp:lastModifiedBy); all other parts unchanged." % SCRUBBED_PART
    entry["parts_crc32_as_downloaded"] = crcs
    return new


def scrub_entry(entry):
    """Scrub one manifest entry's file if it is an .xlsx with author names; update the entry."""
    import os

    path = os.path.join(ROOT, entry["path"])
    if not path.endswith(".xlsx"):
        return False
    with open(path, "rb") as f:
        data = f.read()
    if not has_author_names(data):
        return False
    new, crcs = scrub_bytes(data)
    with open(path, "wb") as f:
        f.write(new)
    entry.setdefault("sha256_as_downloaded", hashlib.sha256(data).hexdigest())
    entry.setdefault("bytes_as_downloaded", len(data))
    entry["scrubbed"] = "Author names removed from %s (dc:creator, cp:lastModifiedBy); all other parts unchanged." % SCRUBBED_PART
    entry["parts_crc32_as_downloaded"] = crcs
    entry["sha256"] = hashlib.sha256(new).hexdigest()
    entry["bytes"] = len(new)
    return True


def main():
    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)
    for e in manifest["files"]:
        if scrub_entry(e):
            print("scrubbed", e["path"])
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
