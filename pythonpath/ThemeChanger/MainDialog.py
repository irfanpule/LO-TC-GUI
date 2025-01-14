# -*- coding: utf-8 -*-
#!/usr/bin/env python

import uno
from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK, BUTTONS_OK_CANCEL, BUTTONS_YES_NO, BUTTONS_YES_NO_CANCEL, BUTTONS_RETRY_CANCEL, BUTTONS_ABORT_IGNORE_RETRY
from com.sun.star.awt.MessageBoxButtons import DEFAULT_BUTTON_OK, DEFAULT_BUTTON_CANCEL, DEFAULT_BUTTON_RETRY, DEFAULT_BUTTON_YES, DEFAULT_BUTTON_NO, DEFAULT_BUTTON_IGNORE
from com.sun.star.awt.MessageBoxType import MESSAGEBOX, INFOBOX, WARNINGBOX, ERRORBOX, QUERYBOX
from ThemeChanger.UI.MainDialog_UI import MainDialog_UI
from ThemeChanger.ImportDialog import ImportDialog
from ThemeChanger.CreateDialog import CreateDialog
from ThemeChanger.DetailsDialog import DetailsDialog
import ThemeChanger.Helper as Helper

from os import listdir, makedirs, readlink
from os.path import exists, isfile, abspath, dirname, relpath
from shutil import copytree as copy_to_userdir, rmtree
import tempfile
import traceback
import zipfile

def mri(ctx, target):
    mri = ctx.ServiceManager.createInstanceWithContext("mytools.Mri", ctx)
    mri.inspect(target)
