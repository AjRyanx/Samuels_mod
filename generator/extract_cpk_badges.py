import sys, os, io
from PIL import Image
pes_tools_path = r'C:\Users\User\.gemini\antigravity-cli\brain\801e151f-01cb-4bed-af83-cdf704b25fa6\scratch\pes-file-tools\lib'
sys.path.insert(0, pes_tools_path)
import pes_file_tools.cpk as cpk

reader = cpk.CpkReader()
reader.open(r'Data\dt15_x64.cpk')
file_map = {f.name: f for f in reader.files}

targets = {
    109: 'Real_Madrid',
    116: 'Ajax',
    119: 'Inter_Milan',
    121: 'AC_Milan',
    125: 'AS_Roma',
    131: 'Celtic',
    138: 'River_Plate',
    139: 'Boca_Juniors',
    179: 'Tottenham'
}

dest_dirs = [
    r'mods\Dynamic_Kit_and_Sponsor_mod_pes21\content\KitGenerator\badges',
    r'SiderAddons\content\KitGenerator\badges',
    r'C:\Users\User\.gemini\antigravity\brain\0dd829c3-5cd6-4f4d-ba1f-e2c598b3ed89'
]

for tid, name in targets.items():
    key = f'common/render/symbol/flag/e_000{tid}_r_ll.png'
    if key in file_map:
        data = reader.readFile(file_map[key])
        img = Image.open(io.BytesIO(data)).convert('RGBA')
        print(f'{name} (ID {tid}): {key} -> size={img.size}, bbox={img.getbbox()}')
        for d in dest_dirs:
            os.makedirs(d, exist_ok=True)
            if 'brain' in d:
                out_p = os.path.join(d, f'official_{tid}_{name}.png')
            else:
                out_p = os.path.join(d, f'{tid}.png')
            img.save(out_p)
            print(f'  saved {out_p}')
    else:
        print(f'MISSING {key}!')

reader.close()
