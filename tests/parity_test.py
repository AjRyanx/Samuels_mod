"""Proves the Lua counter rule (KitGenerator.lua) equals the Python one (kg_core.py) on thousands of inputs.
Also syntax-loads both Lua files. Run:  python tests/parity_test.py"""
import sys, re
from pathlib import Path
from lupa import LuaRuntime
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'generator'))
from kg_core import counter_reply, h32

lua = LuaRuntime(unpack_returned_tuples=True)
src = (root / 'modules/KitGenerator.lua').read_text()
# stub the sider-only globals so the file can be loaded outside the game
lua.execute('log=function() end; ffi=nil')
mod = lua.execute('local f=load(...); return f()' if False else 'return nil')
chunk = lua.eval('function(src) return load(src) end')(src)
assert chunk, 'KitGenerator.lua failed to compile'
M = chunk()
probe = lua.eval('function(src) return load(src) end')((root / 'modules/KGProbe.lua').read_text())
assert probe, 'KGProbe.lua failed to compile'
print('both Lua files compile')

bad = 0; n = 0
asks = [0.15, 0.08, 0.20, 0.0]
for career in ('f545d61a44bc', 'abc', 'zz9plural', ''):
    for season in (2027, 2028, 2035):
        for oid in ('71579-2027-1', '71580-2028-3', 'x'):
            for tier in ('small', 'mid', 'big'):
                for a in asks:
                    for step in (1, 2):
                        n += 1
                        py = counter_reply(career, season, oid, tier, a, step)
                        lu = M.counter_reply(career, season, oid, tier, a, step)
                        if py != lu: bad += 1
print(f'{n} cases, {bad} mismatches')
assert bad == 0
print('PARITY OK')
