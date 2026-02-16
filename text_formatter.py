import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class TextFormatter:
    """
    Simple markdown-based (*very* lightweight) formatter to HTML using HTML template.

    **How to use (CLI)**
    - Call the `execute` function of this class in a script (main.py, for example) and run the script with optional flags:
        - `python main.py -i text.md -o output.html -t template.html`
    - Defaults (when omitted):
        - `-i/--input`: `text.md`
        - `-o/--output`: `output.html`
        - `-t/--template`: `template.html`

    **How to use (Python API)**
    - Call `TextFormatter.execute(input_file_path, output_file_path, template_file_path)`.

    **Template**
    - The template is normal HTML with *placeholders* in the format `$key$`.
    - Keys come from the input's metadata block (below) and there's also `$body$`, which is
        the already formatted content.
    - If a key doesn't exist in the metadata, it remains literal in the output.

    **Input (`.md`) and metadata**
    - Optionally, the file can start with a YAML-style block between `---` and `---`:

        ---
        title: My Title
        date: February 15, 2026
        author: John Doe
        ---

    - Each line `key: value` becomes a metadata entry.

    **Supported marks in the body**
    The body is transformed by applying the patterns below (in order):
    - Bold: `**text**` → `<b>text</b>`
    - Italic: `*text*` → `<i>text</i>`
    - Italic (alternative): `_text_` → `<i>text</i>`
    - Strikethrough: `~~text~~` → `<s>text</s>`
    - Heading level 1: `# Heading` → `<h1>Heading</h1>`

    **Paragraphs (important)**
    - Each "normal" line becomes a paragraph: `A line` → `<p>A line</p>`.
        That is: line breaks in the input generate separate paragraphs in HTML.

    **Stanzas / verse blocks**
    - A block wrapped by lines containing only `/` becomes:

        /
        line 1
        line 2
        /

        ...and is converted to `<div class=stanza>...</div>`, and then each internal line becomes `<p>`.

    **Notes**
    - Multiple spaces are reduced and multiple blank lines are compacted.
    """

    @dataclass
    class Regex:
        match_pattern: str
        replace_pattern: str
        flags: re.RegexFlag = re.NOFLAG

    _REPLACE_REGEXES = [
        Regex(
            match_pattern=r"\n{2,}",
            replace_pattern=r"\n",
        ),
        Regex(
            match_pattern=r" {2,}",
            replace_pattern=r" ",
        ),
        Regex(
            match_pattern=r"^\s+|\s+$",
            replace_pattern=r"",
        ),
        Regex(
            match_pattern=r"\n*$",
            replace_pattern=r"\n",
        ),
        Regex(
            match_pattern=r"\*\*(.*?)\*\*",
            replace_pattern=r"<b>\1</b>",
        ),
        Regex(
            match_pattern=r"\*(.*?)\*",
            replace_pattern=r"<i>\1</i>",
        ),
        Regex(
            match_pattern=r"\_(.*?)\_",
            replace_pattern=r"<i>\1</i>",
        ),
        Regex(
            match_pattern=r"\~\~(.*?)\~\~",
            replace_pattern=r"<s>\1</s>",
        ),
        Regex(
            match_pattern=r"#\s*(.*)",
            replace_pattern=r"<h1>\1</h1>",
        ),
        Regex(
            match_pattern=r"^\/\n(.*?)\n\/$",
            replace_pattern=r"<div class=stanza>\n\1\n</div>",
            flags=re.MULTILINE | re.S,
        ),
        Regex(
            match_pattern=r"^(?!<)(?!.*>\n)(.*?)\n",
            replace_pattern=r"<p>\1</p>",
            flags=re.MULTILINE,
        ),
    ]

    @staticmethod
    def _log(
        level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        message: str,
    ) -> None:
        print(f"{(f'[{level}]'):12} {message}")

    @staticmethod
    def execute() -> None:
        try:
            parser = TextFormatter._build_cli_parser()
            args = parser.parse_args()

            log = TextFormatter._log
            log("INFO", "Starting Text Formatter execution...")

            input_file_path = args.input_file_path
            output_file_path = args.output_file_path
            template_file_path = args.template_file_path

            log("INFO", "Reading input file...")
            input_file_content = TextFormatter._read_file(
                input_file_path,
            )

            log("INFO", "Reading template file...")
            template_file_content = TextFormatter._read_file(
                template_file_path,
            )

            log("INFO", "Extracting input file metadata...")
            metadata, input_file_content_without_metadata = (
                TextFormatter._extract_metadata(
                    input_file_content,
                )
            )

            log("INFO", "Replacing file marks...")
            input_file_content_replaced = TextFormatter._replace_file_marks(
                input_file_content_without_metadata,
            )

            log("INFO", "Merging with template file...")
            input_file_content_merged = TextFormatter._merge_with_template(
                input_file_content_replaced,
                template_file_content,
                metadata,
            )

            log("INFO", "Saving output HTML file...")
            TextFormatter._write_file(
                output_file_path,
                input_file_content_merged,
            )

            log("INFO", "File Formatter finished successfully.")

        except Exception as e:
            log("CRITICAL", f"{repr(e)}")

    @staticmethod
    def _build_cli_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="text-formatter",
            description="Format a simple markdown-based file into HTML using an HTML template.",
        )

        parser.add_argument(
            "-i",
            "--input",
            dest="input_file_path",
            default="input.txt",
            help="Input file path (default: %(default)s)",
        )
        parser.add_argument(
            "-o",
            "--output",
            dest="output_file_path",
            default="output.html",
            help="Output HTML file path (default: %(default)s)",
        )
        parser.add_argument(
            "-t",
            "--template",
            dest="template_file_path",
            default="template.html",
            help="HTML template file path (default: %(default)s)",
        )

        return parser

    @staticmethod
    def _extract_metadata(
        content: str,
    ) -> tuple[dict[str, str], str]:
        block_match = re.search(
            r"^---\s*\n(.*?)\n---",
            content,
            re.DOTALL,
        )

        if not block_match:
            return {}, content

        block = block_match.group(1)

        metadata = dict(
            re.findall(
                r"^\s*([\w\-]+)\s*:\s*(.+?)\s*$",
                block,
                re.MULTILINE,
            )
        )

        start, end = block_match.span()
        content_without_metadata = content[:start] + content[end:]

        return metadata, content_without_metadata

    @staticmethod
    def _replace_file_marks(
        content: str,
    ) -> str:
        content_replaced = content
        for replace_regex in TextFormatter._REPLACE_REGEXES:
            content_replaced = re.sub(
                replace_regex.match_pattern,
                replace_regex.replace_pattern,
                content_replaced,
                0,
                replace_regex.flags,
            )

        return content_replaced

    @staticmethod
    def _merge_with_template(
        to_merge_content: str,
        template_content: str,
        metadata: dict[str, str],
    ) -> str:
        metadata["body"] = to_merge_content

        def replacer(
            match: re.Match,
        ) -> str:
            key = match.group(1)
            return metadata.get(key, match.group(0))

        return re.sub(
            r"\$([A-Za-z0-9_\-]+)\$",
            lambda match: metadata.get(
                match.group(1),
                match.group(0),
            ),
            template_content,
        )

    @staticmethod
    def _read_file(
        file_path: Path,
        encoding: str = "utf-8",
    ) -> str:
        with open(
            file=file_path,
            mode="r",
            encoding=encoding,
        ) as file:
            return file.read()

    @staticmethod
    def _write_file(
        file_path: Path,
        content: str,
        encoding: str = "utf-8",
    ) -> None:
        with open(
            file=file_path,
            mode="w",
            encoding=encoding,
        ) as file:
            file.write(content)
