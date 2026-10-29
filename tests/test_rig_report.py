"""Run actual acceptance files; failures must remain visible in the report."""
import json
import math
from minerva.test_rig.runner import run_test_rig


def test_rig_report(tmp_path):
    code = run_test_rig(tmp_path)
    report = json.loads((tmp_path / 'test_report.json').read_text())
    assert report['schema_version'] == 1
    assert report['statement'] == 'Simulation only; never flown.'
    assert report['environment']['python']
    assert report['environment']['os']
    assert len(report['environment']['libraries']) == 7
    assert [t['id'] for t in report['tests']] == [f'T{i}' for i in range(1, 9)]
    assert code == (0 if all(t['passed'] for t in report['tests']) else 1)
    for test in report['tests']:
        assert test['name'] and test['target_gate']
        assert test['elapsed_s'] > 0
        measured = test['measured_result']
        assert measured['acceptance_output']
        assert measured['test_cases']
        assert sum(test['counts'].values()) == len(measured['test_cases'])
        for case in measured['test_cases']:
            assert case['name']
            assert math.isfinite(case['elapsed_s']) and case['elapsed_s'] >= 0
            if case['status'] != 'passed':
                assert case['detail']
        if test['id'] == 'T4':
            assert measured['metrics']['requests'] == 100
            assert measured['metrics']['found'] >= 95
            assert measured['metrics']['validated'] == measured['metrics']['found']
            assert 0 < measured['metrics']['median_s'] <= measured['metrics']['p95_s']
        if test['id'] == 'T5':
            assert set(measured['metrics']['counts']) == {'10', '50', '200', '500'}
        assert (tmp_path / f"{test['id']}.log").exists()
    assert report['tests'][-1]['measured_result']['frozen_executable'] == 'checked by CI workflow'
    markdown = (tmp_path / 'test_report.md').read_text()
    assert 'Simulation only; never flown.' in markdown
    assert "applicant's responsibility" in markdown
    assert 'checked by CI workflow' in markdown
