from villanibench.harness.adapters.villani import DEFAULT_TEMPLATE
from villanibench.harness.adapters.external_cli import ExternalCliAdapter


def test_villani_default_template_flags_and_placeholders():
    assert '{prompt_text}' in DEFAULT_TEMPLATE
    assert '{prompt_file}' not in DEFAULT_TEMPLATE
    assert '--cwd' not in DEFAULT_TEMPLATE
    assert '--repo "{cwd}"' in DEFAULT_TEMPLATE
    for expected in [
        '--provider openai',
        '--model "{model}"',
        '--base-url "{base_url}"',
        '--api-key "{api_key}"',
        '--auto-approve',
        '--auto-accept-edits',
        '--dangerously-skip-permissions',
        '--plan-mode off',
        '--no-stream',
        '--debug trace',
    ]:
        assert expected in DEFAULT_TEMPLATE


def test_villani_template_renders_prompt_text_not_prompt_file():
    adapter = ExternalCliAdapter('villani', DEFAULT_TEMPLATE)
    cmd = adapter.render_command(
        DEFAULT_TEMPLATE,
        prompt_file='/tmp/prompt.txt',
        prompt_text='Fix the bug now',
        cwd='/tmp/repo',
        model='m',
        base_url='u',
        api_key='k',
        output_dir='/tmp/out',
        visible_test_command='pytest -q tests/visible',
    )
    assert 'Fix the bug now' in cmd
    assert '/tmp/prompt.txt' not in cmd
