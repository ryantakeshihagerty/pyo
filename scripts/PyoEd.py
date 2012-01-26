#! /usr/bin/env python
# encoding: utf-8
"""
PyoEd is a simple text editor especially configured to edit pyo audio programs.

You can do absolutely everything you want to do with this piece of software.

Olivier Belanger - 2012

TODO:
    - Undo / Redo in Code menu
    - ZoomIn / ZoomOut in Code Menu
    - Manula menu
    - Shortcut to play the example

"""

import sys, os, string, inspect, keyword, wx, codecs, subprocess
import wx.stc  as  stc
import wx.aui
from pyo import *

NAME = 'PyoEd'
VERSION = '0.1.0'
TEMP_PATH = os.path.join(os.path.expanduser('~'), '.pyoed')
if not os.path.isdir(TEMP_PATH):
    os.mkdir(TEMP_PATH)

def convert_line_endings(temp, mode):
        #modes:  0 - Unix, 1 - Mac, 2 - DOS
        if mode == 0:
                temp = string.replace(temp, '\r\n', '\n')
                temp = string.replace(temp, '\r', '\n')
        elif mode == 1:
                temp = string.replace(temp, '\r\n', '\r')
                temp = string.replace(temp, '\n', '\r')
        elif mode == 2:
                import re
                temp = re.sub("\r(?!\n)|(?<!\r)\n", "\r\n", temp)
        return temp

if sys.platform == "darwin":
#     # Open a new terminal window on each run
#     terminal_script = """set my_path to quoted form of POSIX path of "%s"
# set my_file to quoted form of POSIX path of "%s"
# tell application "Terminal"
#     launch
#     activate
#     do script "clear; cd " & my_path & "; /usr/local/bin/python " & my_file
# end tell
#     """
#     terminal_script_path = os.path.join(TEMP_PATH, "terminal_script.scpt")

    # Use the same terminal window for each run
    terminal_close_server_script = """tell application "Terminal" 
    close window 1
end tell
    """
    terminal_close_server_script = convert_line_endings(terminal_close_server_script, 1)
    terminal_close_server_script_path = os.path.join(TEMP_PATH, "terminal_close_server_script.scpt")

    terminal_server_script = """tell application "Terminal"
    do script ""
    set a to get id of front window
    set custom title of tab 1 of window id a to "PyoEd Output"
    set the number of columns of window 1 to 80
    set the number of rows of window 1 to 30
    set the position of window 1 to {810, 25}
end tell
    """
    terminal_server_script = convert_line_endings(terminal_server_script, 1)
    terminal_server_script_path = os.path.join(TEMP_PATH, "terminal_server_script.scpt")
    f = open(terminal_server_script_path, "w")
    f.write(terminal_server_script)
    f.close()
    pid = subprocess.Popen(["osascript", terminal_server_script_path]).pid
    
    terminal_client_script = """set my_path to quoted form of POSIX path of "%s"
set my_file to quoted form of POSIX path of "%s"
tell application "System Events"
    tell application process "Terminal"
    set frontmost to true
    keystroke "clear"
    keystroke return
    delay 0.25
    keystroke "cd " & my_path
    keystroke return
    delay 0.25
    keystroke "python " & my_file
    keystroke return
    delay 0.25
    end tell
    tell application process "PyoEd"
    set frontmost to true
    end tell
end tell
    """
    terminal_client_script_path = os.path.join(TEMP_PATH, "terminal_client_script.scpt")

################## TEMPLATES ##################
PYO_TEMPLATE = """from pyo import *

s = Server(sr=44100, nchnls=2, buffersize=512, duplex=1).boot()




s.gui(locals())
"""

CECILIA5_TEMPLATE = '''class Module(BaseModule):
    """
    Module's documentation
    
    """
    def __init__(self):
        BaseModule.__init__(self)
        self.snd = self.addSampler("snd")
        self.out = Mix(self.snd, voices=self.nchnls, mul=self.env)


Interface = [
    csampler(name="snd"),
    cgraph(name="env", label="Overall Amplitude", func=[(0,1),(1,1)], col="blue"),
    cpoly()
]
'''

ZYNE_TEMPLATE = '''class MySynth(BaseSynth):
    """
    Synth's documentation

    """
    def __init__(self, config):
        # `mode` handles pitch conversion : 1 for hertz, 2 for transpo, 3 for midi
        BaseSynth.__init__(self, config, mode=1)
        self.fm1 = FM(self.pitch, ratio=self.p1, index=self.p2, mul=self.amp*self.panL).mix(1)
        self.fm2 = FM(self.pitch*0.997, ratio=self.p1, index=self.p2, mul=self.amp*self.panR).mix(1)
        self.filt1 = Biquad(self.fm1, freq=self.p3, q=1, type=0)
        self.filt2 = Biquad(self.fm2, freq=self.p3, q=1, type=0)
        self.out = Mix([self.filt1, self.filt2], voices=2)


MODULES = {
            "MySynth": { "title": "- Generic module -", "synth": MySynth, 
                    "p1": ["Ratio", 0.5, 0, 10, False, False],
                    "p2": ["Index", 5, 0, 20, False, False],
                    "p3": ["LP cutoff", 4000, 100, 15000, False, True]
                    },
          }
'''

# Bitstream Vera Sans Mono, Corbel, Monaco, Envy Code R, MonteCarlo, Courier New
conf = {"preferedStyle": "Espresso"}
STYLES = {'Default': {'default': '#000000', 'comment': '#007F7F', 'commentblock': '#7F7F7F', 'selback': '#CCCCCC',
                    'number': '#005000', 'string': '#7F007F', 'triple': '#7F0000', 'keyword': '#00007F',
                    'class': '#0000FF', 'function': '#007F7F', 'identifier': '#000000', 'caret': '#00007E',
                    'background': '#FFFFFF', 'linenumber': '#000000', 'marginback': '#B0B0B0', 'markerfg': '#CCCCCC',
                      'markerbg': '#000000', 'bracelight': '#AABBDD', 'bracebad': '#DD0000'},

           'Custom': {'default': '#FFFFFF', 'comment': '#9FFF9F', 'commentblock': '#7F7F7F', 'selback': '#333333',
                      'number': '#90CB43', 'string': '#FF47D7', 'triple': '#FF3300', 'keyword': '#4A94FF',
                      'class': '#4AF3FF', 'function': '#00E0B6', 'identifier': '#FFFFFF', 'caret': '#DDDDDD',
                      'background': '#000000', 'linenumber': '#111111', 'marginback': '#AFAFAF', 'markerfg': '#DDDDDD',
                      'markerbg': '#404040', 'bracelight': '#AABBDD', 'bracebad': '#DD0000'},

            'Soft': {'default': '#000000', 'comment': '#444444', 'commentblock': '#7F7F7F', 'selback': '#CBCBCB',
                     'number': '#222222', 'string': '#272727', 'triple': '#333333', 'keyword': '#000000',
                     'class': '#666666', 'function': '#555555', 'identifier': '#000000', 'caret': '#222222',
                     'background': '#EFEFEF', 'linenumber': '#111111', 'marginback': '#AFAFAF', 'markerfg': '#DDDDDD',
                     'markerbg': '#404040', 'bracelight': '#AABBDD', 'bracebad': '#DD0000'},

            'Smooth': {'default': '#FFFFFF', 'comment': '#DD0000', 'commentblock': '#AF0000', 'selback': '#555555',
                       'number': '#FFFFFF', 'string': '#00EE00', 'triple': '#00AA00', 'keyword': '#9999FF',
                       'class': '#00FFA2', 'function': '#00FFD5', 'identifier': '#CCCCCC', 'caret': '#EEEEEE',
                       'background': '#222222', 'linenumber': '#111111', 'marginback': '#AFAFAF', 'markerfg': '#DDDDDD',
                       'markerbg': '#404040', 'bracelight': '#AABBDD', 'bracebad': '#DD0000'},

            'Espresso': {'default': '#BDAE9C', 'comment': '#0066FF', 'commentblock': '#0044DD', 'selback': '#5D544F',
                         'number': '#44AA43', 'string': '#2FE420', 'triple': '#049B0A', 'keyword': '#43A8ED',
                         'class': '#EE8247', 'function': '#FF9358', 'identifier': '#BDAE9C', 'caret': '#DDDDDD',
                         'background': '#2A211C', 'linenumber': '#111111', 'marginback': '#AFAFAF', 'markerfg': '#DDDDDD',
                         'markerbg': '#404040', 'bracelight': '#AABBDD', 'bracebad': '#DD0000'}
                         }
