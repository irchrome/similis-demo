#!/usr/bin/env python3
# Добавляет 14 реальных находок НовГУ (второй владелец) в catalog.json + similarity_graph.json.
# Изображения — хотлинк миниатюр НовГУ (arc_small) с fallback в UI. Similarity НовГУ — по материалу/типу.
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'public', 'data')
nov = json.load(open(os.path.join(HERE, 'novgu_finds.json'), encoding='utf-8'))
cat = json.load(open(os.path.join(DATA, 'catalog.json'), encoding='utf-8'))
graph = json.load(open(os.path.join(DATA, 'similarity_graph.json'), encoding='utf-8'))

SITE_COORD = {'Старая Русса': (31.36, 57.99), 'Пески': (31.30, 57.98)}
def macro_of(mat):
    if 'металл' in mat.lower(): return 'Металл'
    if 'Стекло' in mat: return 'Стекло'
    if 'Керамик' in mat or 'Глина' in mat: return 'Керамика'
    return 'Прочее'
def url_of(i):
    s = str(i); return f'https://portal.novsu.ru/arc.novsu.ru/np-includes/upload/arc_small/{s[-3]}/{s[-2]}/{s[-1]}/{s}.png'

nov_items = []
for f in nov['finds']:
    lon, lat = SITE_COORD.get(f['site'], (31.36, 57.99))
    nov_items.append(dict(
        id='НГУ-'+f['id'], code='НГУ-'+f['id'], name=f['name'], material=f['material'],
        description=f['desc'], size='', square='', object='', excname='раскоп '+f['excav'] if f['excav'] else '',
        cultlayer='', dating=f['dating'], macro=macro_of(f['material']), type=f['name'],
        site=f['site'], owner='НовГУ', lon=lon, lat=lat,
        img=url_of(f['id']), external=True, in_ardb=False))

# similarity НовГУ: соседи по материалу/типу (сначала НовГУ, потом ИИМК того же macro)
all_items = cat['items'] + nov_items
def neigh_for(it):
    same = [x for x in all_items if x['id'] != it['id'] and x['macro'] == it['macro']]
    # приоритет: тот же material, тот же owner
    same.sort(key=lambda x: (x['material'] != it['material'], x['owner'] != it['owner']))
    top = same[:8]
    n = len(top)
    return [dict(id=x['id'], score=round(0.95 - 0.30*(k/(max(n-1,1))), 2)) for k, x in enumerate(top)]
for it in nov_items:
    nb = neigh_for(it)
    graph['resnet'][it['id']] = nb
    graph['clip'][it['id']] = nb

cat['items'] = all_items
cat['_meta']['n'] = len(all_items)
cat['_meta']['owners'] = sorted(set(i['owner'] for i in all_items))
cat['_meta']['sites'] = sorted(set(i['site'] for i in all_items))
# добавить НовГУ-пресет (Крест или Змеевик)
pres = cat['_meta'].get('presets', [])
for want in ['НГУ-29100', 'НГУ-16313', 'НГУ-10889']:
    if any(x['id'] == want for x in nov_items): pres.append(want); break
cat['_meta']['presets'] = pres[:6]
cat['_meta']['novgu_source'] = 'portal.novsu.ru/archeology/db — Средневековые древности Новгородской земли'

json.dump(cat, open(os.path.join(DATA, 'catalog.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(graph, open(os.path.join(DATA, 'similarity_graph.json'), 'w'), ensure_ascii=False)

# PII gate
blob = open(os.path.join(DATA, 'catalog.json'), encoding='utf-8').read()
assert not re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', blob), 'PII LEAK'
print('merged: total', len(all_items), '| owners', cat['_meta']['owners'], '| sites', cat['_meta']['sites'])
print('presets', cat['_meta']['presets'])
print('PII gate OK')
