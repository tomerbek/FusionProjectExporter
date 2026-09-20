"""Export all designs in the current Fusion project, or selected cloud files."""

import os
import json
import re
import traceback
import time
import uuid

import adsk.core
import adsk.fusion


_dialog_handlers = []

DESIGN_FORMATS = {
    'Fusion archive (.f3d/.f3z)': ('archive', '.f3d'),
    '3MF (.3mf)': ('3mf', '.3mf'),
    'IGES (.iges)': ('iges', '.iges'),
    'OBJ (.obj)': ('obj', '.obj'),
    'SAT (.sat)': ('sat', '.sat'),
    'SMT (.smt)': ('smt', '.smt'),
    'STEP (.step)': ('step', '.step'),
    'STL (.stl)': ('stl', '.stl'),
    'USD (.usd)': ('usd', '.usd'),
}


class _DialogCreated(adsk.core.CommandCreatedEventHandler):
    def __init__(self, result):
        super().__init__()
        self.result = result

    def notify(self, args):
        command = args.command
        inputs = command.commandInputs
        scope = inputs.addDropDownCommandInput(
            'scope', 'Files', adsk.core.DropDownStyles.TextListDropDownStyle)
        scope.listItems.add('Choose a project folder', True, '')
        scope.listItems.add('All files in current project', False, '')
        scope.listItems.add('Selected files', False, '')
        scope.listItems.add('All projects in active hub', False, '')
        fmt = inputs.addDropDownCommandInput(
            'format', 'Design format', adsk.core.DropDownStyles.TextListDropDownStyle)
        for index, label in enumerate(DESIGN_FORMATS):
            fmt.listItems.add(label, index == 0, '')
        handler = _DialogExecute(self.result)
        command.execute.add(handler)
        _dialog_handlers.append(handler)
        handler = _DialogDestroy(self.result)
        command.destroy.add(handler)
        _dialog_handlers.append(handler)


class _DialogExecute(adsk.core.CommandEventHandler):
    def __init__(self, result):
        super().__init__()
        self.result = result

    def notify(self, args):
        inputs = args.command.commandInputs
        self.result['scope'] = inputs.itemById('scope').selectedItem.name
        self.result['format'] = inputs.itemById('format').selectedItem.name


class _DialogDestroy(adsk.core.CommandEventHandler):
    def __init__(self, result):
        super().__init__()
        self.result = result

    def notify(self, args):
        self.result['done'] = True


def choose_options(ui):
    result = {'done': False}
    command_id = 'FusionProjectExporterOptions_' + uuid.uuid4().hex
    definition = ui.commandDefinitions.addButtonDefinition(
        command_id, 'Export Fusion project', 'Choose files and export format')
    handler = _DialogCreated(result)
    definition.commandCreated.add(handler)
    _dialog_handlers.append(handler)
    try:
        definition.execute()
        while not result['done']:
            adsk.doEvents()
            time.sleep(0.01)
    finally:
        try:
            if definition.isValid:
                definition.deleteMe()
        except RuntimeError:
            # Fusion can release the definition itself when Cancel ends the command.
            pass
        _dialog_handlers.clear()
    return result if 'scope' in result else None