if wx.Platform == '__WXMSW__':
    faces = {'face': 'Courier', 'size' : 10, 'size2': 8}
elif wx.Platform == '__WXMAC__':
    faces = {'face': 'Monaco', 'size' : 12, 'size2': 9}
else:
    faces = {'face': 'Courier New', 'size' : 8, 'size2': 7}

styles = STYLES.keys()

for key, value in STYLES[conf['preferedStyle']].items():
    faces[key] = value
faces2 = faces.copy()
faces2['size3'] = faces2['size2'] + 4
for key, value in STYLES['Default'].items():
    faces2[key] = value

class MainFrame(wx.Frame):
    def __init__(self, parent, ID, title, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):
        wx.Frame.__init__(self, parent, ID, title, pos, size, style)

        self.panel = MainPanel(self, size=size)

        if sys.platform == "darwin":
            accel = wx.ACCEL_CMD
        else:
            accel = wx.ACCEL_CTRL
        aTable = wx.AcceleratorTable([(accel, ord('1'), 10001),
                                      (accel, ord('2'), 10002),
                                      (accel, ord('3'), 10003),
                                      (accel, ord('4'), 10004),
                                      (accel, ord('5'), 10005),
                                      (accel, ord('6'), 10006),
                                      (accel, ord('7'), 10007),
                                      (accel, ord('8'), 10008),
                                      (accel, ord('9'), 10009),
                                      (accel, ord('0'), 10010)])
        self.SetAcceleratorTable(aTable)
        
        self.menuBar = wx.MenuBar()
        menu1 = wx.Menu()
        menu1.Append(110, "New\tCtrl+N")
        self.submenu1 = wx.Menu()
        self.submenu1.Append(98, "Pyo Template")
        self.submenu1.Append(97, "Cecilia5 Template")
        self.submenu1.Append(96, "Zyne Template")
        menu1.AppendMenu(99, "New From Template", self.submenu1)
        menu1.Append(100, "Open\tCtrl+O")
        menu1.Append(112, "Open Project\tShift+Ctrl+O")
        self.submenu2 = wx.Menu()
        subId2 = 2000
        recentFiles = []
        filename = os.path.join(TEMP_PATH,'.recent.txt')
        if os.path.isfile(filename):
            f = open(filename, "r")
            for line in f.readlines():
                recentFiles.append(line)
            f.close()
        if recentFiles:
            for file in recentFiles:
                self.submenu2.Append(subId2, file)
                subId2 += 1
        menu1.AppendMenu(998, "Open Recent...", self.submenu2)
        menu1.InsertSeparator(5)
        menu1.Append(101, "Save\tCtrl+S")
        menu1.Append(102, "Save As...\tShift+Ctrl+S")
        menu1.Append(111, "Close\tCtrl+W")
        if sys.platform != "darwin":
            menu1.InsertSeparator(9)
        prefItem = menu1.Append(wx.ID_PREFERENCES, "Preferences...\tCtrl+;")
        if sys.platform != "darwin":
            menu1.InsertSeparator(11)
        quitItem = menu1.Append(wx.ID_EXIT, "Quit\tCtrl+Q")
        self.menuBar.Append(menu1, 'File')

        menu2 = wx.Menu()
        menu2.Append(150, "Undo\tCtrl+Z")
        menu2.Append(151, "Redo\tShift+Ctrl+Z")
        menu2.InsertSeparator(2)
        menu2.Append(163, "Cut\tCtrl+X")
        menu2.Append(160, "Copy\tCtrl+C")
        menu2.Append(161, "Paste\tCtrl+V")
        menu2.Append(162, "Select All\tCtrl+A")
        menu2.InsertSeparator(7)
        menu2.Append(132, "Zoom in\tCtrl+=")
        menu2.Append(133, "Zoom out\tCtrl+-")
        menu2.InsertSeparator(10)
        menu2.Append(103, "Collapse/Expand\tShift+Ctrl+F")
        menu2.Append(108, "Un/Comment Selection\tCtrl+J")
        menu2.Append(114, "Show AutoCompletion\tCtrl+K")
        menu2.Append(121, "Insert File Path...\tCtrl+P")
        menu2.InsertSeparator(15)
        menu2.Append(170, "Convert Selection to Uppercase\tCtrl+U")
        menu2.Append(171, "Convert Selection to Lowercase\tShift+Ctrl+U")
        menu2.Append(172, "Convert Tabs to Spaces")
        menu2.InsertSeparator(19)
        menu2.Append(140, "Goto line...\tCtrl+L")
        menu2.Append(122, "Find...\tCtrl+F")
        menu2.InsertSeparator(22)
        menu2.Append(180, "Show Documentation for Current Object\tCtrl+D")
        self.menuBar.Append(menu2, 'Code')

        menu3 = wx.Menu()
        menu3.Append(104, "Run\tCtrl+R")
        self.menuBar.Append(menu3, 'Process')

        menu5 = wx.Menu()
        stId = 500
        for st in styles:
            menu5.Append(stId, st, "", wx.ITEM_RADIO)
            if st == conf['preferedStyle']: menu5.Check(stId, True)
            stId += 1
        self.menuBar.Append(menu5, 'Styles')

        menu = wx.Menu()
        helpItem = menu.Append(wx.ID_ABOUT, '&About %s %s' % (NAME, VERSION), 'wxPython RULES!!!')
        self.menuBar.Append(menu, '&Help')

        self.SetMenuBar(self.menuBar)

        self.Bind(wx.EVT_MENU, self.new, id=110)
        self.Bind(wx.EVT_MENU, self.newFromTemplate, id=96, id2=98)
        self.Bind(wx.EVT_MENU, self.open, id=100)
        self.Bind(wx.EVT_MENU, self.openProject, id=112)
        self.Bind(wx.EVT_MENU, self.save, id=101)
        self.Bind(wx.EVT_MENU, self.saveas, id=102)
        self.Bind(wx.EVT_MENU, self.delete, id=111)
        self.Bind(wx.EVT_MENU, self.cut, id=163)
        self.Bind(wx.EVT_MENU, self.copy, id=160)
        self.Bind(wx.EVT_MENU, self.paste, id=161)
        self.Bind(wx.EVT_MENU, self.selectall, id=162)
        self.Bind(wx.EVT_MENU, self.undo, id=150, id2=151)
        self.Bind(wx.EVT_MENU, self.zoom, id=132, id2=133)
        self.Bind(wx.EVT_MENU, self.upperLower, id=170, id2=171)
        self.Bind(wx.EVT_MENU, self.tabsToSpaces, id=172)
        self.Bind(wx.EVT_MENU, self.gotoLine, id=140)
        self.Bind(wx.EVT_MENU, self.fold, id=103)
        self.Bind(wx.EVT_MENU, self.autoComp, id=114)
        self.Bind(wx.EVT_MENU, self.insertPath, id=121)
        self.Bind(wx.EVT_MENU, self.showFind, id=122)
        self.Bind(wx.EVT_MENU, self.runner, id=104)
        self.Bind(wx.EVT_MENU, self.onHelpAbout, helpItem)
        self.Bind(wx.EVT_MENU, self.OnComment, id=108)
        self.Bind(wx.EVT_MENU, self.showDoc, id=180)
        self.Bind(wx.EVT_MENU, self.openPrefs, prefItem)
        self.Bind(wx.EVT_MENU, self.onSwitchTabs, id=10001, id2=10010)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MENU, self.OnClose, quitItem)

        if subId2 > 2000:
            for i in range(2000,subId2):
                self.Bind(wx.EVT_MENU, self.openRecent, id=i)
        for i in range(500, stId):
            self.Bind(wx.EVT_MENU, self.changeStyle, id=i)

        if projectsToOpen:
            for p in projectsToOpen:
                self.panel.project.loadProject(p)
                sys.path.append(p)

        if filesToOpen:
            for f in filesToOpen:
                self.panel.addPage(f)

    ### Editor functions ###
    def cut(self, evt):
        self.panel.editor.Cut()

    def copy(self, evt):
        self.panel.editor.Copy()

    def paste(self, evt):
        self.panel.editor.Paste()

    def selectall(self, evt):
        self.panel.editor.SelectAll()

    def upperLower(self, evt):
        if evt.GetId() == 170:
            self.panel.editor.UpperCase()
        else:
            self.panel.editor.LowerCase()

    def tabsToSpaces(self, evt):
        self.panel.editor.tabsToSpaces()

    def undo(self, evt):
        if evt.GetId() == 150:
            self.panel.editor.Undo()
        else:
            self.panel.editor.Redo()

    def zoom(self, evt):
        if evt.GetId() == 132:
            self.panel.editor.SetZoom(self.panel.editor.GetZoom() + 1)
        else:
            self.panel.editor.SetZoom(self.panel.editor.GetZoom() - 1)

    def gotoLine(self, evt):
        dlg = wx.TextEntryDialog(self, "Enter a line number:", "Go to Line")
        val = -1
        if dlg.ShowModal() == wx.ID_OK:
            try:
                val = int(dlg.GetValue())
            except:
                val = -1
            dlg.Destroy()
        if val != -1:
            pos = self.panel.editor.FindColumn(val-1, 0)
            self.panel.editor.SetCurrentPos(pos)
            self.panel.editor.EnsureVisible(val)
            self.panel.editor.EnsureCaretVisible()
            wx.CallAfter(self.panel.editor.SetAnchor, pos)

    def OnComment(self, evt):
        self.panel.editor.OnComment()

    def fold(self, event):
        self.panel.editor.FoldAll()

    def autoComp(self, evt):
        try:
            self.panel.editor.showAutoComp()
        except AttributeError:
            pass

    def showFind(self, evt):
        self.panel.editor.OnShowFindReplace()

    def insertPath(self, evt):
        dlg = wx.FileDialog(self, message="Choose a file", defaultDir=os.getcwd(),
                            defaultFile="", style=wx.OPEN | wx.MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()
            text = str(path[0])
            self.panel.editor.ReplaceSelection("'" + text + "'")
        dlg.Destroy()

    def changeStyle(self, evt):
        menu = self.GetMenuBar()
        id = evt.GetId()
        st = menu.FindItemById(id).GetLabel()
        for key, value in STYLES[st].items():
            faces[key] = value
        for i in range(self.panel.notebook.GetPageCount()):
            ed = self.panel.notebook.GetPage(i)
            ed.setStyle()
        #self.panel.project.setStyle()

    def onSwitchTabs(self, evt):
        page = evt.GetId() - 10001
        self.panel.setPage(page)

    ### Open Prefs ang Logs ###
    def openPrefs(self, evt):
        pass

    ### New / Open / Save / Delete ###
    def new(self, event):
        self.panel.addNewPage()

    def newFromTemplate(self, event):
        self.panel.addNewPage()
        temp = {98: PYO_TEMPLATE, 97: CECILIA5_TEMPLATE, 96: ZYNE_TEMPLATE}[event.GetId()]
        self.panel.editor.SetText(temp)

    def newRecent(self, file):
        filename = os.path.join(TEMP_PATH,'.recent.txt')
        try:
            f = open(filename, "r")
            lines = [line[:-1] for line in f.readlines()]
            f.close()
        except:
            lines = []
        if not file in lines:
            f = open(filename, "w")
            lines.insert(0, file)
            if len(lines) > 10:
                lines = lines[0:10]
            for line in lines:
                f.write(line + '\n')
            f.close()

        subId2 = 2000
        recentFiles = []
        f = open(filename, "r")
        for line in f.readlines():
            recentFiles.append(line)
        f.close()
        if recentFiles:
            for item in self.submenu2.GetMenuItems():
                self.submenu2.DeleteItem(item)
            for file in recentFiles:
                self.submenu2.Append(subId2, file)
                subId2 += 1

    def open(self, event):
        dlg = wx.FileDialog(self, message="Choose a file", defaultDir=os.getcwd(),
            defaultFile="", style=wx.OPEN | wx.MULTIPLE)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()
            for file in path:
                self.panel.addPage(file)
                self.newRecent(file)
        dlg.Destroy()

    def openProject(self, event):
        dlg = wx.DirDialog(self, message="Choose a project folder", defaultPath=os.getcwd(),
                           style=wx.DD_DEFAULT_STYLE)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.folder = path
            self.panel.project.loadProject(self.folder)
            sys.path.append(path)
        dlg.Destroy()

    def openRecent(self, event):
        menu = self.GetMenuBar()
        id = event.GetId()
        file = menu.FindItemById(id).GetLabel()
        self.panel.addPage(file[:-1])

    def save(self, event):
        if not self.panel.editor.path or self.panel.editor.path == "Untitled.py":
            self.saveas(None)
        else:
            self.panel.editor.saveMyFile(self.panel.editor.path)
            self.SetTitle(self.panel.editor.path)

    def saveas(self, event):
        dlg = wx.FileDialog(self, message="Save file as ...", defaultDir=os.path.expanduser('~'),
            defaultFile="", style=wx.SAVE)
        dlg.SetFilterIndex(0)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.panel.editor.path = path
            self.panel.editor.setStyle()
            self.panel.editor.SetCurrentPos(0)
            self.panel.editor.AddText(" ")
            self.panel.editor.DeleteBackNotLine()
            self.panel.editor.saveMyFile(path)
            self.SetTitle(self.panel.editor.path)
            self.panel.notebook.SetPageText(self.panel.notebook.GetSelection(), os.path.split(path)[1])
            self.newRecent(path)
        dlg.Destroy()

    def delete(self, event):
        action = self.panel.editor.close()
        if action == 'delete':
            self.panel.deletePage()
        else:
            pass

    ### Run actions ###
    def runner(self, event):
        # Need to determine which python to use...
        path = self.panel.editor.path
        if os.path.isfile(path):
            cwd = os.path.split(path)[0]
            if sys.platform == "darwin":
                script = terminal_client_script % (cwd, path)
                script = convert_line_endings(script, 1)
                f = codecs.open(terminal_client_script_path, "w", encoding="utf-8")
                f.write(script)
                f.close()
                pid = subprocess.Popen(["osascript", terminal_client_script_path]).pid
            else:
                pid = subprocess.Popen(["python", path], cwd=cwd).pid

    def showDoc(self, evt):
        self.doc_frame = wx.Frame(None, -1, title='pyo documentation', size=(940, 700))
        self.doc_panel = HelpWin(self.doc_frame)
        self.doc_frame.Show()
        page = None
        if page:
            page_count = self.doc_panel.GetPageCount()
            for i in range(page_count):
                text = self.doc_panel.GetPageText(i)
                if text == page:
                    self.doc_panel.SetSelection(i)
                    return
        else:
            self.doc_panel.SetSelection(0)

    def onHelpAbout(self, evt):
        info = wx.AboutDialogInfo()
        info.Name = NAME
        info.Version = VERSION
        info.Copyright = u"(C) 2012 Olivier Bélanger"
        info.Description = "PyoEd is a simple text editor especially configured to edit pyo audio programs.\n\n"
        wx.AboutBox(info)

    def OnClose(self, event):
        try:
            self.doc_frame.Destroy()
        except:
            pass
        self.panel.OnQuit()
        if sys.platform == "darwin":
            f = open(terminal_close_server_script_path, "w")
            f.write(terminal_close_server_script)
            f.close()
            pid = subprocess.Popen(["osascript", terminal_close_server_script_path]).pid
        self.Destroy()

class MainPanel(wx.Panel):
    def __init__(self, parent, size=(1200,800), style=wx.SUNKEN_BORDER):
        wx.Panel.__init__(self, parent, size=(1200,800), style=wx.SUNKEN_BORDER)

        self.mainFrame = parent
        mainBox = wx.BoxSizer(wx.HORIZONTAL)

        self.notebook = MyNotebook(self)
        self.editor = Editor(self.notebook, -1, size=(0, -1), setTitle=self.SetTitle, getTitle=self.GetTitle)
        mainBox.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(mainBox)

        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.onPageChange)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.onClosePage)

    def addNewPage(self):
        editor = Editor(self.notebook, -1, size=(0, -1), setTitle=self.SetTitle, getTitle=self.GetTitle)
        editor.path = "Untitled.py"
        editor.setStyle()
        self.notebook.AddPage(editor, "Untitled.py", True)
        self.editor = editor

    def addPage(self, file):
        editor = Editor(self.notebook, -1, size=(0, -1), setTitle=self.SetTitle, getTitle=self.GetTitle)
        label = os.path.split(file)[1].split('.')[0]
        self.notebook.AddPage(editor, label, True)
        editor.LoadFile(file)
        editor.path = file
        editor.setStyle()
        self.editor = editor
        self.SetTitle(file)

    def onClosePage(self, evt):
        ed = self.notebook.GetPage(self.notebook.GetSelection())
        ed.Close()

    def deletePage(self):
        ed = self.notebook.GetPage(self.notebook.GetSelection())
        self.notebook.DeletePage(self.notebook.GetSelection())

    def setPage(self, pageNum):
        totalNum = self.notebook.GetPageCount()
        if pageNum < totalNum:
            self.notebook.SetSelection(pageNum)

    def onPageChange(self, event):
        self.editor = self.notebook.GetPage(self.notebook.GetSelection())
        if not self.editor.path:
            if self.editor.GetModify():
                self.SetTitle("*** PyoEd Editor ***")
            else:
                self.SetTitle("PyoEd Editor")
        else:
            if self.editor.GetModify():
                self.SetTitle('*** ' + self.editor.path + ' ***')
            else:
                self.SetTitle(self.editor.path)

    def SetTitle(self, title):
        self.mainFrame.SetTitle(title)

    def GetTitle(self):
        return self.mainFrame.GetTitle()

    def OnQuit(self):
        for i in range(self.notebook.GetPageCount()):
            ed = self.notebook.GetPage(i)
            ed.Close()

