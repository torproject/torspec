#!/usr/bin/python

import re, os
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
OUTFILE = "000-index.txt"
TMPFILE = OUTFILE+".tmp"

def indexed(seq):
    n = 0
    for i in seq:
        yield n, i
        n += 1

def readProposal(fn):
    fields = { }
    f = open(fn, 'r')
    lastField = None
    try:
        for lineno, line in indexed(f):
            line = line.rstrip()
            if not line:
                return fields
            if line[0].isspace():
                fields[lastField] += " %s"%(line.strip())
            else:
                parts = line.split(":", 1)
                if len(parts) != 2:
                    raise Error("%s:%s:  Neither field nor continuation"%
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
        if not fn.endswith(".txt"):
            raise Error("%s doesn't end with .txt"%fn)
        num = m.group(1)
        fields = readProposal(fn)
        checkProposal(fn, fields)
        fields['num'] = num
        res.append(fields)
    return res

def writeIndexFile(proposals):
    proposals.sort(key=lambda f:f['num'])
    seenStatuses = set()
    for p in proposals:
        seenStatuses.add(p['Status'])

    out = open(TMPFILE, 'w')
    inf = open(OUTFILE, 'r')
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
    os.rename(TMPFILE, OUTFILE)

try:
    os.unlink(TMPFILE)
except OSError:
    pass

writeIndexFile(readProposals())
