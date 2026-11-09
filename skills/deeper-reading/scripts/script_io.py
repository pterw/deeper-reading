"""Output and CLI boundaries shared by the document tools."""
from pathlib import Path
import os
import sys
import tempfile


def validate_output(out: Path, *, inputs=(), root: Path | None = None) -> None:
    out = Path(out)
    resolved = out.resolve()
    if out.is_symlink():
        raise ValueError(f'output must not be a symbolic link: {out}')
    if root is not None:
        try:
            resolved.relative_to(Path(root).resolve())
        except ValueError as exc:
            raise ValueError(f'output escapes run root: {out}') from exc
    for source in inputs:
        source = Path(source)
        if resolved == source.resolve() or (out.exists() and source.exists() and out.samefile(source)):
            raise ValueError(f'output would overwrite input: {source}')


def write_text_atomic(out: Path, text: str, *, inputs=(), root: Path | None = None) -> None:
    """Publish a complete artifact; never truncate an input or a previous output."""
    out = Path(out)
    validate_output(out, inputs=inputs, root=root)
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         dir=out.parent, prefix=f'.{out.name}.', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        validate_output(out, inputs=inputs, root=root)
        os.replace(temporary, out)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run_cli(main) -> int:
    """Report operational failures at the CLI boundary; library calls still raise."""
    try:
        return main()
    except Exception as exc:
        print(f'FAIL: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
