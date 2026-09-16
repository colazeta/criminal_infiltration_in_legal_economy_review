from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_private_machine_authentication_precedes_store_readiness():
    source = (ROOT / 'curator-app/src/enrichment-store.js').read_text(encoding='utf-8')
    fetch_start = source.index('  async fetch(request) {')
    fetch_end = source.index('\n  }\n}\n\nexport function enrichmentStore', fetch_start)
    fetch_source = source[fetch_start:fetch_end]
    route = "if(url.pathname==='/machine')return this.machine(request);"
    assert route in fetch_source
    assert fetch_source.index(route) < fetch_source.index('await this.ready;')


def test_machine_still_authenticates_before_verify_waits_for_readiness():
    source = (ROOT / 'curator-app/src/enrichment-store.js').read_text(encoding='utf-8')
    machine_start = source.index('  async machine(request,now=Date.now()) {')
    machine_end = source.index('\n  async alarm()', machine_start)
    machine = source[machine_start:machine_end]
    assert 'await this.authorise(request,body,now);' in machine
    assert "if(data.operation==='verify')return json(await this.verify());" in machine
    assert machine.index('await this.authorise(request,body,now);') < machine.index("if(data.operation==='verify')")
