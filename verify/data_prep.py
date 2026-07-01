#!/usr/bin/env python3
# P0 data-prep для мока SIMILIS. Джойн реальных изображений (Validation_dataset, имя файла=код)
# с метаданными ARDB, реальные визуальные признаки (2 набора: color→resnet-proxy, shape→clip-proxy),
# offline KNN-граф похожести, ресайз картинок. Детерминированно.
import openpyxl, os, glob, re, json, math
from PIL import Image
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../similis
VD = os.path.join(BASE, 'Validation_dataset')
OUTIMG = os.path.join(BASE, 'prototype', 'public', 'img')
OUTDATA = os.path.join(BASE, 'prototype', 'public', 'data')

def norm(c): return re.sub(r'\s+','',str(c or '')).upper()

# ── ARDB index ──
wb = openpyxl.load_workbook(os.path.join(BASE,'ARDB_Описи_15_05_23.xlsx'), read_only=True, data_only=True)
ws = wb['Лист1']
COLS = ['code','name','description','material','size','fragm','cultlayer','object','square','memo','memo1','survey','site','excname','longitude','latitude']
ardb = {}
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[0] is None: break
    ardb[norm(r[0])] = {COLS[i]: r[i] for i in range(min(len(COLS),len(r)))}

# ── тип-папка → макро-категория + материал (по смыслу) ──
FOLDER_META = {
 'штоф': ('Штоф','Стекло','Стекло'),
 'чашки': ('Чашка','Керамика','Керамика'),
 'чернолощен_кувшины': ('Кувшин чернолощёный','Керамика','Керамика'),
 'чернил_бутыл_с_квадрат_дном': ('Чернильница','Стекло','Стекло'),
 'чернил_бутыл_с_8гран_туловом': ('Чернильница','Стекло','Стекло'),
 'черепица': ('Черепица','Керамика','Глина'),
 'янтарь': ('Изделие из янтаря','Прочее','Янтарь'),
 'чешуя_киверная': ('Чешуя киверная','Металл','Металл'),
}
# сайт: сперва из ARDB site, иначе префикс кода
def site_of(code, ardb_site=None):
    if ardb_site:
        z=str(ardb_site)
        if 'Охта' in z: return ('Ниеншанц (Охта 1)','ИИМК РАН',30.408,59.945)
        if 'осадск' in z: return ('Большая Посадская 12А','ИИМК РАН',30.324,59.959)
        if 'ейшлот' in z or 'Нейш' in z: return ('Нейшлотский 3А','ИИМК РАН',30.344,59.966)
    u=re.sub(r'[^А-ЯA-Z0-9]','',code.upper())
    if u.startswith('НЕЙШ') or u.startswith('НЕИШ'): return ('Нейшлотский 3А','ИИМК РАН',30.344,59.966)
    if u.startswith('БП'): return ('Большая Посадская 12А','ИИМК РАН',30.324,59.959)
    if u.startswith('Т'): return ('Тульская (СПб)','ИИМК РАН',30.36,59.93)
    return ('Ниеншанц (Охта 1)','ИИМК РАН',30.408,59.945)

# ── отбор ~60 картинок, предпочитая joined ──
selected = []
per_folder_cap = 12
for folder, (tname, macro, mat) in FOLDER_META.items():
    d = os.path.join(VD, folder)
    imgs = sorted(glob.glob(d+'/*.jpg'))
    joined = [f for f in imgs if norm(os.path.splitext(os.path.basename(f))[0].split(' ')[0]) in ardb]
    pick = (joined + [f for f in imgs if f not in joined])[:per_folder_cap]
    for f in pick:
        code_raw = os.path.splitext(os.path.basename(f))[0].split(' ')[0]
        selected.append((f, code_raw, folder, tname, macro, mat))
    if len(selected) >= 64: pass
print('selected', len(selected))