class Editor(stc.StyledTextCtrl):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style= wx.NO_BORDER,
                 setTitle=None, getTitle=None):
        stc.StyledTextCtrl.__init__(self, parent, ID, pos, size, style)

        dt = MyFileDropTarget(self)
        self.SetDropTarget(dt)

        self.SetSTCCursor(2)
        self.panel = parent

        self.path = ''
        self.setTitle = setTitle
        self.getTitle = getTitle
        self.saveMark = False
        self.inside = False
        self.anchor1 = self.anchor2 = 0

        self.alphaStr = string.lowercase + string.uppercase + '0123456789'

        self.Colourise(0, -1)
        self.SetCurrentPos(0)

        self.SetIndent(4)
        self.SetBackSpaceUnIndents(True)
        self.SetTabIndents(True)
        self.SetTabWidth(4)
        self.SetUseTabs(False)
        self.SetViewWhiteSpace(False)

        self.SetEOLMode(wx.stc.STC_EOL_LF)
        self.SetViewEOL(False)

        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        self.SetMargins(5,5)
        self.SetUseAntiAliasing(True)
        self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.SetEdgeColumn(1000)

        self.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(1, 28)
        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)
        self.SetMarginWidth(2, 12)

        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_FIND, self.OnFind)
        self.Bind(wx.EVT_FIND_NEXT, self.OnFind)
        self.Bind(wx.EVT_FIND_REPLACE, self.OnFind)
        self.Bind(wx.EVT_FIND_REPLACE_ALL, self.OnFind)
        self.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)

        tree = OBJECTS_TREE
        self.wordlist = []
        for k1 in tree.keys():
            if type(tree[k1]) == type({}):
                for k2 in tree[k1].keys():
                    for val in tree[k1][k2]:
                        self.wordlist.append(val)
            else:
                for val in tree[k1]:
                    self.wordlist.append(val)
        self.wordlist.append("PyoObject")
        self.wordlist.append("PyoTableObject")
        self.wordlist.append("PyoMatrixObject")
        self.wordlist.append("Server")

        self.EmptyUndoBuffer()
        self.SetFocus()
        self.setStyle()

        wx.CallAfter(self.SetAnchor, 0)
        self.Refresh()

    def setStyle(self):
        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "fore:%(default)s,face:%(face)s,size:%(size)d,back:%(background)s" % faces)
        self.StyleClearAll()  # Reset all to be like the default

        ext = os.path.splitext(self.path)[1].strip(".")
        if ext in ["py", "c5"]:
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS, faces['markerfg'], faces['markerbg'])
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS, faces['markerfg'], faces['markerbg'])
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE, faces['markerfg'], faces['markerbg'])
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNERCURVE, faces['markerfg'], faces['markerbg'])
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_ARROW, faces['markerfg'], faces['markerbg'])
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_ARROWDOWN, faces['markerfg'], faces['markerbg'])
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_LCORNERCURVE, faces['markerfg'], faces['markerbg'])

            self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "fore:%(default)s,face:%(face)s,size:%(size)d" % faces)
            self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  "fore:%(linenumber)s,back:%(marginback)s,face:%(face)s,size:%(size2)d" % faces)
            self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "fore:%(default)s,face:%(face)s" % faces)
            self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  "fore:#000000,back:%(bracelight)s,bold" % faces)
            self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    "fore:#000000,back:%(bracebad)s,bold" % faces)

            self.SetLexer(stc.STC_LEX_PYTHON)
            self.SetKeyWords(0, " ".join(keyword.kwlist) + " None True False " + " ".join(self.wordlist))

            # Default
            self.StyleSetSpec(stc.STC_P_DEFAULT, "fore:%(default)s,face:%(face)s,size:%(size)d" % faces)
            # Comments
            self.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:%(comment)s,face:%(face)s,size:%(size)d" % faces)
            # Number
            self.StyleSetSpec(stc.STC_P_NUMBER, "fore:%(number)s,face:%(face)s,bold,size:%(size)d" % faces)
            # String
            self.StyleSetSpec(stc.STC_P_STRING, "fore:%(string)s,face:%(face)s,size:%(size)d" % faces)
            # Single quoted string
            self.StyleSetSpec(stc.STC_P_CHARACTER, "fore:%(string)s,face:%(face)s,size:%(size)d" % faces)
            # Keyword
            self.StyleSetSpec(stc.STC_P_WORD, "fore:%(keyword)s,face:%(face)s,bold,size:%(size)d" % faces)
            # Triple quotes
            self.StyleSetSpec(stc.STC_P_TRIPLE, "fore:%(triple)s,face:%(face)s,size:%(size)d" % faces)
            # Triple double quotes
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:%(triple)s,face:%(face)s,size:%(size)d" % faces)
            # Class name definition
            self.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:%(class)s,face:%(face)s,bold,size:%(size)d" % faces)
            # Function or method name definition
            self.StyleSetSpec(stc.STC_P_DEFNAME, "fore:%(function)s,face:%(face)s,bold,size:%(size)d" % faces)
            # Operators
            self.StyleSetSpec(stc.STC_P_OPERATOR, "bold,size:%(size)d,face:%(face)s" % faces)
            # Identifiers
            self.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:%(identifier)s,face:%(face)s,size:%(size)d" % faces)
            # Comment-blocks
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, "fore:%(commentblock)s,face:%(face)s,size:%(size)d" % faces)

        self.SetCaretForeground(faces['caret'])
        self.SetSelBackground(1, faces['selback'])

    def OnShowFindReplace(self):
        data = wx.FindReplaceData()
        self.findReplace = wx.FindReplaceDialog(self, data, "Find & Replace", wx.FR_REPLACEDIALOG | wx.FR_NOUPDOWN)
        self.findReplace.data = data  # save a reference to it...
        self.findReplace.Show(True)

    def OnFind(self, evt):
        map = { wx.wxEVT_COMMAND_FIND : "FIND",
                wx.wxEVT_COMMAND_FIND_NEXT : "FIND_NEXT",
                wx.wxEVT_COMMAND_FIND_REPLACE : "REPLACE",
                wx.wxEVT_COMMAND_FIND_REPLACE_ALL : "REPLACE_ALL" }

        et = evt.GetEventType()
        findTxt = evt.GetFindString()

        selection = self.GetSelection()
        if selection[0] == selection[1]:
            selection = (0, self.GetLength())

        if map[et] == 'FIND':
            startpos = self.FindText(selection[0], selection[1], findTxt, evt.GetFlags())
            endpos = startpos+len(findTxt)
            self.anchor1 = endpos
            self.anchor2 = selection[1]
            self.SetSelection(startpos, endpos)
        elif map[et] == 'FIND_NEXT':
            startpos = self.FindText(self.anchor1, self.anchor2, findTxt, evt.GetFlags())
            endpos = startpos+len(findTxt)
            self.anchor1 = endpos
            self.SetSelection(startpos, endpos)
        elif map[et] == 'REPLACE':
            startpos = self.FindText(selection[0], selection[1], findTxt)
            endpos = startpos+len(findTxt)
            if startpos != -1:
                self.SetSelection(startpos, endpos)
                self.ReplaceSelection(evt.GetReplaceString())
        elif map[et] == 'REPLACE_ALL':
            self.anchor1 = selection[0]
            self.anchor2 = selection[1]
            startpos = selection[0]
            while startpos != -1:
                startpos = self.FindText(self.anchor1, self.anchor2, findTxt)
                endpos = startpos+len(findTxt)
                self.anchor1 = endpos
                if startpos != -1:
                    self.SetSelection(startpos, endpos)
                    self.ReplaceSelection(evt.GetReplaceString())

    def OnFindClose(self, evt):
        evt.GetDialog().Destroy()

    def tabsToSpaces(self):
        text = self.GetText()
        text = text.replace("\t", "    ")
        self.SetText(text)

    ### Save and Close file ###
    def saveMyFile(self, file):
        self.SaveFile(file)
        self.path = file
        self.saveMark = False

    def close(self):
        if self.GetModify():
            if not self.path: f = "Untitled"
            else: f = self.path
            dlg = wx.MessageDialog(None, 'file ' + f + ' has been modified. Do you want to save?', 'Warning!', wx.YES | wx.NO | wx.CANCEL)
            but = dlg.ShowModal()
            if but == wx.ID_YES:
                dlg.Destroy()
                if not self.path:
                    dlg2 = wx.FileDialog(None, message="Save file as ...", defaultDir=os.getcwd(), defaultFile="", style=wx.SAVE)
                    dlg2.SetFilterIndex(0)
                    if dlg2.ShowModal() == wx.ID_OK:
                        path = dlg2.GetPath()
                        self.SaveFile(path)
                        dlg2.Destroy()
                    else:
                        dlg2.Destroy()
                        return 'keep'
                else:
                    self.SaveFile(self.path)
                return 'delete'
            elif but == wx.ID_NO:
                dlg.Destroy()
                return 'delete'
            elif but == wx.ID_CANCEL:
                dlg.Destroy()
                return 'keep'
        else:
            return 'delete'

    def OnClose(self, event):
        if self.GetModify():
            if not self.path: f = "Untitled"
            else: f = self.path
            dlg = wx.MessageDialog(None, 'file ' + f + ' has been modified. Do you want to save?', 'Warning!', wx.YES | wx.NO)
            if dlg.ShowModal() == wx.ID_YES:
                dlg.Destroy()
                if not self.path:
                    dlg2 = wx.FileDialog(None, message="Save file as ...", defaultDir=os.getcwd(),
                        defaultFile="", style=wx.SAVE)
                    dlg2.SetFilterIndex(0)

                    if dlg2.ShowModal() == wx.ID_OK:
                        path = dlg2.GetPath()
                        self.SaveFile(path)
                        dlg2.Destroy()
                else:
                    self.SaveFile(self.path)
            else:
                dlg.Destroy()

    def OnModified(self):
        if self.GetModify() and not self.saveMark:
            title = self.getTitle()
            str = '*** ' + title + ' ***'
            self.setTitle(str)
            self.saveMark = True

    ### Editor functions ###
    def showAutoComp(self):
        charBefore = None
        caretPos = self.GetCurrentPos()
        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
        startpos = self.WordStartPosition(caretPos, True)
        endpos = self.WordEndPosition(caretPos, True)
        currentword = self.GetTextRange(startpos, endpos)
        if chr(charBefore) in self.alphaStr:
            list = ''
            for word in self.wordlist:
                if word.startswith(currentword) and word != currentword:
                    list = list + word + ' '
            if list:
                self.AutoCompShow(len(currentword), list)

    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos
        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)

        self.checkScrollbar()
        self.OnModified()
        evt.Skip()

    def checkScrollbar(self):
        lineslength = [self.LineLength(i)+1 for i in range(self.GetLineCount())]
        maxlength = max(lineslength)
        width = self.GetCharWidth() + (self.GetZoom() * 0.5)
        if (self.GetSize()[0]) < (maxlength * width):
            self.SetUseHorizontalScrollBar(True)
        else:
            self.SetUseHorizontalScrollBar(False)
            self.SetXOffset(0)

    def OnComment(self):
        selStartPos, selEndPos = self.GetSelection()
        self.firstLine = self.LineFromPosition(selStartPos)
        self.endLine = self.LineFromPosition(selEndPos)
        commentStr = '#'

        for i in range(self.firstLine, self.endLine+1):
            lineLen = len(self.GetLine(i))
            pos = self.PositionFromLine(i)
            if self.GetTextRange(pos,pos+1) != commentStr and lineLen > 2:
                self.InsertText(pos, commentStr)
            elif self.GetTextRange(pos,pos+1) == commentStr:
                self.GotoPos(pos+1)
                self.DelWordLeft()

    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())

                if self.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)

    def FoldAll(self):
        lineCount = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break

        lineNum = 0
        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)
                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)
            lineNum = lineNum + 1

    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldExpanded(line, True)
                    else:
                        self.SetFoldExpanded(line, False)
                    line = self.Expand(line, doExpand, force, visLevels-1)
                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1
        return line

