"""Preserve campaign batches as hashed archives and restore without overwrites."""

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import tarfile
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4

from src.evaluation.benchmark import file_hash
from .__main__ import _ROOT
from .batch import _exclude_batch, _record_manifest, _write_json
from .benchmark_plan import checked_path, read_json


def pack(root,campaign):
    root,campaign=Path(root).resolve(),Path(campaign).resolve()
    state=read_json(campaign/'manifest.json')
    if state['schema_version']!='fhcp-campaign/1' or state['status']!='complete':
        raise ValueError('Only a fully audited campaign can be archived.')
    if state.get('archive_index'):
        path=checked_path(root,state['archive_index']['path'])
        if file_hash(path)!=state['archive_index']['sha256']:
            raise ValueError('Archive index changed.')
        return path
    directory=campaign/'archives'
    directory.mkdir(exist_ok=True)
    rows=[]
    for phase,info in state['phases'].items():
        manifest_path=checked_path(root,info['manifest_path'])
        batch=manifest_path.parent
        batch_id=str(UUID(batch.name))
        if batch_id!=batch.name or batch.parent!=root/'experiments/results':
            raise ValueError('Invalid batch path.')
        filename=directory/f'{batch_id}-{uuid4()}.tar.gz'
        with NamedTemporaryFile(dir=directory,delete=False) as temporary:
            partial=Path(temporary.name)
        count=0
        try:
            with tarfile.open(partial,'w:gz',compresslevel=6) as archive:
                for path in sorted(batch.rglob('*')):
                    if path.name=='.lock':
                        continue
                    if path.is_symlink():
                        raise ValueError('Scientific archive cannot contain symbolic links.')
                    if path.is_file():
                        archive.add(path,arcname=(Path(batch_id)/path.relative_to(batch)).as_posix(),recursive=False)
                        count+=1
            partial.replace(filename)
        finally:
            partial.unlink(missing_ok=True)
        rows.append(dict(phase=phase,batch_id=batch_id,path=filename.relative_to(root).as_posix(),
                         sha256=file_hash(filename),manifest_sha256=file_hash(manifest_path),members=count))
    index=campaign/f'archive-index-{uuid4()}.json'
    _write_json(index,dict(schema_version='fhcp-campaign-archive/1',campaign_id=state['batch_id'],
                           freeze=state['freeze'],archives=rows))
    state['archive_index']=dict(path=index.relative_to(root).as_posix(),sha256=file_hash(index))
    _record_manifest(campaign,state)
    return index


def restore(root,index_path):
    root=Path(root).resolve()
    index=read_json(index_path)
    if index['schema_version']!='fhcp-campaign-archive/1':
        raise ValueError('Unknown archive schema.')
    destination=root/'experiments/results'
    if not destination.resolve().is_relative_to(root):
        raise ValueError('Results directory escapes the checkout.')
    restored=[]
    for row in index['archives']:
        batch_id=str(UUID(row['batch_id']))
        if batch_id!=row['batch_id']:
            raise ValueError('Invalid batch UUID.')
        path=checked_path(root,row['path'])
        if file_hash(path)!=row['sha256']:
            raise ValueError('Archive SHA-256 mismatch.')
        with tarfile.open(path,'r:gz') as archive:
            members=archive.getmembers()
            names=set()
            for member in members:
                name=PurePosixPath(member.name)
                target=(destination/Path(member.name)).resolve()
                if (name.is_absolute() or '..' in name.parts or not name.parts
                    or name.parts[0]!=batch_id or not member.isfile() or member.name in names
                    or not target.is_relative_to(destination/batch_id)):
                    raise ValueError('Unsafe or duplicated archive member.')
                names.add(member.name)
                if target.exists():
                    with archive.extractfile(member) as source:
                        if not target.is_file() or sha256(source.read()).hexdigest()!=file_hash(target):
                            raise ValueError('Restore would overwrite different existing evidence.')
            if len(members)!=row['members']:
                raise ValueError('Archive inventory differs.')
            _exclude_batch(root,Path('experiments/results')/batch_id)
            for member in members:
                target=destination/member.name
                if target.exists():
                    continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.extractfile(member) as source,target.open('xb') as stream:
                    while data:=source.read(1024*1024):
                        stream.write(data)
        if file_hash(destination/batch_id/'manifest.json')!=row['manifest_sha256']:
            raise ValueError('Restored manifest hash mismatch.')
        restored.append(batch_id)
    return restored


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    for name,argument in (('pack','campaign'),('restore','index')):
        command=sub.add_parser(name);command.add_argument(argument,type=Path)
    args=parser.parse_args(argv)
    if args.action=='pack':
        print(pack(_ROOT,args.campaign))
    else:
        print(json.dumps(dict(restored=restore(_ROOT,args.index))))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
