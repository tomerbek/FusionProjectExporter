"""Toolbar launcher for the sibling FusionProjectExporter script."""

import importlib.util
import os
import traceback

import adsk.core


COMMAND_ID = 'FusionProjectExporterToolbarButton'
EVENT_ID = 'FusionProjectExporterToolbarLaunch'
PANEL_ID = 'FusionProjectExporterPanel'
WORKSPACE_ID = 'FusionSolidEnvironment'
_handlers = []
_pending_choices = None
_queued_choices = None
_export_running = False
_exporter = None


class ButtonCreated(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        inputs = args.command.commandInputs
        scope = inputs.addDropDownCommandInput(
            'scope', 'Files', adsk.core.DropDownStyles.TextListDropDownStyle)
        for index, label in enumerate((
                'Choose a project folder', 'All files in current project',
                'Selected files', 'All projects in active hub')):
            scope.listItems.add(label, index == 0, '')
        fmt = inputs.addDropDownCommandInput(
            'format', 'Design format', adsk.core.DropDownStyles.TextListDropDownStyle)
        for index, label in enumerate(_exporter.DESIGN_FORMATS):
            fmt.listItems.add(label, index == 0, '')
        handler = ButtonExecuted()
        args.command.execute.add(handler)
        _handlers.append(handler)
        handler = ButtonDestroyed()
        args.command.destroy.add(handler)
        _handlers.append(handler)


class ButtonExecuted(adsk.core.CommandEventHandler):
    def notify(self, args):
        global _pending_choices
        if _export_running or _queued_choices is not None:
            return
        inputs = args.command.commandInputs
        _pending_choices = {
            'scope': inputs.itemById('scope').selectedItem.name,
            'format': inputs.itemById('format').selectedItem.name,
        }


class ButtonDestroyed(adsk.core.CommandEventHandler):
    def notify(self, args):
        global _pending_choices, _queued_choices
        if _pending_choices is not None and _queued_choices is None:
            _queued_choices = _pending_choices
            _pending_choices = None
            # Fusion handles this queued event after the dialog command ends.
            adsk.core.Application.get().fireCustomEvent(EVENT_ID)
        else:
            _pending_choices = None


class LaunchExporter(adsk.core.CustomEventHandler):
    def notify(self, args):
        global _queued_choices, _export_running
        if _queued_choices is None or _export_running:
            return
        choices = _queued_choices
        _queued_choices = None
        _export_running = True
        app = adsk.core.Application.get()
        panel = app.userInterface.allToolbarPanels.itemById(PANEL_ID)
        control = panel.controls.itemById(COMMAND_ID) if panel else None
        try:
            if control:
                control.isEnabled = False
            _exporter.run({}, choices)
        except Exception:
            app.userInterface.messageBox('Could not launch exporter:\n' + traceback.format_exc())
        finally:
            if control and control.isValid:
                control.isEnabled = True
            _export_running = False


def run(context):
    global _exporter
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'FusionProjectExporter',
            'FusionProjectExporter.py'))
        spec = importlib.util.spec_from_file_location('fusion_project_exporter_core', path)
        _exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_exporter)
        event = app.registerCustomEvent(EVENT_ID)
        if not event:
            raise RuntimeError('Could not register export launch event')
        handler = LaunchExporter()
        event.add(handler)
        _handlers.append(handler)

        definition = ui.commandDefinitions.itemById(COMMAND_ID)
        if definition:
            definition.deleteMe()
        definition = ui.commandDefinitions.addButtonDefinition(
            COMMAND_ID, 'Export Project', 'Export Fusion project files locally',
            os.path.join(os.path.dirname(__file__), 'Resources', 'ExportProject'))
        handler = ButtonCreated()
        definition.commandCreated.add(handler)
        _handlers.append(handler)

        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        if not workspace:
            raise RuntimeError('Fusion Design workspace was not found')
        utilities_tab = None
        for tab in workspace.toolbarTabs:
            if tab.name.strip().upper() == 'UTILITIES':
                utilities_tab = tab
                break
        if not utilities_tab:
            raise RuntimeError('Fusion Utilities tab was not found')
        panel = ui.allToolbarPanels.itemById(PANEL_ID)
        if not panel:
            panel = utilities_tab.toolbarPanels.add(PANEL_ID, 'EXPORT')
        if not panel:
            raise RuntimeError('Could not add Export panel to Utilities tab')
        control = panel.controls.addCommand(definition)
        control.isPromotedByDefault = True
        control.isPromoted = True
    except Exception:
        ui.messageBox('Could not install exporter button:\n' + traceback.format_exc())


def stop(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    panel = ui.allToolbarPanels.itemById(PANEL_ID)
    if panel:
        control = panel.controls.itemById(COMMAND_ID)
        if control:
            control.deleteMe()
        panel.deleteMe()
    definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if definition:
        definition.deleteMe()
    app.unregisterCustomEvent(EVENT_ID)
    _handlers.clear()