class ProjectTree(wx.Panel):
    """Projects panel"""
    def __init__(self, parent, mainPanel, size):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS | wx.SUNKEN_BORDER | wx.EXPAND)

        self.mainPanel = mainPanel

        self.projectDict = {}

        size = size[0], size[1]
        self.tree = wx.TreeCtrl(self, -1, (0, 0), size,
                               wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.SUNKEN_BORDER | wx.EXPAND)

        if wx.Platform == '__WXMAC__':
            self.tree.SetFont(wx.Font(11, wx.ROMAN, wx.NORMAL, wx.NORMAL, face=faces['face']))
        else:
            self.tree.SetFont(wx.Font(8, wx.ROMAN, wx.NORMAL, wx.NORMAL, face=faces['face']))
        self.tree.SetBackgroundColour(faces['background'])

        isz = (12,12)
        self.il = wx.ImageList(isz[0], isz[1])
        self.fldridx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self.fldropenidx = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self.fileidx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))

        self.tree.SetImageList(self.il)
        self.tree.SetSpacing(12)
        self.tree.SetIndent(6)

        self.root = self.tree.AddRoot("Projects")
        self.tree.SetPyData(self.root, None)
        self.tree.SetItemImage(self.root, self.fldridx, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.root, self.fldropenidx, wx.TreeItemIcon_Expanded)
        self.tree.SetItemTextColour(self.root, faces['identifier'])

        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEdit, self.tree)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEndEdit, self.tree)

    def setStyle(self):
        if not self.tree.IsEmpty():
            self.tree.SetBackgroundColour(faces['background'])
            self.tree.SetItemTextColour(self.root, faces['identifier'])
            (child, cookie) = self.tree.GetFirstChild(self.root)

            while child.IsOk():
                self.tree.SetItemTextColour(child, faces['identifier'])
                if self.tree.ItemHasChildren(child):
                    (subchild, subcookie) = self.tree.GetFirstChild(child)
                    while subchild.IsOk():
                        self.tree.SetItemTextColour(subchild, faces['identifier'])
                        if self.tree.ItemHasChildren(subchild):
                            (ssubchild, ssubcookie) = self.tree.GetFirstChild(subchild)
                            while ssubchild.IsOk():
                                self.tree.SetItemTextColour(ssubchild, faces['identifier'])
                                (ssubchild, ssubcookie) = self.tree.GetNextChild(subchild, ssubcookie)
                                if self.tree.ItemHasChildren(ssubchild):
                                    while sssubchild.IsOk():
                                        self.tree.SetItemTextColour(sssubchild, faces['identifier'])
                                        (sssubchild, sssubcookie) = self.tree.GetNextChild(ssubchild, sssubcookie)
                            (sssubchild, sssubcookie) = self.tree.GetFirstChild(ssubchild)
                        (subchild, subcookie) = self.tree.GetNextChild(child, subcookie)
                (child, cookie) = self.tree.GetNextChild(self.root, cookie)

    def loadProject(self, dirPath):
        projectName = os.path.split(dirPath)[1]

        self.projectDict[projectName] = dirPath

        projectDir = {}

        for root, dirs, files in os.walk(dirPath):
            if os.path.split(root)[1][0] != '.':
                if root == dirPath:
                    child = self.tree.AppendItem(self.root, projectName)
                    self.tree.SetPyData(child, None)
                    self.tree.SetItemImage(child, self.fldridx, wx.TreeItemIcon_Normal)
                    self.tree.SetItemImage(child, self.fldropenidx, wx.TreeItemIcon_Expanded)
                    self.tree.SetItemTextColour(child, faces['identifier'])
                    if dirs:
                        ddirs = [dir for dir in dirs if dir[0] != '.']
                        for dir in ddirs:
                            subfol = self.tree.AppendItem(child, "%s" % dir)
                            projectDir[dir] = subfol
                            self.tree.SetPyData(subfol, None)
                            self.tree.SetItemImage(subfol, self.fldridx, wx.TreeItemIcon_Normal)
                            self.tree.SetItemImage(subfol, self.fldropenidx, wx.TreeItemIcon_Expanded)
                            self.tree.SetItemTextColour(subfol, faces['identifier'])
                    if files:
                        ffiles = [file for file in files if file[0] != '.' and file[-3:] != 'pyc']
                        for file in ffiles:
                            item = self.tree.AppendItem(child, "%s" % file)
                            self.tree.SetPyData(item, None)
                            self.tree.SetItemImage(item, self.fileidx, wx.TreeItemIcon_Normal)
                            self.tree.SetItemImage(item, self.fileidx, wx.TreeItemIcon_Selected)
                            self.tree.SetItemTextColour(item, faces['identifier'])
                else:
                    if os.path.split(root)[1] in projectDir.keys():
                        parent = projectDir[os.path.split(root)[1]]
                        if dirs:
                            ddirs = [dir for dir in dirs if dir[0] != '.']
                            for dir in ddirs:
                                subfol = self.tree.AppendItem(parent, "%s" % dir)
                                projectDir[dir] = subfol
                                self.tree.SetPyData(subfol, None)
                                self.tree.SetItemImage(subfol, self.fldridx, wx.TreeItemIcon_Normal)
                                self.tree.SetItemImage(subfol, self.fldropenidx, wx.TreeItemIcon_Expanded)  
                                self.tree.SetItemTextColour(subfol, faces['identifier'])
                        if files:
                            ffiles = [file for file in files if file[0] != '.' and file[-3:] != 'pyc']
                            for file in ffiles:
                                item = self.tree.AppendItem(parent, "%s" % file)
                                self.tree.SetPyData(item, None)
                                self.tree.SetItemImage(item, self.fileidx, wx.TreeItemIcon_Normal)
                                self.tree.SetItemImage(item, self.fileidx, wx.TreeItemIcon_Selected)
                                self.tree.SetItemTextColour(item, faces['identifier'])

        self.tree.SortChildren(self.root)
        self.tree.SortChildren(child)

    def OnBeginEdit(self, event):
        # show how to prevent edit...
        item = event.GetItem()
        if item:
            wx.Bell()
            # Lets just see what's visible of its children
            cookie = 0
            root = event.GetItem()
            (child, cookie) = self.tree.GetFirstChild(root)
            while child.IsOk():
                (child, cookie) = self.tree.GetNextChild(root, cookie)
            event.Veto()

    def OnEndEdit(self, event):
        # show how to reject edit, we'll not allow any digits
        for x in event.GetLabel():
            if x in string.digits:
                event.Veto()
                return

