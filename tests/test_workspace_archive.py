"""Release restoration must preserve evidence and refuse destructive writes."""
import hashlib
import io
import json
import tempfile
import tarfile
import unittest
from pathlib import Path

from scripts.package_research_workspace import package, ARCHIVE
from scripts.restore_research_workspace import restore
from scripts.join_research_archive import join


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source, self.assets, self.target = (self.base/'source', self.base/'assets', self.base/'target')
        (self.source/'data/processed').mkdir(parents=True)
        (self.source/'data/processed/input.dat').write_bytes(b'original input')
        (self.source/'results').mkdir()
        (self.source/'results/evidence.json').write_text('{"failed_control":true}')
        worker = self.source/'results/worker.out'
        worker.write_bytes(b'preserved binary bytes')
        worker.chmod(0o755)
        (self.source/'models').mkdir()
        (self.source/'models/model.joblib').write_bytes(b'never unpickle')

    def prepare(self):
        package(self.source, self.assets)
        return self.assets/ARCHIVE, self.assets/'research-workspace-manifest.json'

    def test_roundtrip_preserves_bytes_mode_and_idempotent_restore(self):
        archive, manifest = self.prepare()
        first = restore(archive, manifest, self.target, self.assets/'research-workspace.sha256')
        self.assertEqual(first['restored'], 4)
        self.assertEqual((self.target/'results/evidence.json').read_bytes(), (self.source/'results/evidence.json').read_bytes())
        self.assertTrue((self.target/'results/worker.out').stat().st_mode & 0o111)
        again = restore(archive, manifest, self.target)
        self.assertEqual(again['restored'], 0)
        self.assertEqual(again['identical_skipped'], 4)

    def test_conflict_is_detected_before_any_new_files_are_written(self):
        archive, manifest = self.prepare()
        (self.target/'results').mkdir(parents=True)
        (self.target/'results/evidence.json').write_text('existing different evidence')
        with self.assertRaisesRegex(ValueError, 'Refuse to overwrite'):
            restore(archive, manifest, self.target)
        self.assertFalse((self.target/'data').exists())
        self.assertEqual((self.target/'results/evidence.json').read_text(), 'existing different evidence')

    def test_archive_tampering_is_rejected_before_extraction(self):
        archive, manifest = self.prepare()
        with archive.open('ab') as output: output.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'Archive SHA256 mismatch'):
            restore(archive, manifest, self.target)
        self.assertFalse(self.target.exists())

    def test_internal_file_link_is_materialized_and_external_link_rejected(self):
        (self.source/'results/alias.json').symlink_to('evidence.json')
        archive, manifest = self.prepare()
        restore(archive, manifest, self.target)
        self.assertFalse((self.target/'results/alias.json').is_symlink())
        self.assertEqual((self.target/'results/alias.json').read_bytes(), (self.source/'results/evidence.json').read_bytes())
        (self.source/'results/unsafe').symlink_to(self.base/'outside')
        (self.base/'outside').write_text('must not publish')
        with self.assertRaisesRegex(ValueError, 'External or nonfile symlink'):
            package(self.source, self.base/'assets2')

    def test_traversal_and_link_members_are_rejected_even_with_matching_archive_hash(self):
        for name, link in [('results/../../escaped', False), ('results/link', True)]:
            with self.subTest(name=name):
                archive = self.base/('link.tar.gz' if link else 'traversal.tar.gz')
                with tarfile.open(archive, 'w:gz') as output:
                    member=tarfile.TarInfo(name)
                    content=b'escape'
                    if link:
                        member.type=tarfile.SYMTYPE
                        member.linkname='/tmp/escaped'
                    else:
                        member.size=len(content)
                    output.addfile(member, None if link else io.BytesIO(content))
                manifest=self.base/'bad-manifest.json'
                manifest.write_text(json.dumps({'schema_version':1,'archive':archive.name,
                    'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                    'files':{name:{'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}}}))
                with self.assertRaises(ValueError):restore(archive, manifest, self.target)
                self.assertFalse(self.target.exists())

    def make_parts(self):
        content=b'complete research bytes'
        pieces=[content[:6],content[6:13],content[13:]]
        records=[]
        directory=self.base/'parts';directory.mkdir()
        for index,piece in enumerate(pieces):
            name=f'workspace.part{index:03d}'
            (directory/name).write_bytes(piece)
            records.append({'name':name,'bytes':len(piece),'sha256':hashlib.sha256(piece).hexdigest()})
        (directory/'research-workspace-parts.json').write_text(json.dumps({'schema_version':1,
            'archive':'workspace.tar.gz','archive_bytes':len(content),
            'archive_sha256':hashlib.sha256(content).hexdigest(),'parts':records}))
        return directory,content

    def test_join_checks_parts_and_whole_archive_without_overwriting(self):
        directory,content=self.make_parts()
        output=join(directory)
        self.assertEqual(output.read_bytes(),content)
        with self.assertRaisesRegex(ValueError,'Refuse to overwrite'):join(directory)

    def test_join_rejects_tampered_part_and_removes_partial_output(self):
        directory,_=self.make_parts()
        path=directory/'workspace.part001'
        path.write_bytes(b'x'*path.stat().st_size)
        with self.assertRaisesRegex(ValueError,'checksum mismatch'):join(directory)
        self.assertFalse((directory/'workspace.tar.gz').exists())
        self.assertFalse((directory/'workspace.tar.gz.partial').exists())


if __name__ == '__main__':
    unittest.main()
