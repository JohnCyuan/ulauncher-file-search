""" Main Module """

import logging
import os
import subprocess
import ipdb
import time
from ulauncher.api.client.EventListener import EventListener
# pylint: disable=import-error
from ulauncher.api.client.Extension import Extension
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem

LOGGING = logging.getLogger(__name__)

FILE_SEARCH_ALL = 'ALL'

FILE_SEARCH_DIRECTORY = 'DIR'

FILE_SEARCH_FILE = 'FILE'


class FileSearchExtension(Extension):
  """ Main Extension Class  """

  def __init__(self):
    """ Initializes the extension """
    super(FileSearchExtension, self).__init__()
    self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())

  def search(self, query, file_type=None, add_extension=False):
    """ Searches for Files using fd command """
    cmd = ['timeout', '15s', 'ionice', '-c', '3', 'fd', '--hidden']
    if file_type == FILE_SEARCH_FILE:
      cmd.append('-t')
      cmd.append('f')
    elif file_type == FILE_SEARCH_DIRECTORY:
      cmd.append('-t')
      cmd.append('d')

    if add_extension:
      cmd.append('-e')
      index = query.rfind('.')
      cmd.append(query[index + 1:])
      cmd.append(query[:index])
    else:
      cmd.append(query)
    cmd.append(self.preferences['base_dir'])
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    out, err = process.communicate()
    # ipdb.set_trace()
    if err:
      self.logger.error(err)
      return []

    files = out.decode("utf-8").split('\n')
    files = filter(None, files)  # remove empty lines

    result = []

    # pylint: disable=C0103
    for f in files:
      filename, file_extension = os.path.splitext(f)
      if file_extension:
        icon = 'images/file.png'
      else:
        icon = 'images/folder.png'

      result.append({
        'path': f,
        'name': filename,
        'icon': icon
      })

    return result

  def get_open_in_terminal_script(self, path):
    """ Returns the script based on the type of terminal """
    terminal_emulator = self.preferences['terminal_emulator']

    # some terminals might work differently. This is already prepared for that.
    if terminal_emulator in ['gnome-terminal', 'terminator', 'tilix', 'xfce-terminal']:
      return RunScriptAction(terminal_emulator, ['--working-directory', path])

    return DoNothingAction()


class KeywordQueryEventListener(EventListener):
  """ Listener that handles the user input """
  start_time = time.time()

  # pylint: disable=unused-argument,no-self-use
  def on_event(self, event, extension):
    """ Handles the event """
    items = []
    query = event.get_argument()
    if not query or len(query) < 2:
      return RenderResultListAction([ExtensionResultItem(
        icon='images/icon.png',
        name='Keep typing your search criteria ...',
        on_enter=DoNothingAction())])

    keyword = event.get_keyword()
    # Find the keyword id using the keyword (since the keyword can be changed by users)
    for kwId, kw in extension.preferences.items():
      if kw == keyword:
        keywordId = kwId
    add_extension = False
    file_type = FILE_SEARCH_ALL
    if keywordId == "ff_kw":
      file_type = FILE_SEARCH_FILE
    if keywordId == "ffe_kw":
      file_type = FILE_SEARCH_FILE
      add_extension = True
    elif keywordId == "fd_kw":
      file_type = FILE_SEARCH_DIRECTORY

    results = extension.search(query.strip(), file_type, add_extension)
    if not results:
      return RenderResultListAction([ExtensionResultItem(
        icon='images/icon.png',
        name='No Results found matching %s' % query,
        on_enter=HideWindowAction())])

    items = []
    for result in results[:15]:
      items.append(ExtensionSmallResultItem(
        icon=result['icon'],
        name=result['path'],
        on_enter=OpenAction(result['path']),
        on_alt_enter=extension.get_open_in_terminal_script(
          result['path'])
      ))

    return RenderResultListAction(items)


if __name__ == '__main__':
  FileSearchExtension().run()