_DOC_KEYWORDS = ['Attributes', 'Examples', 'Parameters', 'Methods', 'Notes', 'Methods details', 'Overview']
_KEYWORDS_LIST = []
def _ed_set_style(editor):
    editor.SetLexer(stc.STC_LEX_PYTHON)
    editor.SetKeyWords(0, " None True False " + " ".join(_KEYWORDS_LIST))
    editor.SetKeyWords(1, " ".join(_DOC_KEYWORDS))

    editor.SetMargins(5,5)
    editor.SetSTCCursor(2)
    editor.SetIndent(4)
    editor.SetTabIndents(True)
    editor.SetTabWidth(4)
    editor.SetUseTabs(False)

    # Global default styles for all languages
    editor.StyleSetSpec(stc.STC_STYLE_DEFAULT,  "fore:%(default)s,face:%(face)s,size:%(size)d,back:%(background)s" % faces2)
    editor.StyleClearAll()  # Reset all to be like the default

    editor.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "fore:%(default)s,face:%(face)s,size:%(size)d" % faces2)
    editor.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  "fore:%(linenumber)s,back:%(marginback)s,face:%(face)s,size:%(size2)d" % faces2)
    editor.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "fore:%(default)s,face:%(face)s" % faces2)

    # Default
    editor.StyleSetSpec(stc.STC_P_DEFAULT, "fore:%(default)s,face:%(face)s,size:%(size)d" % faces2)
    # Comments
    editor.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:%(comment)s,face:%(face)s,size:%(size)d" % faces2)
    # Number
    editor.StyleSetSpec(stc.STC_P_NUMBER, "fore:%(number)s,face:%(face)s,bold,size:%(size)d" % faces2)
    # String
    editor.StyleSetSpec(stc.STC_P_STRING, "fore:%(string)s,face:%(face)s,size:%(size)d" % faces2)
    # Single quoted string
    editor.StyleSetSpec(stc.STC_P_CHARACTER, "fore:%(string)s,face:%(face)s,size:%(size)d" % faces2)
    # Keyword
    editor.StyleSetSpec(stc.STC_P_WORD, "fore:%(keyword)s,face:%(face)s,bold,size:%(size)d" % faces2)
    editor.StyleSetSpec(stc.STC_P_WORD2, "fore:%(comment)s,face:%(face)s,bold,size:%(size3)d" % faces2)
    # Triple quotes
    editor.StyleSetSpec(stc.STC_P_TRIPLE, "fore:%(triple)s,face:%(face)s,size:%(size)d" % faces2)
    # Triple double quotes
    editor.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:%(triple)s,face:%(face)s,size:%(size)d" % faces2)
    # Class name definition
    editor.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:%(class)s,face:%(face)s,bold,size:%(size)d" % faces2)
    # Function or method name definition
    editor.StyleSetSpec(stc.STC_P_DEFNAME, "fore:%(function)s,face:%(face)s,bold,size:%(size)d" % faces2)
    # Operators
    editor.StyleSetSpec(stc.STC_P_OPERATOR, "bold,size:%(size)d,face:%(face)s" % faces2)
    # Identifiers
    editor.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:%(identifier)s,face:%(face)s,size:%(size)d" % faces2)
    # Comment-blocks
    editor.StyleSetSpec(stc.STC_P_COMMENTBLOCK, "fore:%(commentblock)s,face:%(face)s,size:%(size)d" % faces2)

