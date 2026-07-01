#!/usr/bin/env python3
# Единый build датасета SIMILIS. Заменяет data_prep + merge_novgu.
# Чистые одиночные снимки (приоритет search_result — реальные обработанные изображения),
# кроп к объекту + отсечение композитов, СТРОГАЯ типо-когерентность similarity (крест→кресты).
import openpyxl, os, glob, re, json, csv, collections
from PIL import Image
import numpy as np
Image.MAX_IMAGE_PIXELS = None

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTIMG = os.path.join(BASE, 'prototype', 'public', 'img')
OUTDATA = os.path.join(BASE, 'prototype', 'public', 'data')
os.makedirs(OUTIMG, exist_ok=True); os.makedirs(OUTDATA, exist_ok=True)
for f in glob.glob(OUTIMG+'/*.jpg'):
    try: os.remove(f)
    except: pass

def norm(c): return re.sub(r'\s+','',str(c or '')).upper()

# ── ARDB ──
wb = openpyxl.load_workbook(os.path.join(BASE,'ARDB_Описи_15_05_23.xlsx'), read_only=True, data_only=True)
ws = wb['Лист1']
COLS=['code','name','description','material','size','fragm','cultlayer','object','square','memo','memo1','survey','site','excname','longitude','latitude']
ardb={}
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[0] is None: break
    ardb[norm(r[0])]={COLS[i]:r[i] for i in range(min(len(COLS),len(r)))}

# ── data csv: hash -> subject/code/site ──
h2s={}
for r in csv.DictReader(open(os.path.join(BASE,'data-1716294635750.csv'))):
    h=os.path.splitext(r['image_title'])[0]
    if h not in h2s: h2s[h]={'subject':r['subject'],'code':r['inventory_code'],'site':r['site']}

SITE_MAP={'НЦ':('Ниеншанц (Охта 1)',30.408,59.945),'НЕЙШ':('Нейшлотский 3А',30.344,59.966),'НЕИШ':('Нейшлотский 3А',30.344,59.966),
          'БП':('Большая Посадская 12А',30.324,59.959),'Т':('Тульская (СПб)',30.30,59.90),'КБ':('Сытнинская (Козье Болото)',30.31,59.96),'ЗАГ':('Загородный',30.35,59.92)}
def site_of(code, ardb_site=None):
    if ardb_site and 'Охта' in str(ardb_site): return ('Ниеншанц (Охта 1)',30.408,59.945)
    if ardb_site and 'осадск' in str(ardb_site): return ('Большая Посадская 12А',30.324,59.959)
    u=re.sub(r'[^А-ЯA-Z]','',code.upper())
    for p,v in SITE_MAP.items():
        if u.startswith(p): return v
    return ('Ниеншанц (Охта 1)',30.408,59.945)

def macro_of(mat):
    m=(mat or '').lower()
    if 'металл' in m or 'бронз' in m or 'серебр' in m or 'свинец' in m: return 'Металл'
    if 'стекл' in m: return 'Стекло'
    if 'керамик' in m or 'глин' in m or 'фаянс' in m: return 'Керамика'
    if 'кост' in m or 'кож' in m or 'дерев' in m or 'янтар' in m or 'берест' in m: return 'Органика'
    return 'Прочее'

# ── crop to single object ──
def load_clean(path, target=720):
    im=Image.open(path).convert('RGB'); im.thumbnail((1500,1500))
    a=np.asarray(im.convert('L'))
    fg=a<235; ys,xs=np.where(fg)
    if len(xs)>30:
        x0,x1,y0,y1=xs.min(),xs.max(),ys.min(),ys.max()
        pw=int((x1-x0)*0.04)+2; ph=int((y1-y0)*0.04)+2
        im=im.crop((max(0,x0-pw),max(0,y0-ph),min(im.width,x1+pw),min(im.height,y1+ph)))
    w,h=im.size; ar=w/h
    if ar>1.55: im=im.crop((0,0,int(w*0.52),h))        # композит бок-о-бок → левый вид
    elif ar<0.5: im=im.crop((0,0,w,int(h*0.62)))       # вертикальный композит/линейка снизу → верх
    im.thumbnail((target,target))
    return im

