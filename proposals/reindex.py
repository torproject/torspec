#!/usr/bin/env python

import sys
if sys.version_info[0] < 3:
    print("No support for Python 2.")
    sys.exit(1)

import codecs, re, os
class Error(Exception): pass

STATUSES = """DRAFT NEEDS-REVISION NEEDS-RESEARCH OPEN ACCEPTED META FINISHED
   CLOSED SUPERSEDED DEAD REJECTED OBSOLETE RESERVE INFORMATIONAL""".split()
REQUIRED_FIELDS = [ "Filename", "Status", "Title"]
CONDITIONAL_FIELDS = { "OPEN" : [ "Target", "Ticket" ],
                       "ACCEPTED" : [ "Target", "Ticket" ],
                       "CLOSED" : [ "Implemented-In", "Ticket" ],
                       "FINISHED" : [ "Implemented-In", "Ticket" ] }
FNAME_RE = re.compile(r'^(\d\d\d)-.*[^\~]$')
DIR = "."
OUTFILE_TXT = "000-index.txt"
TMPFILE_TXT = OUTFILE_TXT+".tmp"

TEMPFILES = [TMPFILE_TXT]

def unlink_if_present(fname):
    try:
        os.unlink(fname)
    except OSError:
        pass

def indexed(seq):
    n = 0
    for i in seq:
        yield n, i
        n += 1

def readProposal(fn):
    fields = { }
    f = codecs.open(fn, 'r', encoding='utf-8')
    lastField = None
    try:
        for lineno, line in indexed(f):
            line = line.rstrip()
            if not line:
                return fields
            if line[0].isspace():
                fields[lastField] += " %s"%(line.strip())
            elif line == "```":
                pass
            else:
                parts = line.split(":", 1)
                if len(parts) != 2:
                    raise Error("%s:%s:  Neither field, continuation, nor ```."%
                                (fn,lineno))
                else:
                    fields[parts[0]] = parts[1].strip()
                    lastField = parts[0]

        return fields
    finally:
        f.close()

def getProposalNumber(fn):
    """Get the proposal's assigned number from its filename `fn`."""
    parts = fn.split('-', 1)

    assert len(parts) == 2, \
        "Filename must have a proposal number and title separated by a '-'"

    return int(parts[0])

def checkProposal(fn, fields):
    status = fields.get("Status")
    need_fields = REQUIRED_FIELDS + CONDITIONAL_FIELDS.get(status, [])

    number = getProposalNumber(fn)
    # Since prop#288 was the newest when we began requiring the 'Ticket:'
    # field, we don't require the field for it or any older proposal.
    # (Although you're encouraged to add it to your proposal, and add it for
    # older proposals where you know the correct ticket, as it greatly helps
    # newcomers find more information on the implementation.)
    if number <= 288:
        if "Ticket" in need_fields:
            need_fields.remove("Ticket")

    for f in need_fields:
        if f not in fields:
            raise Error("%s has no %s field"%(fn, f))
    if fn != fields['Filename']:
        raise Error("Mismatched Filename field in %s"%fn)
    if fields['Title'][-1] == '.':
        fields['Title'] = fields['Title'][:-1]

    status = fields['Status'] = status.upper()
    if status not in STATUSES:
        raise Error("I've never heard of status %s in %s"%(status,fn))
    if status in [ "SUPERSEDED", "DEAD" ]:
        for f in [ 'Implemented-In', 'Target' ]:
            if f in fields: del fields[f]

def readProposals():
    res = []
    for fn in os.listdir(DIR):
        m = FNAME_RE.match(fn)
        if not m: continue
        if fn.endswith(".tmp"):
            continue
        if not (fn.endswith(".txt") or fn.endswith(".md")):
            raise Error("%s doesn't end with .txt or .md"%fn)
        num = m.group(1)
        fields = readProposal(fn)
        checkProposal(fn, fields)
        fields['num'] = num
        res.append(fields)
    return res

def writeTextIndexFile(proposals):
    proposals.sort(key=lambda f:f['num'])
    seenStatuses = set()
    for p in proposals:
        seenStatuses.add(p['Status'])

    out = open(TMPFILE_TXT, 'w')
    inf = open(OUTFILE_TXT, 'r')
    for line in inf:
        out.write(line)
        if line.startswith("====="): break
    inf.close()

    out.write("Proposals by number:\n\n")
    for prop in proposals:
        out.write("%(num)s  %(Title)s [%(Status)s]\n"%prop)
    out.write("\n\nProposals by status:\n\n")
    for s in STATUSES:
        if s not in seenStatuses: continue
        out.write(" %s:\n"%s)
        for prop in proposals:
            if s == prop['Status']:
                out.write("   %(num)s  %(Title)s"%prop)
                if "Target" in prop:
                    out.write(" [for %(Target)s]"%prop)
                if "Implemented-In" in prop:
                    out.write(" [in %(Implemented-In)s]"%prop)
                out.write("\n")
    out.close()
    os.rename(TMPFILE_TXT, OUTFILE_TXT)

def formatMarkdownEntry(prop, withStatus=False):
    if withStatus:
        fmt = "* [`{Filename}`](/proposals/{Filename}): {Title} [{Status}]\n"
    else:
        fmt = "* [`{Filename}`](/proposals/{Filename}): {Title}\n"
    return fmt.format(**prop)

def writeMarkdownFile(prefix, format_inputs):
    template = prefix+"_template.md"
    output = prefix+".md"
    t = open(template).read()
    content = t.format(**format_inputs)
    with open(output, 'w') as f:
        f.write(content)

def writeMarkdownIndexFiles(proposals):
    markdown_files = [ "README", "INDEX" ]
    format_inputs = {}

    entries = []
    for prop in proposals:
        entries.append(formatMarkdownEntry(prop, withStatus=True))
    format_inputs["BY_INDEX"] = "".join(entries)

    for s in STATUSES:
        entries = []
        for prop in proposals:
            if s == prop['Status']:
                entries.append(formatMarkdownEntry(prop))
        if entries:
            format_inputs[s] = "".join(entries)
        else:
            format_inputs[s] = "(There are no proposals in this category)\n"

    entries = []
    for prop in proposals:
        if prop['Status'] in ('DEAD', 'REJECTED', 'OBSOLETE'):
            entries.append(formatMarkdownEntry(prop, withStatus=True))
    format_inputs['DEAD_REJECTED_OBSOLETE'] = "".join(entries)

    for prefix in markdown_files:
        writeMarkdownFile(prefix, format_inputs)

if __name__ == '__main__':
    proposals = readProposals()
    try:
        writeTextIndexFile(proposals)
        writeMarkdownIndexFiles(proposals)
    finally:
        for tempfile in TEMPFILES:
            unlink_if_present(tempfile)
