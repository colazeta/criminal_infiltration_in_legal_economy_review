"""Back up with the currently deployed code before any new schema is installed."""
import io
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

from scripts.enrichment.service_client import current_commit


def preserve(output):
    commit = current_commit()
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise RuntimeError('predeploy_backup_version_invalid')
    exists = subprocess.run(['git', 'cat-file', '-e', commit + '^{commit}'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if exists.returncode:
        subprocess.run(['git', 'fetch', '--no-tags', '--depth=1', 'origin', commit],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    data = subprocess.check_output(['git', 'archive', '--format=tar', commit], stderr=subprocess.DEVNULL)
    with tempfile.TemporaryDirectory(prefix='cile-predeploy-') as directory:
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(directory, filter='data')
        runner = Path(directory) / 'scripts/architecture/private-backup.mjs'
        if not runner.is_file():
            raise RuntimeError('predeploy_backup_not_supported')
        env = {**os.environ, 'GITHUB_SHA': commit}
        diagnostics = Path(__file__).with_name('backup-diagnostics.mjs').resolve()
        subprocess.run(['node', '--import', str(diagnostics), str(runner), 'capture', str(output)], cwd=directory,
                       env=env, check=True)


if __name__ == '__main__':
    try:
        preserve(Path(os.environ['RUNNER_TEMP']) / 'cile-before-deploy.encrypted.json')
    except Exception:
        raise SystemExit('predeploy_backup_gate_failed') from None
