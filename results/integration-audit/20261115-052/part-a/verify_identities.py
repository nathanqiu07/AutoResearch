"""Identity-only recheck of the exact audit 052 partition A; never imports source."""
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

PROPOSAL_SHA = '0645f1588c016a6178a84b0f7b6458dae9eb8534962587f47e15077077334da0'


def state(s):
    return dict(device=s.st_dev, inode=s.st_ino, mode=oct(stat.S_IMODE(s.st_mode)),
                size_bytes=s.st_size, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)


def read_regular(path):
    path = Path(path)
    assert path.is_absolute() and '..' not in path.parts
    descriptors = []
    try:
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(parent)
        for part in path.parts[1:-1]:
            parent = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            descriptors.append(parent)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        descriptors.append(fd)
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        chunks = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b''.join(chunks)
        after = os.fstat(fd)
        path_after = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        assert stat.S_ISREG(path_after.st_mode)
        assert state(before) == state(after) == state(path_after)
        assert len(raw) == before.st_size
        return raw, state(after)
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--proposal', required=True)
    p.add_argument('--initial', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    proposal_raw, proposal_state = read_regular(args.proposal)
    assert hashlib.sha256(proposal_raw).hexdigest() == PROPOSAL_SHA
    proposal = json.loads(proposal_raw)
    assert len(proposal['files']) == 20
    initial = json.loads(Path(args.initial).read_bytes())
    assert initial['proposal_sha256'] == PROPOSAL_SHA
    assert len(initial['files']) == 10
    rows = []
    for index, (entry, old) in enumerate(zip(proposal['files'][:10], initial['files'])):
        assert old['index'] == index and old['original_path'] == entry['original_path']
        raw, final_state = read_regular(entry['original_path'])
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == entry['sha256'] == old['sha256']
        assert len(raw) == entry['bytes'] == old['size_bytes']
        assert final_state == old['state_before_and_after_initial_read']
        assert len(raw.decode('utf-8').splitlines()) == old['line_count']
        rows.append(dict(index=index, original_path=entry['original_path'], sha256=digest,
                         size_bytes=len(raw), final_file_state=final_state,
                         regular_nonsymlink_path=True, unchanged_since_initial_check=True))
    again, end_state = read_regular(args.proposal)
    assert again == proposal_raw and end_state == proposal_state
    result = dict(schema_version='audit052-part-a-final-identity-check-v1',
                  proposal=dict(path=args.proposal, sha256=PROPOSAL_SHA,
                                size_bytes=len(proposal_raw), stable_state=proposal_state),
                  reviewed_indices=list(range(10)), file_count=len(rows),
                  total_bytes=sum(r['size_bytes'] for r in rows), files=rows,
                  source_imported_or_executed=False, source_bodies_exported=False,
                  semantic_eligibility_not_determined_by_this_check=True)
    data = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    print(json.dumps({'files': len(rows), 'bytes': result['total_bytes'],
                      'all_identities_unchanged': True, 'report_sha256': hashlib.sha256(data).hexdigest()}))


if __name__ == '__main__':
    main()
