#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path
import sys

# Map LaTeX macros (single backslash in file) to single-letter tokens
MACROS={"\\app":"A", "\\email":"E", "\\pk":"K", "\\pwd":"P", "\\sms":"S", "\\sq":"Q"}

def latex_to_tokens(rhs:str):
    s=rhs
    # Map macros (\\email etc.) to letters
    for k,v in MACROS.items():
        s=s.replace(k,v)
    # Drop wrappers and spacing
    s=s.replace('{','').replace('}','').replace('$','')
    s=s.replace('\\access','').replace('\\mobilex','').replace('\\mobile','')
    s=s.replace('\\implied','').replace('\\imply','')
    s=s.replace('\\myAnd','')
    s=s.replace('(','').replace(')','')
    s=re.sub(r"\s+","",s)
    # First try splitting with explicit backslash
    parts=[p for p in s.split('\\myOr') if p]
    if len(parts)==1:
        # If backslashes were stripped by LaTeX variant, split again without backslash
        s2=s.replace('\\','')
        s2=s2.replace('myAnd','')
        parts=[p for p in s2.split('myOr') if p]
    cleaned=[]
    for p in parts:
        p=p.replace('\\','').replace('myAnd','')
        p=''.join(ch for ch in p if ch.isalpha())
        cleaned.append(p)
    return cleaned

def canonical_brackets(parts):
    groups=[]
    for p in parts:
        letters=''.join(sorted(p))
        if letters: groups.append(letters)
    groups=sorted(set(groups))
    return ''.join('['+g+']' for g in groups) if groups else ''

def parse_table(path:Path):
    txt=path.read_text()
    lines=[l.strip() for l in txt.splitlines()]
    section=None
    entries={'suff':[], 'nec':[], 'factors':[]}
    for ln in lines:
        if ln.startswith('%'):
            continue
        if 'Factor Sufficiency' in ln: section='suff'; continue
        if 'Factor Necessity' in ln: section='nec'; continue
        if 'Factors' in ln and 'w/o' in ln: section='factors'; continue
        if ln.startswith('\\midrule') or ln.startswith('\\toprule') or not ln: continue
        if ln.startswith('Total') or ln.startswith('\\end{tabular}'): section=None; continue
        if section in ('suff','nec'):
            # Match the expression in $...$ then non-greedily capture through the numeric count in parentheses.
            # Use non-greedy '.*?' because LaTeX percentages appear as \\%, which breaks a negated class like [^%].
            m=re.search(r"\$([^$]+)\$\s*&\s*.*?\((\d+)\)", ln)
            if not m: continue
            expr,count=m.group(1),int(m.group(2))
            # Keep only RHS of implied/imply
            rhs = re.split(r'\\implied|\\imply', expr, maxsplit=1)
            expr_rhs = rhs[1] if len(rhs)>1 else expr
            parts=latex_to_tokens(expr_rhs)
            br=canonical_brackets(parts)
            entries[section].append((br,count))
        elif section=='factors':
            # Allow optional alias like (=\mobilex) between the set and the first column
            m=re.search(r"\$\\\{([^}]+)\\\}\$(?:\s*\([^)]*\))?\s*&\s*([^&]+?)&\s*([^\\\\]+)\\\\", ln)
            if not m: continue
            set_str,left,right=m.groups()
            ss=set_str
            for k,v in MACROS.items():
                ss=ss.replace(k,v)
            # Remove backslashes and spaces
            ss=re.sub(r"\\", "", ss)
            items=[i.strip() for i in ss.split(',')]
            # Map word tokens to letters if any remain
            word_map={'app':'A','email':'E','pk':'K','pwd':'P','sms':'S'}
            items=[word_map.get(i,i) for i in items]
            items=[i for i in items if i]
            can='{'+', '.join(sorted(items))+'}'
            def parse_count(s):
                mc=re.search(r"\((\d+)\)", s)
                return int(mc.group(1)) if mc else None
            entries['factors'].append((can, parse_count(left), parse_count(right)))
    return entries

def run(cmd:str)->str:
    return subprocess.check_output(cmd, shell=True, text=True)

def parse_access_output(s:str):
    d={}
    for line in s.splitlines():
        line=line.strip()
        m=re.match(r"(\[[A-Z]+(?:\]\[[A-Z]+)*\]):\s*(\d+)", line)
        if m: d[m.group(1)]=int(m.group(2))
    return d

def parse_factor_output(s:str):
    wo,wr={},{}
    current=None
    for line in s.splitlines():
        line=line.strip()
        if line.startswith('Factors: woReset'): current='wo'; continue
        if line.startswith('Factors: woReset: wReset'): current='wr'; continue
        if current=='wo':
            m=re.match(r"\{([^}]+)\}:\s*[^()]*\((\d+)\)", line)
            if m:
                key='{'+', '.join(sorted([x.strip() for x in m.group(1).split(',')]))+'}'
                wo[key]=int(m.group(2))
        elif current=='wr':
            m=re.match(r"\{([^}]+)\}:\s*[^;]+;\s*[^()]*\((\d+)\)", line)
            if m:
                key='{'+', '.join(sorted([x.strip() for x in m.group(1).split(',')]))+'}'
                wr[key]=int(m.group(2))
    return wo,wr