def features(im):
    im2=im.convert('RGB').resize((96,96)); a=np.asarray(im2).astype(np.float32)/255.0
    lum=a.mean(2); fg=lum<0.92
    hsv=np.asarray(im.convert('HSV').resize((96,96))).astype(np.float32)
    m=fg.flatten()
    hf,sf,vf=hsv[:,:,0].flatten()[m],hsv[:,:,1].flatten()[m],hsv[:,:,2].flatten()[m]
    if len(hf)<10: hf,sf,vf=hsv[:,:,0].flatten(),hsv[:,:,1].flatten(),hsv[:,:,2].flatten()
    color=np.concatenate([np.histogram(hf,12,(0,255))[0],np.histogram(sf,6,(0,255))[0],np.histogram(vf,6,(0,255))[0]]).astype(np.float32)
    sil=(np.asarray(Image.fromarray((fg*255).astype(np.uint8)).resize((16,16))).astype(np.float32)/255).flatten()
    ys,xs=np.where(fg); ar=(xs.max()-xs.min()+1)/(ys.max()-ys.min()+1) if len(xs) else 1
    shape=np.concatenate([sil,[ar/3,fg.mean()]]).astype(np.float32)
    color/=np.linalg.norm(color)+1e-6; shape/=np.linalg.norm(shape)+1e-6
    return color,shape

items=[]; fc=[]; fs=[]
def add(imgpath, code, name, material, meta, type_label, owner=None):
    try: im=load_clean(imgpath)
    except Exception as e: return
    imid=re.sub(r'[^A-Za-zА-Яа-я0-9_-]','_',code)
    if any(it['id']==imid for it in items): return
    im.save(os.path.join(OUTIMG,imid+'.jpg'),'JPEG',quality=84)
    col,sh=features(im); fc.append(col); fs.append(sh)
    site,lon,lat=site_of(code, meta.get('site') if meta else None)
    items.append(dict(id=imid,code=code,name=name,material=material or (meta.get('material') if meta else '') or '—',
        description=(meta.get('description') if meta else '') or '', size=(meta.get('size') if meta else '') or '',
        square=(meta.get('square') if meta else '') or '', object=(meta.get('object') if meta else '') or '',
        excname=(meta.get('excname') if meta else '') or '', dating='',
        macro=macro_of(material or (meta.get('material') if meta else '')), type=type_label,
        site=site, owner=owner or 'ИИМК РАН', lon=lon, lat=lat, img='img/'+imid+'.jpg', external=False, in_ardb=bool(meta)))

# ── Источник A: search_result (чистые обработанные, приоритет) ──
seen_hash=set()
for f in glob.glob(os.path.join(BASE,'search_result_similis*','**','*.jpg'),recursive=True):
    h=os.path.splitext(os.path.basename(f))[0]
    if h in seen_hash: continue
    seen_hash.add(h)
    info=h2s.get(h)
    if not info: continue
    code=info['code']; meta=ardb.get(norm(code),{})
    name=meta.get('name') or info['subject']
    add(f, code, info['subject'] or name, meta.get('material'), meta, info['subject'] or name)

# ── Источник B: Validation (одиночные, по типу-папке), добираем объём ──
FOLDER=[('штоф','Штоф','Стекло'),('чашки','Чашка','Керамика'),('чернолощен_кувшины','Кувшин','Керамика'),
        ('чернил_бутыл_с_квадрат_дном','Чернильница','Стекло'),('черепица','Черепица','Глина'),
        ('янтарь','Изделие из янтаря','Янтарь'),('чернил_бутыл_с_8гран_туловом','Чернильница','Стекло')]
for folder,tname,mat in FOLDER:
    cnt=0
    for f in sorted(glob.glob(os.path.join(BASE,'Validation_dataset',folder,'*.jpg'))):
        if cnt>=11: break
        try:
            w,h=Image.open(f).size
            if not (0.5<=w/h<=1.35): continue     # только одиночные, не композиты
        except: continue
        code=os.path.splitext(os.path.basename(f))[0].split(' ')[0]
        meta=ardb.get(norm(code),{})
        add(f, code, (meta.get('name') or tname), (meta.get('material') or mat), meta, tname)
        cnt+=1

