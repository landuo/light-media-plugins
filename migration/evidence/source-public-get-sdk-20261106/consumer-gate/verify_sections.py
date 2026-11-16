from pathlib import Path
import hashlib, json, struct, subprocess

repo = Path.cwd()
work = Path(__file__).resolve().parent
baseline = json.loads((repo / 'work/parallel-sdk-sync-20261106/linux-consumer-builds.json').read_text())

def sections(data):
    assert data[:6] == b'\x7fELF\x02\x01'
    offset = struct.unpack_from('<Q', data, 40)[0]
    width, count, names = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * width) for i in range(count)]
    names_header = headers[names]
    table = data[names_header[4]:names_header[4] + names_header[5]]
    result = {}
    for header in headers:
        name = table[header[0]:].split(b'\0', 1)[0].decode()
        content = data[header[4]:header[4] + header[5]] if header[1] != 8 else b''
        result[name] = dict(offset=header[4], size=header[5], type=header[1], sha256=hashlib.sha256(content).hexdigest())
    return result

notes = {'.note.go.buildid', '.note.gnu.build-id'}
observations = []
for row in baseline:
    if row['id'].endswith('-update'):
        continue
    original = Path(row['artifact']).read_bytes()
    proposed_path = work / (row['id'] + '-linux')
    proposed = proposed_path.read_bytes()
    assert hashlib.sha256(original).hexdigest() == row['sha256']
    a, b = sections(original), sections(proposed)
    assert a.keys() == b.keys()
    differences = [name for name in a if a[name] != b[name]]
    assert len(original) == len(proposed)
    assert set(differences) <= notes
    positions = [i for i, (x, y) in enumerate(zip(original, proposed)) if x != y]
    assert all(any(b[name]['offset'] <= i < b[name]['offset'] + b[name]['size'] for name in notes) for i in positions)
    symbols = subprocess.check_output(['go', 'tool', 'nm', str(proposed_path)], text=True)
    assert '.Network.Get' not in symbols and '.validNetworkGetProfile' not in symbols
    observations.append(dict(id=row['id'], different_sections=differences, changed_bytes=len(positions),
                             exact_bytes_outside_provenance_notes=True, full_bytes_equal=original == proposed))
print(json.dumps(observations, indent=2))
