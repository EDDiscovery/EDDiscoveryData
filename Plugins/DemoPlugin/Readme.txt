Demonstration Python Plugin

Must have:

Config
------

config.json - contains configuration for how to launch the plugin. 
    The "Python" section is used to tell it that the panel is python and the launch parameters, and what modules should be installed if checkmodules.py fails
    
    
Graphics Files
--------------

Put as many graphics in as you want.  The Action dialog can pick them up for buttons etc.

snake.png - panel icon, referred to by the INSTALL PlugInPanel = option in the ACT file which describes the plugin
    Also refered by the UIInterface.act to generate a graphic button


Action Scripts
--------------

Plugins use Action scripts to set up the UI.  You can have as many .act files as you want.  One of them should have the EVENT onStartup, onStartup, "", Condition AlwaysTrue set up.

UIInterface.act 
    This has the OnStartup Action script which gets run as the panel is created, so you can create the UI using action. See the action doc.
    Also has helper programs for the python interface to produce various UI elements
    
UIDialogExample.act
    This is an example Action dialog which the demoplug.py demonstrates using
    
Python Scripts
--------------

DemoPython.py is the script, mentioned in config.json, which gets executed at start.
    This should hook up using ZMQ to EDD using the port given in argv[1] and then run
    
edd.py is the interface which connects python with EDD. It has many functions in it to get data and control the UI set up by UIInterface.act
    The API is described at the top of the file, followed by helper functions to perform the interface calls
    
checkmodules.py is mentioned by config.json as the python file to run before edd.py, and allows you to check modules present before running.  If it fails, you have the means
    to install modules using entries in config.json
    
gridfill.py is a helper to demopython.py


Visual Studio Debugging files
-----------------------------

*.sln and *.pyproj allow you to debug in VS the plugin
    In EDD, using -zmqport 5000 to force a debug port on the plugin and stop it autolaunching the plugin (ports <10000 do not autolaunch)
    Open the sln in visual studio 2022+.  
    Run EDD
        create the python panel, it will wait until the python program connects
    Run the python program in visual studio.  The program will connect to EDD and you can debug the plugin
    
    

    


    



        

For a pyth