class MainDialog(MainDialog_UI):
    '''
    Class documentation...
    '''
    def __init__(self, ctx=uno.getComponentContext(), **kwargs):

        self.ctx = ctx
        MainDialog_UI.__init__(self, self.ctx)

        # --------- my code ---------------------

        # self.DialogModel.Title = "MainDialog"
        # mri(self.ctx, self.DialogModel)

    # --------- helpers ---------------------

    def messageBox(self, MsgText, MsgTitle, MsgType=MESSAGEBOX, MsgButtons=BUTTONS_OK):
        sm = self.ctx.ServiceManager
        si = sm.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        mBox = si.createMessageBox(self.Toolkit, MsgType, MsgButtons, MsgTitle, MsgText)
        mBox.execute()

    def register_new_item(self, ctx, path_to_file=None):
        # path substitution instance
        ps = ctx.getServiceManager().createInstanceWithContext('com.sun.star.util.PathSubstitution', ctx)
        # get user profile dir ($HOME/.config/libreoffice/4/user/)
        userdir = uno.fileUrlToSystemPath(ps.getSubstituteVariableValue("$(user)"))

        # register new dir ($(userdir)/lotc-themes) if not exist
        if not exists(userdir + "/lotc-themes"):
            makedirs(userdir + "/lotc-themes")
            print("Created lotc-themes folder in userdir")

        # register new theme from path_to_file
        if not path_to_file == None:
            # check if path_to_file is exists and it is a file
            if not exists(path_to_file) or not isfile(path_to_file):
                self.messageBox("Oops, %s is missing, please check your lotc file path" % path_to_file, "Error opening file", MsgType=ERRORBOX)
                return
            # create tmp dir
            TMPDIR = tempfile.gettempdir() + "/lotc/"
            try:
                makedirs(TMPDIR)
            except OSError:
                print("TMPDIR already exist, continue process...")

            print("continue here ...")

            # unzip to tmp dir
            zip_ref = zipfile.ZipFile(path_to_file, 'r')
            zip_ref.extractall(TMPDIR)
            zip_ref.close()
            print("%s extracted to TMPDIR, now loading ..." % path_to_file)

            # check if path_to_file is not exists with imported theme
            tmp_theme = listdir(TMPDIR)[0]
            if exists("%s/lotc-themes/%s" % (userdir, tmp_theme)):
                print("Already exist, overwriting to existing dir")
                rmtree("%s/lotc-themes/%s" % (userdir, tmp_theme))

            source = TMPDIR + tmp_theme
            destination = "%s/lotc-themes/%s" % (userdir, tmp_theme)
            # copy tmptheme to userdir
            try:
                copy_to_userdir(source, destination)
            except Exception as e:
                print("exiting ... ", e)
            print("Theme installed successfully")
            # End - delete TMPDIR
            rmtree(TMPDIR)
            print("Deleted tmpdir")

        # create new component to dialog
        try:
            self.installed_themes = self.refresh_installed_themes(userdir)
            self.active_theme = None
            self.alter_installed_themes(userdir)

            # clear first
            self.clear_theme_list()
            # then generate
            for theme in self.installed_themes:
                self.create_new_component(theme, self.active_theme)
        except Exception as e:
            print(e)
            traceback.print_exc()

    def clear_theme_list(self):
        print("Clearing theme lists")
        if len(self.themeListBox.getAllItems()) > 0:
            self.themeListBox.removeAllItems()

    def create_new_component(self, theme, active_theme):
        thumbnail_active_full_path = dirname(abspath(__file__)) + "/UI/icons/active.svg"
        thumbnail_inactive_full_path = dirname(abspath(__file__)) + "/UI/icons/nonactive.png"
        is_active = False
        if theme["name"].lower() == active_theme.lower():
            is_active = True
        print("registering '%s' to dialog" % theme["name"])
        if is_active:
            self.themeListBox.insertItem(0, theme["name"], "file://"+thumbnail_active_full_path)
        else:
            self.themeListBox.insertItem(0, theme["name"], "file://"+thumbnail_inactive_full_path)

    def refresh_installed_themes(self, userdir):
        installed_path = listdir(userdir + "/lotc-themes")
        installed_themes = []
        for item in installed_path:
            if item == "active-theme":
                installed_themes.append({"name": "active-theme", "location": "active-theme"})
            else:
                if exists(userdir + "/lotc-themes/" + item + "/manifest.xml"):
                    theme_name = Helper.parse_manifest(userdir + "/lotc-themes/" + item)["name"]
                else:
                    theme_name = "Default LibreOffice"
                installed_themes.append({"name": theme_name, "location": item})
        # print(installed_themes)
        return installed_themes

    def alter_installed_themes(self, userdir):
        for theme in self.installed_themes:
            if theme["name"] == "active-theme":
                if exists(userdir + "/lotc-themes/active-theme/manifest.xml"):
                    self.active_theme = Helper.parse_manifest(userdir + "/lotc-themes/active-theme")["name"]
                else:
                    self.active_theme = "Default LibreOffice"
                print("remove active-theme from list")
                self.installed_themes.remove(theme)
                break


    # -----------------------------------------------------------
    #               Execute dialog
    # -----------------------------------------------------------

    def showDialog(self):
        self.DialogContainer.setVisible(True)
        self.DialogContainer.createPeer(self.Toolkit, None)
        Helper.prepare_new_install(self.ctx)
        # get os env
        self.register_new_item(self.ctx)
        self.DialogContainer.execute()

    # -----------------------------------------------------------
    #               Action events
    # -----------------------------------------------------------
    def createButton_OnClick(self):
        createDialog = CreateDialog(ctx=self.ctx)
        createDialog.showDialog()

    def importButton_OnClick(self):
        importDialog = ImportDialog(ctx=self.ctx)
        lotc_location = importDialog.showDialog()
        if not lotc_location == None:
            self.register_new_item(self.ctx,lotc_location)

    def closeButton_OnClick(self):
        self.DialogModel.Title = "It's Alive! - closeButton"
        self.messageBox("It's Alive! - closeButton", "Event: OnClick", INFOBOX)
        # TODO: not implemented

    def showDetailDialog(self, theme_name):
        try:
            # path substitution instance
            ps = self.ctx.getServiceManager().createInstanceWithContext('com.sun.star.util.PathSubstitution', self.ctx)
            # get user profile dir ($HOME/.config/libreoffice/4/user/)
            userdir = uno.fileUrlToSystemPath(ps.getSubstituteVariableValue("$(user)"))
            for theme in self.installed_themes:
                if theme["name"] == theme_name:
                    theme_dir = userdir + "/lotc-themes/" + theme["location"]
                    break
            theme_data = Helper.parse_manifest(theme_dir)
            if theme_data == None:
                theme_data = {
                    "author": "LibreOffice",
                    "description": "LibreOffice default theme",
                    "name": theme_name,
                    "screenshots": ["file://{}/program/intro.png".format(theme_dir)]
                }
            theme_data["theme_location"] = theme_dir
            theme_data["current_active"] = self.active_theme
            detailDialog = DetailsDialog(ctx=self.ctx, theme_data=theme_data)
        except Exception as e:
            print(e)
            traceback.print_exc()
            exit(255)
        new_active_theme = detailDialog.showDialog()
        if self.active_theme != new_active_theme:
            self.active_theme = new_active_theme
        self.installed_themes = self.refresh_installed_themes(userdir)
        self.alter_installed_themes(userdir)
        # clear first
        self.clear_theme_list()
        # then generate
        for theme in self.installed_themes:
            self.create_new_component(theme, self.active_theme)

    def themeListBox_OnClick(self):
        print("Theme selected: ", self.DialogContainer.getControl("themeListBox").getSelectedItem())
        self.showDetailDialog(self.DialogContainer.getControl("themeListBox").getSelectedItem())
