"""Validate and package the Fusion Project Exporter release."""

import ast
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
VERSION = '0.1.0'
ADDIN = ROOT / 'FusionProjectExporterToolbar'
SCRIPT = ROOT / 'FusionProjectExporter'


def main():
    for folder in (ADDIN, SCRIPT):
        name = folder.name
        ast.parse((folder / (name + '.py')).read_text(encoding='utf-8'))
        manifest = json.loads((folder / (name + '.manifest')).read_text(encoding='utf-8'))
        assert manifest['version'] == VERSION
        assert manifest['type'] == ('addin' if folder == ADDIN else 'script')

    icon_folder = ADDIN / 'Resources' / 'ExportProject'
    for name in ('16x16.svg', '32x32.svg',
                 '16x16-dark_blue.svg', '32x32-dark_blue.svg'):
        ET.parse(icon_folder / name)

    included = [ROOT / name for name in ('README.md', 'CHANGELOG.md', 'LICENSE')]
    for folder in (ADDIN, SCRIPT):
        included.extend(path for path in folder.rglob('*')
                        if path.is_file() and not any(
                            part.startswith('.') or part == '__pycache__'
                            for part in path.relative_to(folder).parts))

    output = ROOT / 'dist' / ('FusionProjectExporter-' + VERSION + '.zip')
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(included):
            archive.write(path, path.relative_to(ROOT))
    print('{} ({} files)'.format(output, len(included)))


if __name__ == '__main__':
    main()
