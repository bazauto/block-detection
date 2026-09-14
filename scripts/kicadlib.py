"""Minimal S-expression reader/writer plus KiCad symbol-library helpers.

Used by gen_schematic.py to pull *real* symbol definitions out of the installed
KiCad libraries instead of hand-rolling geometry, so the schematic carries
vetted pin numbering and graphics.
"""
import os
import re


class Q(str):
    """A string atom that was quoted in the source and must stay quoted."""


ESCAPES = {'n': '\n', 't': '\t', 'r': '\r'}


def tokenize(text):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in '()':
            yield c
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            i += 1
            buf = []
            while text[i] != '"':
                if text[i] == chr(92):
                    nxt = text[i + 1]
                    buf.append(ESCAPES.get(nxt, nxt))
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            i += 1
            yield Q(''.join(buf))
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()':
                j += 1
            yield text[i:j]
            i = j


def parse(text):
    """Parse the first top-level S-expression in `text`."""
    stack = [[]]
    for tok in tokenize(text):
        if tok == '(' and not isinstance(tok, Q):
            new = []
            stack[-1].append(new)
            stack.append(new)
        elif tok == ')' and not isinstance(tok, Q):
            stack.pop()
        else:
            stack[-1].append(tok)
    return stack[0][0]


_BARE = re.compile(r'^[A-Za-z0-9_.+*/%$#:@!?<>\[\]{}~^&|=,;-]+$')
_BS = chr(92)


def atom_str(a):
    if isinstance(a, Q):
        body = a.replace(_BS, _BS * 2).replace('"', _BS + '"')
        body = body.replace('\n', _BS + 'n').replace('\t', _BS + 't')
        body = body.replace('\r', _BS + 'r')
        return '"%s"' % body
    a = str(a)
    if a == '' or not _BARE.match(a):
        return '"%s"' % a
    return a


def dumps(node, indent=0, tab='\t'):
    """Serialize back to KiCad-style S-expression text."""
    if not isinstance(node, list):
        return atom_str(node)
    pad = tab * indent
    if not node:
        return pad + '()'
    rest = node[1:]
    if all(not isinstance(x, list) for x in rest):
        return pad + '(' + ' '.join(atom_str(x) for x in node) + ')'
    inline = []
    for x in rest:
        if isinstance(x, list):
            break
        inline.append(atom_str(x))
    line = pad + '(' + atom_str(node[0])
    if inline:
        line += ' ' + ' '.join(inline)
    out = [line]
    for x in rest[len(inline):]:
        out.append(dumps(x, indent + 1, tab))
    out.append(pad + ')')
    return '\n'.join(out)


def find(node, key):
    """First child list whose head is `key`."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def find_all(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def get_prop(sym, name):
    for p in find_all(sym, 'property'):
        if str(p[1]) == name:
            return str(p[2])
    return None


def deepcopy(node):
    if isinstance(node, list):
        return [deepcopy(x) for x in node]
    return node


class SymbolLibs:
    """Loads .kicad_sym libraries and resolves `extends` inheritance."""

    def __init__(self, root):
        self.root = root
        self._cache = {}

    def _lib(self, libname):
        if libname not in self._cache:
            path = os.path.join(self.root, libname + '.kicad_sym')
            with open(path, encoding='utf-8') as fh:
                tree = parse(fh.read())
            self._cache[libname] = {str(s[1]): s for s in find_all(tree, 'symbol')}
        return self._cache[libname]

    def raw(self, libname, symname):
        lib = self._lib(libname)
        if symname not in lib:
            raise KeyError('%s:%s not found' % (libname, symname))
        return lib[symname]

    def resolved(self, libname, symname, newname=None):
        """Flatten `extends` inheritance and rename the symbol (and its unit
        sub-symbols) to `newname`, default "libname:symname"."""
        sym = self.raw(libname, symname)
        ext = find(sym, 'extends')
        if ext is not None:
            parent = self.resolved(libname, str(ext[1]), newname='PH')
            body = [x for x in parent
                    if not (isinstance(x, list) and x and x[0] in ('property', 'extends'))]
            props = {}
            for p in find_all(parent, 'property'):
                props[str(p[1])] = deepcopy(p)
            for p in find_all(sym, 'property'):
                props[str(p[1])] = deepcopy(p)
            sym = body[:2] + list(props.values()) + body[2:]
        else:
            sym = deepcopy(sym)
            old = str(sym[1])
            for x in sym:
                if isinstance(x, list) and x and x[0] == 'symbol':
                    x[1] = Q('PH_' + str(x[1])[len(old) + 1:])
        name = newname if newname else '%s:%s' % (libname, symname)
        sym[1] = Q(name)
        # KiCad 10 keeps the library prefix on the top-level entry only; unit
        # sub-symbols carry the bare symbol name.
        short = name.split(':', 1)[-1]
        for x in sym:
            if isinstance(x, list) and x and x[0] == 'symbol':
                x[1] = Q(short + '_' + str(x[1])[3:])
        return sym


def unit_pins(sym):
    """Map {unit: {pin_number: (x, y, name, electrical_type)}} in lib coords."""
    out = {}
    for sub in find_all(sym, 'symbol'):
        m = re.search(r'_(\d+)_(\d+)$', str(sub[1]))
        if not m:
            continue
        slot = out.setdefault(int(m.group(1)), {})
        for pin in find_all(sub, 'pin'):
            at, num, nam = find(pin, 'at'), find(pin, 'number'), find(pin, 'name')
            if at is None or num is None:
                continue
            slot[str(num[1])] = (float(at[1]), float(at[2]),
                                 str(nam[1]) if nam else '', str(pin[1]))
    return out
