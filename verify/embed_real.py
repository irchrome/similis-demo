#!/usr/bin/env python3
# ОПЦИОНАЛЬНО, запускать ЛОКАЛЬНО на маке (в песочнице Cowork torch недоступен — прокси блокирует).
# Считает НАСТОЯЩИЕ эмбеддинги ResNet50 (ImageNet) + CLIP (ViT-B/32) по картинкам public/img/,
# строит KNN-граф и ПЕРЕЗАПИСЫВАЕТ public/data/similarity_graph.json реальными эмбеддингами.
# После этого честная плашка становится «real ResNet50 + CLIP embeddings, precomputed offline».
#
# Установка (на маке):
#   pip install torch torchvision open_clip_torch pillow numpy
# Запуск:
#   python3 embed_real.py
import os, json, numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'public', 'data')
IMG  = os.path.join(HERE, '..', 'public')
cat = json.load(open(os.path.join(DATA, 'catalog.json'), encoding='utf-8'))
items = cat['items']

def l2(x): return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-8)

# ── ResNet50 (torchvision), фичи с penultimate ──
import torch, torchvision
from torchvision import transforms
m = torchvision.models.resnet50(weights=torchvision.models.ResNet50_Weights.IMAGENET1K_V2)
m.fc = torch.nn.Identity(); m.eval()
tf = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224),
    transforms.ToTensor(), transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])])
res = []
with torch.no_grad():
    for it in items:
        im = Image.open(os.path.join(IMG, it['img'])).convert('RGB')
        res.append(m(tf(im).unsqueeze(0)).squeeze(0).numpy())
RES = l2(np.array(res))

# ── CLIP (open_clip ViT-B/32) ──
import open_clip
model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
model.eval()
clip = []
with torch.no_grad():
    for it in items:
        im = preprocess(Image.open(os.path.join(IMG, it['img'])).convert('RGB')).unsqueeze(0)
        clip.append(model.encode_image(im).squeeze(0).numpy())
CLIP = l2(np.array(clip))

def knn(F):
    sim = F @ F.T
    g = {}
    for i, it in enumerate(items):
        order = np.argsort(-sim[i])
        neigh = [j for j in order if j != i][:8]
        raw = np.array([sim[i][j] for j in neigh])
        disp = 0.66 + 0.33*(raw-raw.min())/(raw.max()-raw.min()+1e-9)
        g[it['id']] = [dict(id=items[j]['id'], score=round(float(disp[k]), 2)) for k, j in enumerate(neigh)]
    return g

graph = {'resnet': knn(RES), 'clip': knn(CLIP)}
json.dump(graph, open(os.path.join(DATA, 'similarity_graph.json'), 'w'), ensure_ascii=False)
# пометить в _meta, что эмбеддинги реальные
cat['_meta']['similarity'] = 'real ResNet50 + CLIP embeddings, precomputed offline'
json.dump(cat, open(os.path.join(DATA, 'catalog.json'), 'w'), ensure_ascii=False, indent=1)
print('OK: real embeddings written to similarity_graph.json, _meta updated')
