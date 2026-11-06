#!/usr/bin/env python3
"""Build the road map Groundwork users can download, and the files that go beside it (gw 2.0/ROAD_MAP.md).

This script is also how the map is made, published with it: the map is a database derived from OpenStreetMap, shared
under the Open Database License. Needs `pip install osmium pyvalhalla`, about 15 GB free, and over an hour.

    python scripts/build_road_map.py --pbf us-latest.osm.pbf --data-date 2026-11-03 --out road-map

    --pbf         the OpenStreetMap extract, from https://download.geofabrik.de/north-america/us-latest.osm.pbf
    --data-date   the date of that extract, shown to the person
    --out         a new folder; what lands in it goes in Website/static/download/road-map/
    --tar         an already built us-roads.tar: skips straight to packaging it

Only main roads are kept (motorway to secondary, with their links). Ferries are left out. Private roads are left out.
"""
import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KEEP = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link'}
DOWNLOAD_BASE = 'https://groundworkfinance.app/static/download/road-map/'
NOTICE = """Groundwork road map: main roads of the United States.

Contains information from OpenStreetMap, which is made available here under the Open Database License (ODbL):
https://opendatacommons.org/licenses/odbl/1-0/
Credit: OpenStreetMap, https://www.openstreetmap.org/copyright

us-roads.tar.gz is a database derived from OpenStreetMap and is shared under the same licence. It keeps the ways tagged
motorway, trunk, primary and secondary (and their links), not private or closed, with the nodes they use, compiled to
Valhalla routing tiles. build_road_map.py, beside this file, is the whole method.

Source extract date: {date}. Source: https://download.geofabrik.de/north-america/us-latest.osm.pbf
"""


def filter_roads(src, dst):
    import osmium

    def kept(way):
        return way.tags.get('highway') in KEEP and way.tags.get('access') not in ('private', 'no')

    class Ways(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes = osmium.index.IdSet()

        def way(self, w):
            if kept(w):
                for n in w.nodes:
                    self.nodes.set(n.ref)

    ways = Ways()
    ways.apply_file(str(src), locations=False)
    with osmium.SimpleWriter(str(dst), overwrite=True) as out:
        for obj in osmium.FileProcessor(str(src), osmium.osm.NODE | osmium.osm.WAY):
            if obj.is_node():
                if obj.id in ways.nodes:
                    out.add_node(obj)
            elif kept(obj):
                out.add_way(obj)


def build_tar(pbf, work):
    """Filtered roads to tiles to one file. The Valhalla tools come with the pyvalhalla package."""
    import valhalla
    from valhalla import get_config
    pkg = Path(valhalla.__file__).parent
    tiles = work / 'tiles'
    tiles.mkdir(parents=True, exist_ok=True)
    tar = work / 'us-roads.tar'
    tar.touch()
    cfg = get_config(tile_dir=str(tiles), tile_extract=str(tar))
    cfg['mjolnir']['concurrency'] = max(2, (os.cpu_count() or 4) - 4)
    conf = work / 'valhalla.json'
    conf.write_text(json.dumps(cfg, indent=1), encoding='utf-8')
    env = dict(os.environ)
    env['PATH'] = str(pkg.parent / 'pyvalhalla.libs') + os.pathsep + env.get('PATH', '')
    exe = pkg / 'bin' / ('valhalla_build_tiles.exe' if os.name == 'nt' else 'valhalla_build_tiles')
    subprocess.run([str(exe), '-c', str(conf), str(pbf)], check=True, env=env, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(pkg / 'valhalla_build_extract.py'), '-c', str(conf), '--overwrite'], check=True,
                   stdout=subprocess.DEVNULL)
    return tar


def package(tar, out, data_date):
    out.mkdir(parents=True, exist_ok=True)
    gz = out / 'us-roads.tar.gz'
    with open(tar, 'rb') as src, gzip.GzipFile(filename='', mode='wb', fileobj=open(gz, 'wb'), compresslevel=9, mtime=0) as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    h = hashlib.sha256()
    with open(gz, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    manifest = {'version': data_date.replace('-', ''), 'data_date': data_date, 'url': DOWNLOAD_BASE + 'us-roads.tar.gz',
                'sha256': h.hexdigest(), 'bytes': gz.stat().st_size, 'tar_bytes': Path(tar).stat().st_size,
                'licence': 'ODbL-1.0', 'credit': 'OpenStreetMap', 'built_at': time.strftime('%Y-%m-%d')}
    (out / 'us-roads.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    (out / 'README.txt').write_text(NOTICE.format(date=data_date), encoding='utf-8')
    shutil.copy(__file__, out / 'build_road_map.py')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pbf')
    ap.add_argument('--tar')
    ap.add_argument('--data-date', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    if a.tar:
        tar = Path(a.tar).resolve()
    elif a.pbf:
        work = Path(tempfile.mkdtemp(prefix='gw_road_map_', dir=str(out.parent)))
        roads = work / 'roads.osm.pbf'
        filter_roads(Path(a.pbf).resolve(), roads)
        tar = build_tar(roads, work)
    else:
        ap.error('--pbf or --tar')
    m = package(tar, out, a.data_date)
    print(json.dumps(m, indent=1))


if __name__ == '__main__':
    main()