# ── визуальные признаки ──
def features(path):
    im = Image.open(path).convert('RGB').resize((96,96))
    a = np.asarray(im).astype(np.float32)/255.0
    # foreground mask (non-white)
    lum = a.mean(axis=2)
    fg = lum < 0.92
    # COLOR feature (resnet-proxy): HSV hist over foreground
    hsv = np.asarray(Image.open(path).convert('HSV').resize((96,96))).astype(np.float32)
    h,s,v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
    m = fg.flatten()
    hf,sf,vf = h.flatten()[m], s.flatten()[m], v.flatten()[m]
    if len(hf)<10: hf,sf,vf = h.flatten(),s.flatten(),v.flatten()
    ch = np.histogram(hf,bins=12,range=(0,255))[0]
    cs = np.histogram(sf,bins=6,range=(0,255))[0]
    cv = np.histogram(vf,bins=6,range=(0,255))[0]
    color = np.concatenate([ch,cs,cv]).astype(np.float32); color/= (color.sum()+1e-6)
    # SHAPE feature (clip-proxy): downsampled silhouette 16x16 + aspect + fill
    sil = Image.fromarray((fg*255).astype(np.uint8)).resize((16,16))
    silv = (np.asarray(sil).astype(np.float32)/255.0).flatten()
    ys,xs = np.where(fg)
    if len(xs)>0:
        aspect = (xs.max()-xs.min()+1)/(ys.max()-ys.min()+1)
        fill = fg.mean()
    else: aspect,fill = 1.0,0.0
    shape = np.concatenate([silv,[aspect/3.0, fill]]).astype(np.float32)
    shape /= (np.linalg.norm(shape)+1e-6)
    color /= (np.linalg.norm(color)+1e-6)
    return color, shape

items = []
feats_color, feats_shape = [], []
os.makedirs(OUTIMG, exist_ok=True); os.makedirs(OUTDATA, exist_ok=True)
for f, code_raw, folder, tname, macro, mat in selected:
    ncode = norm(code_raw)
    meta = ardb.get(ncode, {})
    site,owner,lon,lat = site_of(code_raw, meta.get('site'))
    name = meta.get('name') or tname
    material = meta.get('material') or mat
    col,sh = features(f)
    feats_color.append(col); feats_shape.append(sh)
    # resize + save
    imid = re.sub(r'[^A-Za-zА-Яа-я0-9_-]','_', code_raw)
    im = Image.open(f).convert('RGB')
    im.thumbnail((800,800))
    im.save(os.path.join(OUTIMG, imid+'.jpg'), 'JPEG', quality=82)
    items.append(dict(id=imid, code=code_raw, name=name, material=material,
        description=(meta.get('description') or ''), size=(meta.get('size') or ''),
        square=(meta.get('square') or ''), object=(meta.get('object') or ''),
        excname=(meta.get('excname') or ''), cultlayer=(meta.get('cultlayer') or ''),
        macro=macro, type=tname, site=site, owner=owner, lon=lon, lat=lat,
        img='img/'+imid+'.jpg', in_ardb=(ncode in ardb)))

C = np.array(feats_color); S = np.array(feats_shape)
def knn(F):
    sim = F @ F.T
    g = {}
    for i,it in enumerate(items):
        order = np.argsort(-sim[i])
        neigh = [j for j in order if j!=i][:8]
        # нормируем в отображаемый диапазон 0.66..0.99
        raw = np.array([sim[i][j] for j in neigh])
        if raw.max()>raw.min():
            disp = 0.66 + 0.33*(raw-raw.min())/(raw.max()-raw.min())
        else: disp = np.full(len(raw),0.9)
        g[items[i]['id']] = [dict(id=items[j]['id'], score=round(float(disp[k]),2)) for k,j in enumerate(neigh)]
    return g
graph = {'resnet': knn(C), 'clip': knn(S)}

# пресеты запроса — по одному яркому из каждого макро-типа
presets, seen = [], set()
for it in items:
    if it['macro'] not in seen:
        presets.append(it['id']); seen.add(it['macro'])
presets = presets[:5]

json.dump({'_meta':{'synthetic':False,'note':'Real SIMILIS artifact images + ARDB metadata. Similarity is an offline visual-feature proxy of the production ResNet50/CLIP embeddings (illustrative).','n':len(items),'owners':sorted(set(i['owner'] for i in items)),'sites':sorted(set(i['site'] for i in items)),'presets':presets},'items':items}, open(os.path.join(OUTDATA,'catalog.json'),'w'), ensure_ascii=False, indent=1)
json.dump(graph, open(os.path.join(OUTDATA,'similarity_graph.json'),'w'), ensure_ascii=False)
print('wrote catalog.json n=',len(items),'| owners',sorted(set(i['owner'] for i in items)),'| sites',sorted(set(i['site'] for i in items)))
print('macro dist:', {m:sum(1 for i in items if i['macro']==m) for m in set(i['macro'] for i in items)})
print('in_ardb:', sum(1 for i in items if i['in_ardb']),'/',len(items))
print('presets:', presets)

# ── PII GATE (страховка по ревью Opus): в выходных данных не должно быть email ──
import re as _re
_blob=open(os.path.join(OUTDATA,'catalog.json'),encoding='utf-8').read()
_emails=_re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}', _blob)
assert not _emails, f'PII LEAK: emails in catalog.json: {_emails[:3]}'
print('PII gate: no emails in catalog.json — OK')