class HelpWin(wx.Treebook):
    def __init__(self, parent):
        wx.Treebook.__init__(self, parent, -1, style=wx.BK_DEFAULT)
        self.parent = parent

        self.menuBar = wx.MenuBar()
        menu1 = wx.Menu()
        menu1.Append(5003, "Close\tCtrl+W", "Closes front window")
        self.menuBar.Append(menu1, 'File')

        menu2 = wx.Menu()
        menu2.Append(5010, "Copy\tCtrl+C")
        self.menuBar.Append(menu2, 'Edit')

        self.parent.SetMenuBar(self.menuBar)

        self.parent.Bind(wx.EVT_MENU, self.copy, id=5010)
        self.parent.Bind(wx.EVT_MENU, self.close, id=5003)
        self.parent.Bind(wx.EVT_CLOSE, self.close)

        headers = ["Server", "PyoObject", "PyoTableObject", "PyoMatrixObject", "Map", "Stream", "TableStream", "functions"]
        _KEYWORDS_LIST.extend(headers)
        tree = OBJECTS_TREE
        max = 1
        max += len(headers)
        for k1 in headers:
            if type(tree[k1]) == type({}):
                max += len(tree[k1].keys())
                for k2 in tree[k1].keys():
                    _KEYWORDS_LIST.extend(tree[k1][k2])
                    max += len(tree[k1][k2])
            else:
                _KEYWORDS_LIST.extend(tree[k1])
                max += len(tree[k1])

        dlg = wx.ProgressDialog("Pyo Documentation", "    Building manual...    ",
                               maximum = max, parent=self, style = wx.PD_APP_MODAL)
        keepGoing = True
        count = 0
        win = self.makePanel()
        self.AddPage(win, "--- pyo documentation ---")
        for key in headers:
            if type(OBJECTS_TREE[key]) == type([]):
                count += 1
                win = self.makePanel(key)
                self.AddPage(win, key)
                for obj in OBJECTS_TREE[key]:
                    count += 1
                    win = self.makePanel(obj)
                    self.AddSubPage(win, obj)
                    if count <= max:
                        (keepGoing, skip) = dlg.Update(count)
            else:
                if key == "PyoObject":
                    count += 1
                    win = self.makePanel("PyoObject")
                    self.AddPage(win, "PyoObject")
                for key2 in sorted(OBJECTS_TREE[key]):
                    count += 1
                    win = self.makePanel("%s" % key2)
                    self.AddPage(win, "PyoObj - %s" % key2)
                    for obj in OBJECTS_TREE[key][key2]:
                        count += 1
                        win = self.makePanel(obj)
                        self.AddSubPage(win, obj)
                        if count <= max:
                            (keepGoing, skip) = dlg.Update(count)
        dlg.Destroy()
        self.setStyle()

        # This is a workaround for a sizing bug on Mac...
        wx.FutureCall(100, self.AdjustSize)

    def copy(self, evt):
        self.GetPage(self.GetSelection()).win.Copy()

    def close(self, evt):
        self.parent.Hide()

    def AdjustSize(self):
        self.GetTreeCtrl().InvalidateBestSize()
        self.SendSizeEvent()

    def makePanel(self, obj=None):
        panel = wx.Panel(self, -1)
        if obj != None:
            try:
                args = '\n' + class_args(eval(obj)) + '\n'
                isAnObject = True
            except:
                args = '\n' + obj + ':\n'
                if obj in OBJECTS_TREE["functions"]:
                    isAnObject = True
                else:
                    isAnObject = False
            if isAnObject:
                try:
                    text = eval(obj).__doc__
                    text_form = last_line = ""
                    inside_examples = False
                    for line in text.splitlines():
                        if inside_examples and line.strip() == "":
                            if obj not in OBJECTS_TREE["functions"]:
                                text_form += "s.gui(locals())"
                            inside_examples = False
                        if '>>>' in line or '...' in line:
                            l = line[8:]
                            if l.strip() != "":
                                text_form += l + '\n'
                        else:
                            if line.startswith("    "):
                                text_form += line[4:].rstrip() + '\n'
                            else:
                                text_form += line.rstrip() + '\n'
                        if 'Examples' in last_line:
                            text_form += "from pyo import *\n"
                            inside_examples = True
                        last_line = line
                    methods = self.getMethodsDoc(text, obj)
                    panel.win = stc.StyledTextCtrl(panel, -1, size=(600, 600))
                    panel.win.SetMarginWidth(1, 0)
                    panel.win.SetText(args + text_form + methods)
                except:
                    panel.win = stc.StyledTextCtrl(panel, -1, size=(600, 600))
                    panel.win.SetText(args + "\nnot documented yet...\n\n")
            else:
                try:
                    text = eval(obj).__doc__
                except:
                    text = "\nnot documented yet...\n\n"
                if obj in OBJECTS_TREE["PyoObject"].keys():
                    text += "\nOverview:\n"
                    for o in OBJECTS_TREE["PyoObject"][obj]:
                        text += o + ": " + self.getDocFirstLine(o)
                panel.win = stc.StyledTextCtrl(panel, -1, size=(600, 600))
                panel.win.SetMarginWidth(1, 0)
                panel.win.SetText(text)
        else:
            panel.win = stc.StyledTextCtrl(panel, -1, size=(600, 600))
            panel.win.SetText("""
pyo is a Python module written in C to help digital signal processing script creation.

pyo is a Python module containing classes for a wide variety of audio signal processing types. 
With pyo, user will be able to include signal processing chains directly in Python scripts or 
projects, and to manipulate them in real time through the interpreter. Tools in pyo module 
offer primitives, like mathematical operations on audio signal, basic signal processing 
(filters, delays, synthesis generators, etc.), but also complex algorithms to create sound 
granulation and others creative sound manipulations. pyo supports OSC protocol (Open Sound 
Control), to ease communications between softwares, and MIDI protocol, for generating sound 
events and controlling process parameters. pyo allows creation of sophisticated signal 
processing chains with all the benefits of a mature, and wild used, general programming 
language.
""")
        panel.win.SetReadOnly(True)
        panel.win.Bind(wx.EVT_LEFT_DOWN, self.MouseDown)
        _ed_set_style(panel.win)

        def OnPanelSize(evt, win=panel.win):
            win.SetPosition((0,0))
            win.SetSize(evt.GetSize())

        panel.Bind(wx.EVT_SIZE, OnPanelSize)
        return panel

    def MouseDown(self, evt):
        stc = self.GetPage(self.GetSelection()).win
        pos = stc.PositionFromPoint(evt.GetPosition())
        start = stc.WordStartPosition(pos, False)
        end = stc.WordEndPosition(pos, False)
        word = stc.GetTextRange(start, end)

        page_count = self.GetPageCount()
        for i in range(page_count):
            text = self.GetPageText(i)
            if text == word:
                self.SetSelection(i)
                stc.SetCurrentPos(0)
                break
        evt.Skip()

    def getDocFirstLine(self, obj):
        try:
            text = eval(obj).__doc__
            if text == None:
                text = ''
        except:
            text = ''

        if text != '':
            spl = text.split('\n')
            if len(spl) == 1:
                f = spl[0]
            else:
                f = spl[1]
        else:
            f = text
        return f.strip() + "\n"

    def getMethodsDoc(self, text, obj):
        lines = text.splitlines(True)
        flag = False
        methods = ''
        for line in lines:
            if flag:
                if line.strip() == '': continue
                else:
                    l = line.lstrip()
                    ppos = l.find('(')
                    if ppos != -1:
                        meth = l[0:ppos]
                        args = inspect.getargspec(getattr(eval(obj), meth))
                        args = inspect.formatargspec(*args)
                        args = args.replace('self, ', '')
                        methods += obj + '.' + meth + args + ':\n'
                        docstr = getattr(eval(obj), meth).__doc__.rstrip()
                        methods += docstr + '\n\n    '

            if 'Methods:' in line: 
                flag = True
                methods += '    Methods details:\n\n    '

            for key in _DOC_KEYWORDS:
                if key != 'Methods':
                    if key in line: 
                        flag = False

        methods_form = ''
        if methods != '':
            for line in methods.splitlines():
                methods_form += line[4:] + '\n'
        return methods_form

    def setStyle(self):
        tree = self.GetTreeCtrl()
        tree.SetBackgroundColour(STYLES['Default']['background'])
        root = tree.GetRootItem()
        tree.SetItemTextColour(root, STYLES['Default']['identifier'])
        (child, cookie) = tree.GetFirstChild(root)
        while child.IsOk():
            tree.SetItemTextColour(child, STYLES['Default']['identifier'])
            if tree.ItemHasChildren(child):
                (child2, cookie2) = tree.GetFirstChild(child)
                while child2.IsOk():
                    tree.SetItemTextColour(child2, STYLES['Default']['identifier'])
                    (child2, cookie2) = tree.GetNextChild(child, cookie2)
            (child, cookie) = tree.GetNextChild(root, cookie)

