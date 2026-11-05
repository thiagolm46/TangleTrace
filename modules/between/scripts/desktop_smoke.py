"""Exercise the real pipe protocol using synthetic data only."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
WORKER = sys.argv[sys.argv.index('--worker') + 1] if '--worker' in sys.argv else None


class Client:
    def __init__(self, workspace):
        command = [WORKER] if WORKER else [sys.executable, '-u', '-m', 'app.worker']
        self.process = subprocess.Popen([*command, '--workspace', str(workspace)],
                                        cwd=workspace if WORKER else ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding='utf-8', env={**os.environ, 'PYTHONUTF8': '1'})
        self.number = 0

    def request(self, method, **params):
        self.number += 1
        self.process.stdin.write(json.dumps({'id': self.number, 'method': method, 'params': params}) + '\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        assert line, self.process.stderr.read()
        response = json.loads(line)
        assert response['id'] == self.number
        return response

    def call(self, method, **params):
        response = self.request(method, **params)
        assert response['ok'], response
        return response['result']

    def stop(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdout.close()
        self.process.stderr.close()


def main():
    check_root = ROOT / 'workspace' / 'desktop-checks'
    check_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pipes-', dir=check_root) as folder:
        c = Client(folder)
        try:
            config = c.call('config')
            assert config['protocol_version'] == 1
            second = Client(folder)
            try:
                assert not second.request('config')['ok'], 'The lock must prevent two workers from using the same database'
            finally:
                second.stop()
            assert not c.request('unrecognized_method')['ok']
            assert not c.request('open_session')['ok'], 'A missing parameter must not crash the process'
            job_id = c.call('demo')['job_id']
            for _ in range(300):
                job = c.call('job', job_id=job_id)
                if job['status'] != 'running': break
                time.sleep(.05)
            assert job['status'] == 'done', job
            import_id = job['result']['import_id']
            window = c.call('windows', import_id=import_id, annotator_id='desktop-smoke')[0]
            session = c.call('open_session', import_id=import_id, sample_id=window['sample_id'], annotator_id='desktop-smoke')
            state = c.call('state', session_id=session['id'])
            source = next(m for m in state['messages'] if m['requires_reply_annotation'])
            decision = dict(state['decisions'][source['message_id']])
            decision.update(source_status='new_conversation', notes='Local verification: explicit decision.')
            payload = dict(session_id=session['id'], source_id=source['message_id'], decision=decision, expected_revision=0)
            draft = c.call('draft', **payload)
            before = c.call('state', session_id=session['id'])
            assert before['progress']['confirmed'] == 0
            c.call('shutdown')
        finally:
            c.stop()
        c = Client(folder)
        try:
            restored = c.call('state', session_id=session['id'])
            assert restored['drafts'][source['message_id']]['decision']['notes'] == decision['notes']
            after = c.call('confirm', **payload, expected_draft_updated=draft['updated_at'])
            assert after['progress']['confirmed'] == 1
            assert not c.request('confirm', **payload)['ok'], 'A stale revision must be rejected'
            exported = c.call('export', session_id=session['id'], expected_revision=after['session']['graph_revision'])
            out = Path(exported['directory'])
            summary = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
            assert summary['confirmed'] == 1 and summary['status_new_conversation'] == 1
            assert summary['status'] == 'work_in_progress'
            assert (out / 'summary.csv').is_file()
            assert 'summary.csv' in exported['manifest']['outputs']
            assert exported['manifest']['drafts_excluded'] is True
            c.call('shutdown')
        finally:
            c.stop()
    print('OK: JSON pipes, workspace lock, recoverable errors, synthetic import, persistent draft, resume, confirmation, revision conflict, and local CSV/JSON export.')


if __name__ == '__main__':
    main()