# ── Источник C: НовГУ (хотлинк миниатюр, тип=name) ──
nov=json.load(open(os.path.join(os.path.dirname(__file__),'novgu_finds.json'),encoding='utf-8'))
NCO={'Старая Русса':(31.36,57.99),'Пески':(31.30,57.98)}
nov_start=len(items)
for fnd in nov['finds']:
    s=str(fnd['id']); url=f'https://portal.novsu.ru/arc.novsu.ru/np-includes/upload/arc_small/{s[-3]}/{s[-2]}/{s[-1]}/{s}.png'
    lon,lat=NCO.get(fnd['site'],(31.36,57.99))
    items.append(dict(id='НГУ-'+s,code='НГУ-'+s,name=fnd['name'],material=fnd['material'],description=fnd['desc'],
        size='',square='',object='',excname='раскоп '+fnd['excav'] if fnd['excav'] else '',dating=fnd['dating'],
        macro=macro_of(fnd['material']),type=fnd['name'],site=fnd['site'],owner='НовГУ',lon=lon,lat=lat,
        img=url,external=True,in_ardb=False))
    fc.append(None); fs.append(None)

# ── СТРОГО типо-когерентный граф ──
def cos(a,b): return float(np.dot(a,b))
def build(feats):
    g={}
    for i,it in enumerate(items):
        same=[j for j,x in enumerate(items) if j!=i and x['type']==it['type']]
        # ранжируем по визуалу если есть фичи, иначе по материалу
        def key(j):
            if feats[i] is not None and feats[j] is not None: return -cos(feats[i],feats[j])
            return 0 if items[j]['material']==it['material'] else 1
        same.sort(key=key)
        neigh=same[:8]
        if len(neigh)<4:  # добор по макро
            extra=[j for j,x in enumerate(items) if j!=i and x['macro']==it['macro'] and j not in same]
            neigh=neigh+extra[:8-len(neigh)]
        n=len(neigh); out=[]
        for k,j in enumerate(neigh):
            sameType=items[j]['type']==it['type']
            score=round((0.98-0.30*(k/max(n-1,1))) if sameType else (0.70-0.05*k),2)
            out.append(dict(id=items[j]['id'],score=max(score,0.66)))
        g[it['id']]=out
    return g
graph={'resnet':build(fc),'clip':build(fs)}

# ── пресеты: только СИЛЬНЫЕ кластеры (≥6 объектов одного типа) → выдача строго того же типа ──
tcount=collections.Counter(it['type'] for it in items)
presets=[]
for want_type in ['Штоф','Чашка','Чернильница','Изделие из янтаря','Кувшин','Черепица']:
    cand=[it for it in items if it['type']==want_type]
    if cand and tcount[want_type]>=6: presets.append(cand[0]['id'])
    if len(presets)>=5: break
presets=presets[:5]

meta=dict(synthetic=False, n=len(items),
    note='Реальные изображения и метаданные SIMILIS (ИИМК РАН, НовГУ). Similarity — офлайн-прокси прод-эмбеддингов ResNet50/CLIP (иллюстрация). Изображения — обработанные одиночные снимки.',
    owners=sorted(set(i['owner'] for i in items)), sites=sorted(set(i['site'] for i in items)),
    presets=presets, novgu_source='portal.novsu.ru/archeology/db')
json.dump({'_meta':meta,'items':items}, open(os.path.join(OUTDATA,'catalog.json'),'w'), ensure_ascii=False, indent=1)
json.dump(graph, open(os.path.join(OUTDATA,'similarity_graph.json'),'w'), ensure_ascii=False)
# PII gate
blob=open(os.path.join(OUTDATA,'catalog.json'),encoding='utf-8').read()
assert not re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', blob), 'PII LEAK'
print('items',len(items),'| owners',meta['owners'],'| sites',len(meta['sites']))
print('types:',dict(collections.Counter(it['type'] for it in items)))
print('presets:',presets, '| PII OK')
