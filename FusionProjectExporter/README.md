# Fusion Project Exporter

Run `FusionProjectExporter.py` from **Utilities → Scripts and Add-Ins** in Autodesk Fusion. Add the `FusionProjectExporter` folder as a script if needed.

## Toolbar button

The sibling `FusionProjectExporterToolbar` folder is a Fusion add-in. In **Utilities → Scripts and Add-Ins**, open the **Add-Ins** tab, use the **+** button to add that folder, then run it once. A dedicated **EXPORT** panel with an **Export Project** button appears directly on the **UTILITIES** ribbon in the Design workspace. The button's dialog contains the scope and format dropdowns; Cancel closes it without starting an export. The add-in manifest sets `runOnStartup` to `true`, so Fusion loads the button on later launches. Keep both folders together because the toolbar add-in calls the exporter script in the sibling folder. If the button does not show after editing the code, stop and run the add-in again.

1. Open a saved design in the project, or select a folder in its Data Panel.
2. Run the script and choose the file scope and design export format from the dropdowns.
3. Choose a local destination folder.

**Choose a project folder** opens Fusion's cloud folder picker and exports only that folder and its subfolders. The local structure starts with the chosen folder's actual parent project, followed by the chosen folder (for example, `Wagner biro/700023`). **All files in current project** exports that project's full tree. **All projects in active hub** exports every project in the hub shown in the Data Panel, with a separate local folder per project. **Selected files** opens Fusion's cloud multi-file picker; use **Shift** for a range or **Ctrl** on Windows / **Command** on Mac to add individual files. For Fusion designs, choose archive (`.f3d`, or `.f3z` for external references), 3MF, IGES, OBJ, SAT, SMT, STEP, STL, or USD. Only the Fusion archive preserves Fusion's editable timeline and sketches. Other cloud files are downloaded in their original format regardless of the design format choice. Existing local files are kept; a numbered filename is used for duplicates. The script reports successes and failures when finished.

The dropdown covers whole-design formats exposed by Fusion's Design ExportManager. Drawing-only formats (such as PDF) and exports requiring a chosen sketch, flat pattern, toolpath, or manufacturing setup are separate workflows and are not included in this project-wide design dropdown.

For a whole-hub export, choose the local destination before Fusion loads the hub's projects. A progress dialog then shows the project and file being processed and has a **STOP EXPORT** button. The stop request is checked between files and while walking folders; a single Fusion open or export operation may still take time to finish. Completed exports remain on disk, and the manifest is saved periodically so a later run can skip files already exported at the same version.

This script needs Fusion's built-in Python API and cannot run with ordinary system Python. Test it on a small project before using it for a large export.

On later runs to the same destination, the script reads `.fusion-export-manifest.json` and skips files whose cloud version has not changed and whose local export still exists. A modified design already open in Fusion is exported again. The first run still has to open each Fusion design, because Fusion's `DataFile.download` does not support native Fusion design files.
