import pytest
from click.testing import CliRunner
from azamlabs.cli.main import cli
from azamlabs.core.schema import AzamTopology, AzamNode
from azamlabs.core.engine import engine


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_version(runner):
    """Tests 'azam version' and --version flag."""
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "AZAMLABS" in result.output
    assert "Ubuntu 26.04 LTS" in result.output

    flag_result = runner.invoke(cli, ["--version"])
    assert flag_result.exit_code == 0


def test_cli_doctor(runner):
    """Tests 'azam doctor' host diagnostic checks."""
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "Running Host Diagnostics" in result.output
    assert "KVM Virtualization" in result.output
    assert "Kernel Same-Page Merging" in result.output
    assert "High-Speed SQLite WAL Engine" in result.output


def test_cli_lab_lifecycle(runner, tmp_path):
    """Tests full lab lifecycle via CLI: create, list, get, status, start, stop, wipe, delete."""
    # 1. Create a test YAML topology file
    topo = AzamTopology(
        name="CLI Test Topology",
        nodes=[
            AzamNode(id="cn1", name="CLI-R1", device_type="router", driver="docker", console_port=31001)
        ]
    )
    yaml_file = tmp_path / "cli_topo.yaml"
    yaml_file.write_text(topo.to_yaml(), encoding="utf-8")

    # Create
    res_create = runner.invoke(cli, ["lab", "create", str(yaml_file)])
    assert res_create.exit_code == 0
    assert "[OK]" in res_create.output
    lab_id = topo.id

    # List
    res_list = runner.invoke(cli, ["lab", "list"])
    assert res_list.exit_code == 0
    assert lab_id in res_list.output

    # Get
    res_get = runner.invoke(cli, ["lab", "get", lab_id])
    assert res_get.exit_code == 0
    assert "CLI-R1" in res_get.output

    # Status
    res_status = runner.invoke(cli, ["lab", "status", lab_id])
    assert res_status.exit_code == 0
    assert "CLI-R1" in res_status.output

    # Start
    res_start = runner.invoke(cli, ["lab", "start", lab_id])
    assert res_start.exit_code == 0
    assert "100:1 KSM" in res_start.output

    # Stop
    res_stop = runner.invoke(cli, ["lab", "stop", lab_id])
    assert res_stop.exit_code == 0
    assert "[OK] Stopped" in res_stop.output

    # Wipe
    res_wipe = runner.invoke(cli, ["lab", "wipe", lab_id, "--yes"])
    assert res_wipe.exit_code == 0
    assert "overlays wiped" in res_wipe.output

    # Console
    res_console = runner.invoke(cli, ["console", lab_id, "cn1"])
    assert res_console.exit_code == 0
    assert "telnet://127.0.0.1:31001" in res_console.output

    # Day-0
    res_day0 = runner.invoke(cli, ["day0", lab_id, "--routing", "ospf"])
    assert res_day0.exit_code == 0
    assert "Provisioned Day-0" in res_day0.output

    # Delete
    res_del = runner.invoke(cli, ["lab", "delete", lab_id, "--yes"])
    assert res_del.exit_code == 0
    assert "[OK] Lab" in res_del.output


def test_cli_convert(runner, tmp_path):
    """Tests lab conversion via CLI: import and export."""
    clab_content = """
name: cli-clab-import
topology:
  nodes:
    clab-r1:
      kind: linux
      image: alpine:latest
"""
    clab_file = tmp_path / "test.clab.yml"
    clab_file.write_text(clab_content, encoding="utf-8")

    # Import
    res_import = runner.invoke(cli, ["convert", "import", str(clab_file)])
    assert res_import.exit_code == 0
    assert "Auto-converted successfully" in res_import.output

    # Export
    out_file = tmp_path / "exported.clab.yml"
    res_export = runner.invoke(cli, ["convert", "export", "cli-clab-import", "clab", "--output", str(out_file)])
    assert res_export.exit_code == 0
    assert out_file.exists()
    assert "clab-r1" in out_file.read_text(encoding="utf-8")
