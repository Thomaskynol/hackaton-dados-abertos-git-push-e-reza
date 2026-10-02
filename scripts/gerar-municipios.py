#!/usr/bin/env python3
"""Gera public/geo/municipios/<UF>.geo.json a partir da API de Malhas do IBGE.

Uso: python3 scripts/gerar-municipios.py SP MG BA
Sem args: gera SP (piloto Araraquara). Rode com internet UMA vez; o app usa
só os arquivos estáticos gerados (front 100% offline, sem HTTP em produção).

Fonte: IBGE API v3 malhas (intrarregiao=municipio, qualidade=minima) + v1 localidades.
REGRA DE OURO: contornos+nominais oficiais; nenhum dado agrícola inventado.
"""
import json, math, os, sys, urllib.request, gzip

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "front", "public", "geo", "municipios")

COD_UF = {"AC":"12","AL":"27","AM":"13","AP":"16","BA":"29","CE":"23","DF":"53","ES":"32","GO":"52","MA":"21","MG":"31","MS":"50","MT":"51","PA":"15","PB":"25","PE":"26","PI":"22","PR":"41","RJ":"33","RN":"24","RO":"11","RR":"14","RS":"43","SC":"42","SE":"28","SP":"35","TO":"17"}

def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = r.read()
    # Alguns servidores respondem gzip mesmo sem Accept-Encoding: descompacta.
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))

def perp(p,a,b):
    x,y=p;ax,ay=a;bx,by=b;dx,dy=bx-ax,by-ay;L2=dx*dx+dy*dy
    if L2==0: return math.hypot(x-ax,y-ay)
    t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/L2));return math.hypot(x-(ax+t*dx),y-(ay+t*dy))

def rdp(pts,tol):
    if len(pts)<=2: return pts
    keep=[False]*len(pts);keep[0]=keep[-1]=True;stack=[(0,len(pts)-1)]
    while stack:
        s,e=stack.pop();dmax,imax=0,s
        for i in range(s+1,e):
            d=perp(pts[i],pts[s],pts[e])
            if d>dmax:dmax,imax=d,i
        if dmax>tol:keep[imax]=True;stack.append((s,imax));stack.append((imax,e))
    return [p for p,k in zip(pts,keep) if k]

def gerar(uf):
    cod = COD_UF[uf]
    print(f"[{uf}] baixando malha...", flush=True)
    malha = get(f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}?intrarregiao=municipio&qualidade=minima&formato=application%2Fvnd.geo%2Bjson")
    print(f"[{uf}] baixando nomes...", flush=True)
    locs = get(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{cod}/municipios")
    nomes = {str(m["id"]): m["nome"] for m in locs}
    muns = []
    for f in malha["features"]:
        codarea = f["properties"]["codarea"]; g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        aneis = []
        for poly in polys:
            for ring in poly:
                r = rdp([(round(x,4), round(y,4)) for x,y in ring], 0.012)
                if len(r) >= 4: aneis.append(r)
        muns.append({"ibge": codarea, "nome": nomes.get(codarea, codarea), "aneis": aneis})
    out = {"uf": uf, "fonte": "IBGE - API de Malhas v3 (intrarregiao=municipio, qualidade=minima) + API de Localidades", "gerado_em": "2026-10-02", "total": len(muns), "municipios": muns}
    os.makedirs(DIR, exist_ok=True)
    dest = os.path.join(DIR, f"{uf}.geo.json")
    json.dump(out, open(dest, "w"), separators=(",", ":"))
    print(f"[{uf}] OK: {len(muns)} municipios -> {dest} ({os.path.getsize(dest)//1024}KB)")

if __name__ == "__main__":
    ufs = [a.upper() for a in sys.argv[1:]] or ["SP"]
    for uf in ufs:
        if uf not in COD_UF: print(f"UF invalida: {uf}"); continue
        gerar(uf)
