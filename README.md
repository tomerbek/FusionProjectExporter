# Fusion Project Exporter

Export Autodesk Fusion cloud designs and other project files to a local folder. The add-in places an **Export Project** button in an **EXPORT** panel on Fusion's **UTILITIES** tab.

## Install

1. Download the release ZIP and extract it. Keep `FusionProjectExporter` and `FusionProjectExporterToolbar` next to each other.
2. In Fusion, open **Utilities → Scripts and Add-Ins → Add-Ins**.
3. Click **+** and select `FusionProjectExporterToolbar/FusionProjectExporterToolbar.py` from the extracted folder. Run the add-in once.
4. The **Export Project** button appears on the **UTILITIES** tab. It is configured to load when Fusion starts.

The standalone script can also be added from **Scripts and Add-Ins → Scripts** by selecting `FusionProjectExporter/FusionProjectExporter.py`.

## Use

Click **Export Project**, choose a scope and design format, then choose a local destination. The scopes are:

- **Choose a project folder:** Pick a Fusion folder and export it with its subfolders. The local path starts with its actual parent project name.
- **All files in current project:** Export the project currently displayed in the Data Panel.
- **Selected files:** Choose multiple cloud files with Shift or Ctrl/Command.
- **All projects in active hub:** Export each project in the active hub to a separate local project folder.

The design formats are Fusion archive (`.f3d` or `.f3z`), 3MF, IGES, OBJ, SAT, SMT, STEP, STL, and USD. Fusion archive is the default and preserves the editable design history. Other file types download in their original format. Folder structure is preserved, and existing local files are never overwritten; new exports receive a numbered filename.

On repeat runs to the same destination, unchanged saved cloud versions are skipped using `.fusion-export-manifest.json` in the export folder. The progress dialog's **STOP EXPORT** button stops between files and while traversing folders. A single Fusion open, export, or download call may need to finish first. Files completed before stopping remain on disk.

## Limits

- Exports run inside the Fusion desktop app and require access to the cloud project.
- The script processes files sequentially. Large designs and hubs can take substantial time.
- The format dropdown covers whole-design exports. Drawing PDF/DXF and sketch, flat-pattern, or CAM-specific exports require separate workflows.
- Fusion archives are suitable for preserving the editable design. STEP, mesh, and other interchange formats do not preserve Fusion's timeline and sketches.
- This project is an independent community tool and is not affiliated with Autodesk.

See [detailed usage notes](FusionProjectExporter/README.md) and [release notes](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).