class MyNotebook(wx.aui.AuiNotebook):
    def __init__(self, parent, size=(0,-1), style=wx.aui.AUI_NB_TAB_FIXED_WIDTH | 
                                            wx.aui.AUI_NB_CLOSE_ON_ALL_TABS | 
                                            wx.aui.AUI_NB_SCROLL_BUTTONS | wx.SUNKEN_BORDER):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=style)
        dt = MyFileDropTarget(self)
        self.SetDropTarget(dt)

class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, filenames):
        for file in filenames:
            if os.path.isdir(file):
                self.window.GetTopLevelParent().panel.project.loadProject(file)
                sys.path.append(file)
            elif os.path.isfile(file):
                self.window.GetTopLevelParent().panel.addPage(file)
            else:
                pass

if __name__ == '__main__':
    filesToOpen = []
    projectsToOpen = []
    if len(sys.argv) > 1:
        for f in sys.argv[1:]:
            if os.path.isdir(f):
                if f[-1] == '/': f = f[:-1]
                projectsToOpen.append(f)
            elif os.path.isfile(f):
                filesToOpen.append(f)
            else:
                pass

    app = wx.PySimpleApp()

    X,Y = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_X), wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y)
    if X < 800: X -= 50
    else: X = 800
    if Y < 700: Y -= 50
    else: Y = 700
    frame = MainFrame(None, -1, title='PyoEd Editor', pos=(10,25), size=(X, Y))
    frame.Show()

    app.MainLoop()