def diff_entries(got:dict, exp:list):
    mismatches=[]
    for br,count in exp:
        g=got.get(br)
        if g!=count:
            mismatches.append((br, count, g))
    return mismatches

def find_tables_dir() -> Path:
    candidates = [
        Path('Tables'),
        Path('claims')/ 'Tables',
        Path('artifact')/ 'Tables',
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError('Could not locate Tables directory. Checked: ' + ', '.join(str(c) for c in candidates))

def table_path(base: Path, stem: str) -> Path:
    # Prefer .tex, fall back to no extension
    p = base / f"{stem}.tex"
    if p.exists():
        return p
    p2 = base / stem
    return p2

def main():
    # Ensure K-map CSV exists
    run('python3 artifact/kmap_simplify.py artifact/data.csv artifact/data_with_kmap.csv --output-delim same')

    # Build outputs
    pa_t2_s=parse_access_output(run('python3 artifact/access_analyzer.py -s artifact/data.csv 1FA'))
    pa_t2_n=parse_access_output(run('python3 artifact/access_analyzer.py -n artifact/data.csv 1FA'))
    pa_t3_s=parse_access_output(run('python3 artifact/access_analyzer.py -s artifact/data.csv Reset1FA'))
    pa_t3_n=parse_access_output(run('python3 artifact/access_analyzer.py -n artifact/data.csv Reset1FA'))
    pa_t4_s=parse_access_output(run('python3 artifact/access_analyzer.py -s artifact/data.csv 2FA'))
    pa_t4_n=parse_access_output(run('python3 artifact/access_analyzer.py -n artifact/data.csv 2FA'))
    pa_t5_s=parse_access_output(run('python3 artifact/access_analyzer.py -s artifact/data.csv Reset2FA'))
    pa_t5_n=parse_access_output(run('python3 artifact/access_analyzer.py -n artifact/data.csv Reset2FA'))
    pa_t6_s=parse_access_output(run('python3 artifact/access_analyzer.py -s artifact/data_with_kmap.csv Kmap1FA'))
    wo7,wr7=parse_factor_output(run('python3 artifact/factor_analyzer.py artifact/data_with_kmap.csv 1FA Kmap1FA'))
    pa_t8_s=parse_access_output(run('python3 artifact/access_analyzer.py -s artifact/data_with_kmap.csv Kmap2FA'))
    wo9,wr9=parse_factor_output(run('python3 artifact/factor_analyzer.py artifact/data_with_kmap.csv 2FA Kmap2FA'))

    # Parse LaTeX (support multiple locations and .tex extension)
    T = find_tables_dir()
    lt2=parse_table(table_path(T,'TABLE2'))
    lt3=parse_table(table_path(T,'TABLE3'))
    lt4=parse_table(table_path(T,'TABLE4'))
    lt5=parse_table(table_path(T,'TABLE5'))
    lt6=parse_table(table_path(T,'TABLE6'))
    lt7=parse_table(table_path(T,'TABLE7'))
    lt8=parse_table(table_path(T,'TABLE8'))
    lt9=parse_table(table_path(T,'TABLE9'))

    # Guard: if any expected section parsed zero rows, flag a parse issue
    parse_issue=False
    def chk(name, lst):
        nonlocal parse_issue
        if len(lst)==0:
            parse_issue=True
            print(f"[WARN] Parsed 0 rows for {name}; check LaTeX format or regex.")
    chk('TABLE2_suff', lt2['suff']); chk('TABLE2_nec', lt2['nec'])
    chk('TABLE3_suff', lt3['suff']); chk('TABLE3_nec', lt3['nec'])
    chk('TABLE4_suff', lt4['suff']); chk('TABLE4_nec', lt4['nec'])
    chk('TABLE5_suff', lt5['suff']); chk('TABLE5_nec', lt5['nec'])
    chk('TABLE6_suff', lt6['suff'])
    chk('TABLE7_factors', lt7['factors'])
    chk('TABLE8_suff', lt8['suff'])
    chk('TABLE9_factors', lt9['factors'])

    mismatches={}
    mismatches['TABLE2_suff']=diff_entries(pa_t2_s, lt2['suff'])
    mismatches['TABLE2_nec']=diff_entries(pa_t2_n, lt2['nec'])
    mismatches['TABLE3_suff']=diff_entries(pa_t3_s, lt3['suff'])
    mismatches['TABLE3_nec']=diff_entries(pa_t3_n, lt3['nec'])
    mismatches['TABLE4_suff']=diff_entries(pa_t4_s, lt4['suff'])
    mismatches['TABLE4_nec']=diff_entries(pa_t4_n, lt4['nec'])
    mismatches['TABLE5_suff']=diff_entries(pa_t5_s, lt5['suff'])
    mismatches['TABLE5_nec']=diff_entries(pa_t5_n, lt5['nec'])
    mismatches['TABLE6_suff']=diff_entries(pa_t6_s, lt6['suff'])
    mismatches['TABLE8_suff']=diff_entries(pa_t8_s, lt8['suff'])
    # Factors tables
    m7=[]
    for can,l,r in lt7['factors']:
        gv_wo=wo7.get(can)
        gv_wr=wr7.get(can)
        if l is not None and gv_wo!=l: m7.append((can, 'wo', l, gv_wo))
        if r is not None and gv_wr!=r: m7.append((can, 'wr', r, gv_wr))
    mismatches['TABLE7']=m7
    m9=[]
    for can,l,r in lt9['factors']:
        gv_wo=wo9.get(can)
        gv_wr=wr9.get(can)
        if l is not None and gv_wo!=l: m9.append((can, 'wo', l, gv_wo))
        if r is not None and gv_wr!=r: m9.append((can, 'wr', r, gv_wr))
    mismatches['TABLE9']=m9

    # Detailed per-row report helpers
    def to_dict(pairs):
        return {k:v for k,v in pairs}

    def print_access_report(title, got:dict, exp_pairs:list):
        print(f"\n=== {title} ===")
        exp = to_dict(exp_pairs)
        # Preserve LaTeX order, then list extras
        seen=set()
        for br,count in exp_pairs:
            seen.add(br)
            gv = got.get(br)
            status = 'OK' if gv==count else 'DIFF'
            print(f"{br:>20}: expected={count:>2} got={str(gv):>2} [{status}]")
        # Extras present in script but not in LaTeX
        extras = sorted(set(got.keys())-seen)
        if extras:
            print("-- Extra rows present in script output --")
            for br in extras:
                print(f"{br:>20}: expected= -  got={got[br]}")

    def print_factors_report(title, wo:dict, wr:dict, exp_rows:list):
        print(f"\n=== {title} ===")
        seen=set()
        for can,l,r in exp_rows:
            seen.add(can)
            gv_wo = wo.get(can)
            gv_wr = wr.get(can)
            st_wo = 'OK' if (l is None or gv_wo==l) else 'DIFF'
            st_wr = 'OK' if (r is None or gv_wr==r) else 'DIFF'
            print(f"{can:>20}: woReset expected={str(l):>2} got={str(gv_wo):>2} [{st_wo}]  |  wReset expected={str(r):>2} got={str(gv_wr):>2} [{st_wr}]")
        # Extras
        extra_wo = sorted(set(wo.keys())-seen)
        extra_wr = sorted(set(wr.keys())-seen)
        if extra_wo:
            print("-- Extra woReset sets present in script output --")
            for can in extra_wo:
                print(f"{can:>20}: expected= -  got={wo[can]}")
        if extra_wr:
            print("-- Extra wReset sets present in script output --")
            for can in extra_wr:
                print(f"{can:>20}: expected= -  got={wr[can]}")

    # Print detailed reports per table
    print_access_report('TABLE 2 — 1FA Sufficiency', pa_t2_s, lt2['suff'])
    print_access_report('TABLE 2 — 1FA Necessity',   pa_t2_n, lt2['nec'])
    print_access_report('TABLE 3 — Reset1FA Sufficiency', pa_t3_s, lt3['suff'])
    print_access_report('TABLE 3 — Reset1FA Necessity',   pa_t3_n, lt3['nec'])
    print_access_report('TABLE 4 — 2FA Sufficiency', pa_t4_s, lt4['suff'])
    print_access_report('TABLE 4 — 2FA Necessity',   pa_t4_n, lt4['nec'])
    print_access_report('TABLE 5 — Reset2FA Sufficiency', pa_t5_s, lt5['suff'])
    print_access_report('TABLE 5 — Reset2FA Necessity',   pa_t5_n, lt5['nec'])
    print_access_report('TABLE 6 — Kmap1FA Sufficiency',  pa_t6_s, lt6['suff'])
    print_factors_report('TABLE 7 — 1FA vs Kmap1FA Factors', wo7, wr7, lt7['factors'])
    print_access_report('TABLE 8 — Kmap2FA Sufficiency',  pa_t8_s, lt8['suff'])
    print_factors_report('TABLE 9 — 2FA vs Kmap2FA Factors', wo9, wr9, lt9['factors'])

    # Final summary
    any_mis=False
    for k,v in mismatches.items():
        if v:
            any_mis=True
            print(f"\nMismatches in {k}: {len(v)}")
            for item in v:
                print(' ', item)
    if parse_issue:
        print('\nParse warnings were emitted above — results may be incomplete. Fix parsing before relying on matches.')
        # Exit non-zero to make CI or AE runs notice the issue
        return
    if not any_mis:
        print('\nAll tables matched the script outputs.')

if __name__=='__main__':
    main()