def safe_name(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .') or 'Untitled'


def unique_stem(directory, name, suffix):
    stem = safe_name(name)
    candidate = stem
    index = 2
    extensions = ('.f3d', '.f3z') if suffix == '.f3d' else (suffix,)
    while any(os.path.exists(os.path.join(directory, candidate + ext))
              for ext in extensions):
        candidate = '{} ({})'.format(stem, index)
        index += 1
    return candidate


def walk(folder, parts=(), should_stop=None):
    if should_stop:
        adsk.doEvents()
        if should_stop():
            return
    for i in range(folder.dataFiles.count):
        if should_stop:
            adsk.doEvents()
            if should_stop():
                return
        yield folder.dataFiles.item(i), parts
    for i in range(folder.dataFolders.count):
        if should_stop:
            adsk.doEvents()
            if should_stop():
                return
        child = folder.dataFolders.item(i)
        yield from walk(child, parts + (safe_name(child.name),), should_stop)


def folder_parts(folder):
    parts = []
    while folder and not folder.isRoot:
        parts.insert(0, safe_name(folder.name))
        folder = folder.parentFolder
    return tuple(parts)


def project_for(app):
    if app.data.activeProject:
        return app.data.activeProject
    document = app.activeDocument
    if document and document.dataFile:
        return document.dataFile.parentFolder.parentProject
    folder = app.data.activeFolder
    return folder.parentProject if folder else None


def run(context, choices=None):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        project = project_for(app)
        if not project and not app.data.activeHub:
            ui.messageBox('Open a saved design or select a project in the Data Panel first.')
            return

        if choices is None:
            choices = choose_options(ui)
        if not choices:
            return
        export_format, suffix = DESIGN_FORMATS[choices['format']]
        scope = choices['scope']
        if scope == 'All projects in active hub':
            hub = app.data.activeHub
            if not hub:
                ui.messageBox('Select a hub in the Data Panel first.')
                return
            entries = None  # Fetch projects only after the local destination is chosen.
            has_entries = True
            root_name = safe_name(hub.name)
        elif scope == 'All files in current project':
            if not project:
                ui.messageBox('Select a project in the Data Panel first.')
                return
            entries = list(walk(project.rootFolder))
            root_name = safe_name(project.name)
        elif scope == 'Choose a project folder':
            if not project:
                ui.messageBox('Select a project in the Data Panel first.')
                return
            folder_picker = ui.createCloudFolderDialog()
            folder_picker.title = 'Choose a Fusion project folder to export'
            folder_picker.initialFolder = app.data.activeFolder or project.rootFolder
            if folder_picker.showDialog() != adsk.core.DialogResults.DialogOK:
                return
            folder = folder_picker.dataFolder
            selected_project = folder.parentProject
            entries = list(walk(folder, folder_parts(folder)))
            root_name = safe_name(selected_project.name)
        else:
            if not project:
                ui.messageBox('Select a project in the Data Panel first.')
                return
            picker = ui.createCloudFileDialog()
            picker.title = 'Select files: Shift for a range; Ctrl/Command to add files'
            picker.isMultiSelectEnabled = True
            picker.dataFolder = project.rootFolder
            if picker.showOpen() != adsk.core.DialogResults.DialogOK:
                return
            # CloudFileDialog.dataFiles is a DataFileVector (Python sequence),
            # not the DataFiles collection used by project folders.
            entries = [(data_file, folder_parts(data_file.parentFolder))
                       for data_file in picker.dataFiles]
            root_name = safe_name(project.name)

        if scope != 'All projects in active hub':
            has_entries = bool(entries)
            progress_max = max(1, len(entries))
            entries = ((data_file, parts, index, root_name)
                       for index, (data_file, parts) in enumerate(entries, 1))
        if not has_entries:
            ui.messageBox('No files found.')
            return
        destination = ui.createFolderDialog()
        destination.title = 'Choose a local export folder'
        if destination.showDialog() != adsk.core.DialogResults.DialogOK:
            return
        root = os.path.join(destination.folder, root_name)
        os.makedirs(root, exist_ok=True)
        progress = ui.createProgressDialog()
        progress.isCancelButtonShown = True
        progress.cancelButtonText = 'STOP EXPORT'
        if scope == 'All projects in active hub':
            progress.show('Exporting Fusion files', 'Loading projects in hub...', 0, 1)
            try:
                projects = list(hub.dataProjects)
            except Exception:
                progress.hide()
                raise
            if not projects:
                progress.hide()
                ui.messageBox('No projects found in this hub.')
                return
            entries = ((data_file, parts, index, data_project.name)
                       for index, data_project in enumerate(projects, 1)
                       for data_file, parts in walk(
                           data_project.rootFolder, (safe_name(data_project.name),),
                           lambda: progress.wasCancelled))
            progress_max = len(projects)
            progress.maximumValue = progress_max
            progress.message = 'Projects loaded. Starting export...'
        else:
            progress.show('Exporting Fusion files', 'Preparing export...', 0, progress_max)
        manifest_path = os.path.join(root, '.fusion-export-manifest.json')
        try:
            with open(manifest_path, 'r', encoding='utf-8') as manifest_file:
                manifest = json.load(manifest_file)
        except (OSError, ValueError):
            manifest = {}

        exported = []
        unchanged = []
        skipped = []
        failed = []
        cancelled = False
        processed = 0
        try:
          for data_file, parts, step, project_name in entries:
            progress.progressValue = min(step - 1, progress_max)
            progress.message = 'Project: {}\nFile: {}'.format(project_name, data_file.name)
            adsk.doEvents()
            if progress.wasCancelled:
                cancelled = True
                break
            extension = (data_file.fileExtension or '').lower().lstrip('.')
            target_dir = os.path.join(root, *parts)
            os.makedirs(target_dir, exist_ok=True)
            name = data_file.name
            file_id = data_file.id
            version = data_file.versionId
            manifest_key = file_id + ':' + export_format
            previous = manifest.get(manifest_key, {})
            previous_path = os.path.join(root, previous.get('path', ''))
            open_document = None
            for i in range(app.documents.count):
                existing = app.documents.item(i)
                if existing.dataFile and existing.dataFile.id == file_id:
                    open_document = existing
                    break
            if (previous.get('version') == version and previous.get('path')
                    and os.path.isfile(previous_path)
                    and not (open_document and open_document.isModified)):
                unchanged.append(name)
                continue
            if extension in ('f3d', 'f3z'):
                document = None
                opened_here = False
                try:
                    # Reuse an open document so unsaved user edits are never discarded.
                    document = open_document
                    opened_here = document is None
                    if opened_here:
                        document = app.documents.open(data_file, False)
                    fusion_document = adsk.fusion.FusionDocument.cast(document)
                    if not fusion_document or not fusion_document.design:
                        skipped.append(name + ' (not a design)')
                        continue
                    manager = fusion_document.design.exportManager
                    archive_name = os.path.splitext(name)[0] if name.lower().endswith(('.f3d', '.f3z')) else name
                    path = os.path.join(target_dir, unique_stem(target_dir, archive_name, suffix) + suffix)
                    if export_format == 'archive':
                        options = manager.createFusionArchiveExportOptions(path)
                    elif export_format == '3mf':
                        options = manager.createC3MFExportOptions(
                            fusion_document.design.rootComponent, path)
                    elif export_format == 'obj':
                        options = manager.createOBJExportOptions(
                            fusion_document.design.rootComponent, path)
                    elif export_format == 'stl':
                        options = manager.createSTLExportOptions(
                            fusion_document.design.rootComponent, path)
                    else:
                        method = {
                            'iges': manager.createIGESExportOptions,
                            'sat': manager.createSATExportOptions,
                            'smt': manager.createSMTExportOptions,
                            'step': manager.createSTEPExportOptions,
                            'usd': manager.createUSDExportOptions,
                        }[export_format]
                        options = method(path)
                    if not options:
                        raise RuntimeError('Fusion could not create export options for ' + export_format)
                    if not manager.execute(options):
                        raise RuntimeError('Fusion reported export failure')
                    exported.append(name)
                    actual_path = path if os.path.isfile(path) else os.path.splitext(path)[0] + '.f3z'
                    if os.path.isfile(actual_path) and not (open_document and open_document.isModified):
                        manifest[manifest_key] = {'version': version,
                                             'path': os.path.relpath(actual_path, root)}
                except Exception as exc:
                    failed.append('{}: {}'.format(name, exc))
                finally:
                    if document and opened_here:
                        document.close(False)
            else:
                try:
                    filename = safe_name(name)
                    if extension and not filename.lower().endswith('.' + extension):
                        filename += '.' + extension
                    stem, ext = os.path.splitext(filename)
                    path = os.path.join(target_dir, filename)
                    index = 2
                    while os.path.exists(path):
                        path = os.path.join(target_dir, '{} ({}){}'.format(stem, index, ext))
                        index += 1
                    if not data_file.download(path, None):
                        raise RuntimeError('Fusion reported download failure')
                    exported.append(name)
                    if os.path.isfile(path):
                        manifest[manifest_key] = {'version': version,
                                             'path': os.path.relpath(path, root)}
                except Exception as exc:
                    failed.append('{}: {}'.format(name, exc))

            processed += 1
            if processed % 10 == 0:
                with open(manifest_path, 'w', encoding='utf-8') as manifest_file:
                    json.dump(manifest, manifest_file, indent=2)
        finally:
            cancelled = cancelled or progress.wasCancelled
            progress.hide()

        with open(manifest_path, 'w', encoding='utf-8') as manifest_file:
            json.dump(manifest, manifest_file, indent=2)
        report = 'Exported: {}\nAlready current: {}\nSkipped: {}\nFailed: {}\nFolder: {}'.format(
            len(exported), len(unchanged), len(skipped), len(failed), root)
        if cancelled:
            report = 'Cancelled. Completed files were kept.\n\n' + report
        if skipped:
            report += '\n\nSkipped:\n' + '\n'.join(skipped[:20])
        if failed:
            report += '\n\nFailed:\n' + '\n'.join(failed[:20])
        ui.messageBox(report)
    except Exception:
        ui.messageBox('Export stopped:\n' + traceback.format_exc())
