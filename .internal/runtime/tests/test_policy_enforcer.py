"""Tests for the policy enforcer runtime."""

from __future__ import annotations

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from policy_enforcer import PolicyEnforcer, PolicyFinding, PolicyReport


@pytest.fixture
def enforcer():
    return PolicyEnforcer(run_id="test-policy-001")


class TestPolicyEnforcerBasic:
    def test_clean_file_passes(self, enforcer, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("x = 1\ny = 2\n")
        report = enforcer.scan_file(f)
        assert report.passed
        assert len(report.findings) == 0

    def test_scan_content_clean(self, enforcer):
        report = enforcer.scan_content("print('hello')", "test.py")
        assert report.passed

    def test_scan_nonexistent_file(self, enforcer):
        report = enforcer.scan_file("/nonexistent/file.py")
        assert not report.passed
        assert len(report.findings) == 1

    def test_scan_nonexistent_directory(self, enforcer):
        report = enforcer.scan_directory("/nonexistent/dir")
        assert not report.passed


class TestPolicyEnforcerSecrets:
    def test_api_key_detection(self, enforcer):
        key = "sk_" + "test_" + "abc123def456ghi789jkl012mno345"
        content = "API_KEY = " + chr(34) + key + chr(34)
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "SEC-001" for f in report.findings)

    def test_password_detection(self, enforcer):
        pwd = "P@ss" + "w0rd!" + "2024"
        content = "password = " + chr(34) + pwd + chr(34)
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "SEC-003" for f in report.findings)

    def test_token_detection(self, enforcer):
        tok = "ghp_" + "ABC" + "DEF" + "GHI" + "JKL" + "MNO" + "PQR" + "STU"
        content = "token = " + chr(34) + tok + chr(34)
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "SEC-004" for f in report.findings)

    def test_aws_key_detection(self, enforcer):
        aws_key = "AKIA" + "IOSFODNN7EXAMPLE"
        content = "aws_access_key_id = " + chr(34) + aws_key + chr(34)
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "SEC-005" for f in report.findings)

    def test_private_key_detection(self, enforcer):
        pem_header = "-----BEGIN " + "RSA PRIVATE KEY-----"
        content = "private_key = " + chr(34) + pem_header + chr(34)
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "SEC-006" for f in report.findings)

    def test_github_token_detection(self, enforcer):
        tok = "ghp_" + "XYZ" + "123" + "ABC" + "456" + "DEF" + "789" + "GHI"
        content = "GITHUB_TOKEN = " + chr(34) + tok + chr(34)
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "SEC-008" for f in report.findings)


class TestPolicyEnforcerForbidden:
    def test_eval_detection(self, enforcer):
        content = "result = eval(user_input)"
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "POL-001" for f in report.findings)

    def test_os_system_detection(self, enforcer):
        content = 'os.system("rm -rf /")'
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "POL-002" for f in report.findings)

    def test_subprocess_shell_detection(self, enforcer):
        content = 'subprocess.run("ls", shell=True)'
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "POL-003" for f in report.findings)

    def test_pickle_detection(self, enforcer):
        content = "data = pickle.loads(raw_bytes)"
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "POL-005" for f in report.findings)

    def test_unsafe_yaml_detection(self, enforcer):
        content = "data = yaml.load(raw_yaml)"
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "POL-006" for f in report.findings)

    def test_safe_yaml_passes(self, enforcer):
        content = "data = yaml.safe_load(raw_yaml)"
        report = enforcer.scan_content(content, "test.py")
        assert report.passed


class TestPolicyEnforcerOWASP:
    def test_sql_injection_detection(self, enforcer):
        content = 'query = "SELECT * FROM users WHERE id = " + user_id'
        report = enforcer.scan_content(content, "test.py")
        assert not report.passed
        assert any(f.rule_id == "OWASP-001" for f in report.findings)

    def test_xss_script_detection(self, enforcer):
        content = '<script>alert("xss")</script>'
        report = enforcer.scan_content(content, "test.html")
        assert not report.passed
        assert any(f.rule_id == "OWASP-002" for f in report.findings)

    def test_xss_javascript_uri_detection(self, enforcer):
        content = '<a href="javascript:alert(1)">click</a>'
        report = enforcer.scan_content(content, "test.html")
        assert not report.passed
        assert any(f.rule_id == "OWASP-003" for f in report.findings)

    def test_plain_javascript_key_does_not_trigger_xss(self, enforcer):
        content = "javascript:\n  linter: eslint\n"
        report = enforcer.scan_content(content, "linting-tools.yaml")
        assert report.passed


class TestPolicyReport:
    def test_risk_score_zero_when_clean(self, enforcer):
        report = enforcer.scan_content("x = 1", "test.py")
        assert report.risk_score == 0.0

    def test_risk_score_high_for_critical(self, enforcer):
        key = "sk_" + "live_" + "abc123def456ghi789jkl012mno345"
        content = "API_KEY = " + chr(34) + key + chr(34)
        report = enforcer.scan_content(content, "test.py")
        assert report.risk_score > 0

    def test_secrets_found_count(self, enforcer):
        key = "sk_" + "test_" + "xyz789abc123def456ghi012jkl345"
        pwd = "P@ss" + "w0rd!" + "2024"
        content = (
            "API_KEY = "
            + chr(34)
            + key
            + chr(34)
            + "\n"
            + "password = "
            + chr(34)
            + pwd
            + chr(34)
        )
        report = enforcer.scan_content(content, "test.py")
        assert report.secrets_found >= 1

    def test_to_dict_structure(self, enforcer):
        report = enforcer.scan_content("x = 1", "test.py")
        d = report.to_dict()
        assert "run_id" in d
        assert "passed" in d
        assert "findings" in d
        assert "integrity_hash" in d


class TestPolicyEnforcerDirectory:
    def test_scan_specs_directory(self, enforcer):
        report = enforcer.scan_directory(".internal/specs")
        assert report.files_scanned > 0
        assert report.passed

    def test_scan_with_exclude(self, enforcer, tmp_path):
        (tmp_path / "clean.py").write_text("x = 1")
        key = "sk_" + "test_" + "exclude123abc456def789ghi012jkl"
        (tmp_path / "bad.py").write_text("API_KEY = " + chr(34) + key + chr(34))
        report = enforcer.scan_directory(tmp_path, exclude_patterns=["bad.py"])
        assert report.passed
