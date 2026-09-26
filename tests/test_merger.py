import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('merger', ROOT / 'tools/merge_opportunities.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def record(name='Example 2027', url='https://example.org/call'):
    r = {f: 'test' for f in m.REQUIRED}
    r.update(name=name, url=url, priority='B', verified='2026-09-26', tags=['Sculpture'], discipline=['Sculpture'])
    return r


def insert(r=None, state='READY', id='axis1.example.r1'):
    r = r or record()
    return dict(id=id, axis=1, state=state, op='insert', key={k:r[k] for k in ('name', 'url')}, edition='2027', record=r,
                evidence=[dict(url=r['url'], checkedAt='2026-09-26T20:40:00Z', supports=['eligibility'])])


def queue(items, **kwargs):
    q = dict(protocol=m.PROTOCOL, publicationGate='AUTHORIZED', authorizationEvidence='SYNTHETIC TEST FIXTURE ONLY', items=items, quarantine=[], receipts=[])
    q.update(kwargs)
    return q


def js(records):
    return 'window.DIANE_OPPORTUNITIES = [\n' + ',\n'.join(m.stable(r) for r in records) + '\n];\n'


class MergeTests(unittest.TestCase):
    def run_plan(self, text, q, mode='authorized'):
        return m.plan(text, q, m.blob_sha(text), mode)

    def test_empty_noop(self):
        t = js([record()])
        self.assertEqual(self.run_plan(t, queue([]))[0], t)

    def test_insert_empty(self):
        out, report = self.run_plan(js([]), queue([insert()]))
        self.assertEqual(m.LiteralParser(out).records()[0], [record()])
        self.assertFalse(report['published'])

    def test_insert_preserves_raw_neighbor(self):
        t = 'window.DIANE_OPPORTUNITIES = [\n {name:"Old",url:"https://old.example/",custom:123}\n];\n'
        out, _ = self.run_plan(t, queue([insert()]))
        self.assertIn('{name:"Old",url:"https://old.example/",custom:123}', out)
        self.assertEqual(len(m.LiteralParser(out).records()[0]), 2)

    def test_compact_no_comma(self):
        t = 'window.DIANE_OPPORTUNITIES=[{name:"Old",url:"https://old.example/"}];'
        out, _ = self.run_plan(t, queue([insert()]))
        self.assertEqual(len(m.LiteralParser(out).records()[0]), 2)

    def test_trailing_comma(self):
        t = 'window.DIANE_OPPORTUNITIES=[{name:"Old",url:"https://old.example/"},/*keep*/];'
        out, _ = self.run_plan(t, queue([insert()]))
        self.assertIn('/*keep*/', out)
        self.assertEqual(len(m.LiteralParser(out).records()[0]), 2)

    def test_idempotent_insert(self):
        q = queue([insert()])
        once, _ = self.run_plan(js([]), q)
        twice, r = self.run_plan(once, q)
        self.assertEqual(once, twice)
        self.assertEqual(r['results'][0]['status'], 'ALREADY_APPLIED')

    def test_review_never_emits_changes(self):
        t = js([])
        out, r = self.run_plan(t, queue([insert()]), 'review')
        self.assertEqual(out, t)
        self.assertEqual(r['plannedCount'], 1)

    def test_global_hold(self):
        q = queue([insert()], publicationGate='HOLD_UNRESOLVED_SAFETY')
        with self.assertRaises(m.Invalid):
            self.run_plan(js([]), q)
        self.assertEqual(self.run_plan(js([]), q, 'review')[0], js([]))

    def test_blocked_skipped(self):
        out, r = self.run_plan(js([]), queue([insert(state='BLOCKED_SAFETY')]))
        self.assertEqual(out, js([]))
        self.assertEqual(r['results'][0]['status'], 'QUARANTINED')

    def test_quarantine_survives_rename(self):
        item = insert(record('Renamed', 'https://example.org/call'))
        q = queue([item], quarantine=[dict(key=dict(name='Former name', url='https://example.org/call'))])
        self.assertEqual(self.run_plan(js([]), q)[1]['results'][0]['status'], 'QUARANTINED')

    def test_atomic_batch_on_conflict(self):
        original = record()
        conflict = record()
        conflict['fee'] = 'different'
        t = js([original])
        q = queue([insert(record('Good', 'https://good.example/'), id='good'), insert(conflict)])
        out, r = self.run_plan(t, q)
        self.assertEqual(out, t)
        self.assertTrue(r['validationErrors'])

    def test_stale_blob(self):
        with self.assertRaises(m.Invalid):
            m.plan(js([]), queue([]), '0'*40)

    def test_reused_id_rejected(self):
        with self.assertRaises(m.Invalid):
            self.run_plan(js([]), queue([insert(), insert(record('Other', 'https://other.example/'))]))

    def test_duplicate_identical_id(self):
        _, r = self.run_plan(js([]), queue([insert(), insert()]))
        self.assertEqual(len(r['results']), 1)

    def test_unknown_state(self):
        out, r = self.run_plan(js([]), queue([insert(state='MAGIC_APPROVED')]))
        self.assertEqual(out, js([]))
        self.assertTrue(r['validationErrors'])

    def test_missing_evidence(self):
        i = insert()
        i['evidence'] = []
        self.assertTrue(self.run_plan(js([]), queue([i]))[1]['validationErrors'])

    def test_patch_tags_and_neighbor(self):
        before = record()
        other = record('Other', 'https://other.example/')
        item = insert()
        item.pop('record')
        item.update(op='patch', changes={'fee':dict(beforePresent=True, before='test', after='verified fee')}, addTags=['Sculpture','résidence'])
        t = js([before, other])
        out, _ = self.run_plan(t, queue([item]))
        parsed = m.LiteralParser(out).records()[0]
        self.assertEqual(parsed[0]['tags'], ['Sculpture','résidence'])
        self.assertEqual(parsed[0]['fee'], 'verified fee')
        self.assertIn(m.stable(other), out)
        self.assertEqual(self.run_plan(out, queue([item]))[0], out)

    def test_field_conflict_preserves_all(self):
        item = insert()
        item.pop('record')
        item.update(op='patch', changes={'fee':dict(beforePresent=True, before='stale', after='new')})
        t = js([record()])
        self.assertEqual(self.run_plan(t, queue([item]))[0], t)

    def test_receipt_prevents_old_replay(self):
        item = insert()
        receipt = dict(id=item['id'], payloadHash=m.operation_hash(item), status='INTEGRATED_MAIN')
        changed = record()
        changed['fee'] = 'owner edit'
        t = js([changed])
        out, r = self.run_plan(t, queue([item], receipts=[receipt]))
        self.assertEqual(out, t)
        self.assertEqual(r['results'][0]['status'], 'ALREADY_RECEIPTED')

    def test_untrusted_receipt(self):
        q = queue([], receipts=[dict(id='x',payloadHash='x',status='QUEUED')])
        with self.assertRaises(m.Invalid):
            self.run_plan(js([]), q)

    def test_no_js_execution(self):
        for t in ['window.DIANE_OPPORTUNITIES=[];process.exit(0)',
                  'window.DIANE_OPPORTUNITIES=[{name:"x",url:"https://e.org",x:(()=>1)()}]',
                  'window.DIANE_OPPORTUNITIES=[{name:"a",name:"b",url:"https://e.org"}]',
                  'window.DIANE_OPPORTUNITIES=[{name:"a",url:"https://e.org",__proto__:{}}]']:
            with self.subTest(t=t), self.assertRaises(m.Invalid):
                m.LiteralParser(t).records()

    def test_current_data_untouched(self):
        path = ROOT/'data.js'
        if not path.exists():
            self.skipTest('historical exact-byte fixture is local only')
        text = path.read_bytes().decode('utf-8')
        self.assertGreater(len(m.LiteralParser(text).records()[0]), 0)
        q = queue([insert(state='BLOCKED_SAFETY')], publicationGate='HOLD_UNRESOLVED_SAFETY')
        self.assertEqual(self.run_plan(text,q,'review')[0],text)


if __name__ == '__main__':
    unittest.main()
