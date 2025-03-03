Demonstration Python Plugin

This Folder contains:

config.json
-----------

Contains configuration for how to launch the plugin.
    The "Python" section is used to tell it that the panel is python and the launch parameters, and what modules should be installed if checkmodules.py fails.
        Version: "3.13" : Force this version of python to be used. Optional
        ModulesCheck: "modulecheck.py" : Run this module check script before running the python main program.
        Modules: [ "module1", "module2"] : If modules check fail, install this list of modules
        Start: "DemoPlugin.py" : Start this script
        CreateNoWindow : true/false : If true, no python window is created.

    The "Panel" section is used to configure the EDD form.
        SupportTransparency : True/False (Default if not Present) : TBD
        DefaultTransparent : True/False (Default if not Present) : TBD
        Hidden : True/False (False if not Present):
            If set true, hide the EDD pop out window when python connects. You must have PopOutOnly True set below in PlugInPanel ACT file in the V1 folder (see below)
            This allows a headless EDD panel to run a python plugin in GUI/Text mode, instead of using the EDD panel as the UI.

Python Scripts
--------------

DemoPython.py is the script, mentioned in config.json, which gets executed at start.
    This should hook up using ZMQ to EDD using the port given in argv[1] then run.
    argv[2] gives a unique instance integer, which you could use if you want to save config for the panel instance outside of the EDDIF.Config system

edd.py is the interface which connects python with EDD. It has many functions in it to get data and control the UI set up by UIInterface.act
    The API is described at the top of the file, followed by helper functions to perform the interface calls

checkmodules.py is mentioned by config.json as the python file to run before edd.py, and allows you to check modules present before running.  If it fails, you have the means
    to install modules using entries in config.json. Import all the modules across the whole project to check

gridfill.py is a helper to demopython.py

Action Scripts
--------------

Plugins use Action scripts to set up the UI.  You can have as many .act files as you want.  One of them should have the EVENT onStartup, onStartup, "", Condition AlwaysTrue set up.

Action scripts for a plugin run in their own controller instance and do not interact with the standard action system or with each other.

UIInterface.act
    This has the OnStartup Action script which gets run as the panel is created, so you can create the UI using action. See the action doc.
    Also has helper programs for the python interface to produce various UI elements

UIDialogExample.act
    This is an example Action dialog which the demoplug.py demonstrates using


Graphics Files
--------------

Put as many graphics in as you want.  The Action dialog can pick them up for buttons etc.

snake.png - panel icon, referred to by the INSTALL PlugInPanel = option in the ACT file which describes the plugin
    Also refered by the UIInterface.act to generate a graphic button

Visual Studio Debugging files
-----------------------------

*.sln and *.pyproj allow you to debug in VS the plugin
    In EDD, using -zmqport 5000 to force a debug port on the plugin and stop it autolaunching the plugin (ports <10000 do not autolaunch)
    Open the sln in visual studio 2022+ (make sure its the latest).
    Run EDD
        create the python panel, it will wait until the python program connects
    Run the python program in visual studio.  The program will connect to EDD and you can debug the plugin

Additional Action File Required
--------------------------------

In ActionFiles\V1 you need a action file for this plugin.

This action file needs to have the following statements:

ACTIONFILE V4
ENABLED True
INSTALL LongDescription="Description.."
INSTALL ShortDescription="Short name"
INSTALL Version=0.1.0.0
INSTALL MinEDVersion=18.1.0.0
INSTALL Location=Actions

REM Here we declare the plugin panel to EDD.  First is a unique key used by EDD to recognise a panel type
REM then followed by the type which must be at present ZMQPanel
REM then wintitle, refname (for DB), Description, icon filename (relative to plugin folder), Plugin Folder in AppData structure where config.json is located, Pop Out Only (True/False)

INSTALL PlugInPanel=DemoPythonPanelUniqueNameKey,EDDiscovery.UserControls.UserControlZMQPanel,"Demo Python Addon Panel",DemoPythonv1,"Demonstration of a python script interacting with EDD","snake.png","Plugins\DemoPlugin",false

REM We need to download the plugin, so from this github folder, download all files found in it to Plugins/...
INSTALL DownloadFolder=Plugins/DemoPlugin;Plugins\DemoPlugin

Then optionally OnStartup/OnInstall statements to present info to the user.

The plugin cannot call programs in this action file, or any main action files, as noted above.

ZMQ Interface is documented in UserControlZMQPanel ZMQInterface.txt





