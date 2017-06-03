#TODO Export packed soundfile
#TODO Only show UI in Timeline/Both mode of VSE

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or modify it under the terms of the GNU General 
#  Public License as published by the Free Software Foundation; either version 2 of the License, or (at your 
#  option) any later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the 
#  implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License 
#  for more details.
#
#  You should have received a copy of the GNU General Public License along with this program; if not, write to 
#  the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
bl_info = {
    "name" : "AudacityLink",
    "author" : "qwertquadrat",
    "version" : (1,0),
    "blender" : (2, 78, 0),
    "location" : "Video Sequence Editor > Properties",
    "description" : "Easier sound editing with VSE using Audacity",
    "category" : "Import-Export"
}

#Imports                   Used to...
import tempfile          # Find TEMP directory
import bpy               # Blender integration
import random            # Generate random numbers
import os                # IO operations
import subprocess        # Launch Audacity
import addon_utils       # Show Addon Preferences
from shutil import copy2 # Copy files

# Language Definitions for UI
lang_button1 = \
    "Edit (Audacity)"
lang_button1_detail = \
    "Edit in Audacity"
lang_button2 = \
    "Integrate Edit (Audacity)"
lang_button2_detail = \
    "Integrate edited audio from Audacity"
lang_button4 = \
    "General Settings"
lang_button4_detail = \
    "Edit general settings of AudacityLink"
# lang_text1 = \
#     "Edit and export via (File > Export Audio) in Audacity as .wav (!!!Do not touch the file name!!!)?"
# lang_text1_detail = lang_text1
# lang_error1 = \
#     "The sound file must not be packed!"
lang_error2 = \
    "Could not find Audacity!\nPlease edit Audacity path under User Preferences > Add-ons > Audacity-Link."
lang_filepath1 = \
    "Audacity Executable (Classpath if empty)"
lang_preferences1 = \
    "AudacityLink Addon Preferences"
lang_enum1_name = \
    "Replace"
lang_enum1_desc = \
    "Replace current sound strip with edited one"
lang_enum2_name = \
    "Both"
lang_enum2_desc = \
    "Keep current sound strip and add edited one"
lang_enum3_name = \
    "Both in Meta-Group"
lang_enum3_desc = \
    "Add Meta-Group containing current sound strip and edited one"
lang_al_import = \
    "Integration Method:"
lang_export = \
    "Export"
lang_import = \
    "Import"
lang_settings = \
    "Settings"
lang_al_import_keep = \
    "Keep original strip"
lang_al_import_meta = \
    "Wrap both in meta strip"
lang_enumexport1_name = \
    "Session TEMP"
lang_enumexport1_desc = \
    "Temporar Blender Session Directory - Cleared after closing Blender"
lang_enumexport2_name = \
    "System TEMP"
lang_enumexport2_desc = \
    "Temporar Directory of the Operating System"
lang_enumexport3_name = \
    "Custom Directory"
lang_enumexport3_desc = \
    "Custom Directory with a User-defined Path"
lang_al_export = \
    "Path"
lang_al_import_fromsame = \
    "Same Directory as for Export"
lang_custompath = lang_enumexport3_name
lang_importcustom = \
    "Custom Path to the .wav File"
lang_al_import_copyfile = \
    "Copy Edit to original Directory"
lang_al_import_copyfile_desc = \
    "Copy edited File back to Directory of original File (always true for reimport from temp directories)"
lang_al_stripnotfound = \
    "Strip %s does not exist."


# Variable/Type declarations
class SoundStripAdditionals(bpy.types.PropertyGroup):
    """Variables per Strip"""
    ## http://blender.stackexchange.com/questions/26898/how-to-create-a-folder-dialog/26906#26906
    
    # GENERAL
    # ID used in Audacity Project filename
    al_tmpID = bpy.props.IntProperty(name = "AudacityLink-TMP-Filename")
    #
    # EXPORT
    # Export directory
    al_export = bpy.props.EnumProperty(
        items=(
            ('BLENDER_TEMP', lang_enumexport1_name, lang_enumexport1_desc),
            ('SYSTEM_TEMP', lang_enumexport2_name, lang_enumexport2_desc),
            ('CUSTOM', lang_enumexport3_name, lang_enumexport3_desc),
        ),
        name=lang_al_export,
        default="BLENDER_TEMP"
    )
    # Custom export directory
    al_exportcustom = bpy.props.StringProperty(
        name="",
        description=lang_custompath,
        subtype='DIR_PATH',
        default='//'
    )
    #
    # IMPORT
    # Keep original strip
    al_import_keep = bpy.props.BoolProperty(
        name=lang_al_import_keep,
        default=True
    )
    # Encapsulate original and imported strip in single meta strip
    al_import_meta = bpy.props.BoolProperty(
        name=lang_al_import_meta,
        default=False
    )
    # Import from export directory
    al_import_fromsame = bpy.props.BoolProperty(
        name=lang_al_import_fromsame,
        default=True
    )
    # Custom import directory
    al_importcustom = bpy.props.StringProperty(
        name="",
        description=lang_importcustom,
        subtype='FILE_PATH',
        default='//'
    )
    # Copy file to destination
    al_import_copy = bpy.props.BoolProperty(
        name=lang_al_import_copyfile,
        description=lang_al_import_copyfile_desc,
        default=False
    )

# GLOBAL (Variables per project)
# (Use of WindowManager type is cheaty, but it is the best one can do)
# Always true (replaces al_import_copy in certain conditions for seemingly being true - only decoration)
bpy.types.WindowManager.AL_IMPORT_COPY_TRUE = bpy.props.BoolProperty(
    name=lang_al_import_copyfile,
    description=lang_al_import_copyfile_desc,
    default=True )

# [GUI]
class AudacityLinkAddonPreferences(bpy.types.AddonPreferences):
    """GUI: Custom Addon Preferences"""
    # Copyed from https://docs.blender.org/api/blender_python_api_2_78_3/bpy.types.AddonPreferences.html
    bl_idname = __name__
    filepath = bpy.props.StringProperty(
            name=lang_filepath1,
            subtype='FILE_PATH',
            )
    def draw(self, context):
        layout = self.layout
        layout.label(text=lang_preferences1)
        layout.prop(self, "filepath")

class SEQUENCER_PT_AudacityLink(bpy.types.Panel):
    """GUI: AudacityLink-Panel for Sequencer Sound Strips showing new Operators and Properties"""
    bl_label = "AudacityLink"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    @classmethod
    def poll(cls, context):
        strip = act_strip(context)
        if not strip:
            return False
        return (strip.type == 'SOUND')
    def draw(self, context):
        layout = self.layout
        st = context.space_data
        strip = act_strip(context)
        sound = strip.sound
        if sound is not None:
            col = layout.column(align=True)
            col.operator("audacitylink.exporttemp", icon = "MODIFIER")
            col.operator("audacitylink.importtemp", icon = "FILE_TICK")
            
            bigbox = layout.box()
            bigbox.label(text=lang_settings)
            box = bigbox.box()
            box.label(text=lang_export)
            
            box.prop(strip.sound_strip_additionals, "al_export")
            
            if strip.sound_strip_additionals.al_export=='CUSTOM':
                box.prop(strip.sound_strip_additionals, "al_exportcustom")
            
            box = bigbox.box()
            box.label(text=lang_import)
            # Copy always when saved in TEMP
            col = box.column(align=True)
            if not copyImportRequired(strip):
                col.prop(strip.sound_strip_additionals, "al_import_copy")
            else:
                col.enabled = False
                col.prop(context.window_manager, "AL_IMPORT_COPY_TRUE")
            box.prop(strip.sound_strip_additionals, "al_import_fromsame")
            
            if not strip.sound_strip_additionals.al_import_fromsame:
                box.prop(strip.sound_strip_additionals, "al_importcustom")
                
            box.prop(strip.sound_strip_additionals, "al_import_keep")
            col = box.column(align=True)
            col.enabled = strip.sound_strip_additionals.al_import_keep
            col.prop(strip.sound_strip_additionals, "al_import_meta")
            
            bigbox.operator("audacitylink.settings", icon = "PREFERENCES")
            

# OPERATORS
class OBJECT_OT_AudacityLinkExportTemp(bpy.types.Operator):
    """Operator: AudacityLink Export"""
    bl_label = lang_button1
    bl_idname = "audacitylink.exporttemp"
    bl_description = lang_button1_detail
    def execute(self, context):
        export_tmp(self, context)
        return{"FINISHED"}


class OBJECT_OT_AudacityLinkImportTemp(bpy.types.Operator):
    """Operator: AudacityLink Import"""
    bl_label = lang_button2
    bl_idname = "audacitylink.importtemp"
    bl_description = lang_button2_detail
    
    @classmethod
    def poll(cls, context):
        sound = act_strip(context)
        return (sound.sound_strip_additionals.al_tmpID > 0)
    
    def execute(self, context):
        importTMP(self, context)
        return{"FINISHED"}


class OBJECT_OT_AudacityLinkSettings(bpy.types.Operator):
    """Operator: Settings - Opens Addon Preferences"""
    bl_label = lang_button4
    bl_idname = "audacitylink.settings"
    bl_description = lang_button4_detail
    
    def execute(self, context):
        bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
        context.user_preferences.active_section = 'ADDONS'
        bpy.data.window_managers["WinMan"].addon_search = "AudacityLink"
        bpy.ops.wm.addon_expand(module="audacitylink")
        
        # Expand (see startup/bl_operators/wm.py, WM_OT_addon_expand)
        try:
            mod = addon_utils.addons_fake_modules.get("audacitylink")
        except:
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        info = addon_utils.module_bl_info(mod)
        info["show_expanded"] = True
        return{"FINISHED"}
    
#[/GUI]


# IM- & EXPORT-LOGIC
def export_tmp(self, context):
    """Export Strip to Audacity Project"""
    # Definitions
    strip = act_strip(context)
    actual_fps = context.scene.render.fps / context.scene.render.fps_base
    if(strip.sound.packed_file):
        self.report(type = {'ERROR_INVALID_CONTEXT'}, message = lang_error1)
        return {'CANCELLED'}
    audiopath = bpy.path.abspath(strip.sound.filepath, library=strip.sound.library)
    filename = os.path.basename(audiopath)
    offset = float(strip.frame_start)/actual_fps
    length = float(strip.frame_duration)/actual_fps
    
    # Generate AUD Project
    # Choose random file name
    while(os.path.isdir(getExportPath(strip.sound_strip_additionals)+\
            str(strip.sound_strip_additionals.al_tmpID)+"_data")\
        or os.path.isfile(getExportPath(strip.sound_strip_additionals)+str(strip.sound_strip_additionals.al_tmpID)+\
            ".aup")\
        or os.path.isfile(bpy.app.tempdir+str(strip.sound_strip_additionals.al_tmpID)+".wav")):
        strip.sound_strip_additionals.al_tmpID = random.randint(1,2**30)

    # Write file
    audFilepath = getExportPath(strip.sound_strip_additionals)\
        +str(strip.sound_strip_additionals.al_tmpID)+".aup"
    auProjectpath = getExportPath(strip.sound_strip_additionals)\
        +str(strip.sound_strip_additionals.al_tmpID)+"_data"
    audFile = open(audFilepath, "w")
    audFile.write(\
        '<?xml version="1.0" standalone="no" ?>\n' +\
        '<!DOCTYPE project PUBLIC "-//audacityproject-1.3.0//DTD//EN" '+\
        '"http://audacity.sourceforge.net/xml/audacityproject-1.3.0.dtd" >\n'+\
        '<project xmlns="http://audacity.sourceforge.net/xml/"'\
        'projname="' + str(strip.sound_strip_additionals.al_tmpID) + '_data" '+\
        'version="1.3.0" audacityversion="2.1.2" sel0="0.0000000000" sel1="0.0000000000" '+\
        'vpos="0" h="0.0000000000" zoom="86.1328125000" rate="44100.0" snapto="off" '+\
        'selectionformat="hh:mm:ss + milliseconds" frequencyformat="Hz" bandwidthformat="octaves">\n'+\
        '\t<tags/>\n'+\
        '\t<import filename="'+filename+'" offset="0"/>\n'+\
        '\t<labeltrack name="Blender Labels">\n')
    # Add Timeline Markers to AUD file - short but useful
    for TimelineMarker in bpy.context.scene.timeline_markers:
        temp_time = float(TimelineMarker.frame)/actual_fps-offset
        if(temp_time > 0 and temp_time <= length):
            audFile.write('\t\t<label t="'+str(temp_time)+'" t1="'+str(temp_time)+\
                '" title="'+TimelineMarker.name+'"/>\n')
    audFile.write(\
        '\t</labeltrack>\n'+ \
        '</project>\n')
    audFile.close()
    
    # Generate Audacity Project Directory
    os.mkdir(auProjectpath)
    copy2(audiopath, auProjectpath)
    
    #Load user preferences
    user_preferences = context.user_preferences
    addon_prefs = user_preferences.addons["audacitylink"].preferences
    filepath=addon_prefs.filepath
    
    # Launch Audacity
    if not filepath:
        try:
            audProgram = subprocess.Popen(["audacity", audFilepath])
        except Exception:
            self.report(type = {'ERROR'}, message = lang_error2)
    else:
        try:
            audProgram = subprocess.Popen([filepath, audFilepath])
        except Exception:
            print(Exception)
            self.report(type = {'ERROR'}, message = lang_error2)
        
    
def importTMP(self, context):
    """Import (.wav) file to Strip depending on Properties of old Strip"""
    strip = act_strip(context)
    if strip.sound_strip_additionals.al_import_keep:
        if strip.sound_strip_additionals.al_import_meta:
            # Meta-Strip
            
            #  Select Strip
            bpy.ops.sequencer.select_all(action='DESELECT')
            strip.select = True
            
            #  Encapsulate in Meta Strip
            bpy.ops.sequencer.meta_make()
            bpy.ops.sequencer.meta_toggle()
            
            #  Add Strip
            addStrip(self, context, strip)
            
            bpy.ops.sequencer.meta_toggle()
        else:
            # Both Add Strip
            addStrip(self, context, strip)
    else:
        # Replace
        #  Get Channel and Start Frame
        channel = strip.channel
        frame_start = strip.frame_start
        #  Delete
        bpy.ops.sequencer.select_all(action='DESELECT')
        strip.select = True
        bpy.ops.sequencer.delete()
        #  Try to add in channel, otherwise add in other channel
        addStrip(self, context, strip, channel, frame_start)
        

# AUXILIARY FUNCTIONS
def addStrip(self, context, strip, channel=None,frame_start=None):
    """Add new Strip to VSE

    Args:
        strip: Old sound strip
        channel: Channel number of new strip
        frame_start: Start frame of next channel
    """
    # Default Values
    if(channel == None):
        channel = strip.channel
    if(frame_start == None):
        frame_start = strip.frame_start
    
    # Path of edit
    src_path = getImportPath(strip.sound_strip_additionals)
    
    # Path to import new strip from (If different from src_path, edited file is copied to this path)
    dest_path=src_path
    # Name of new strip
    name = os.path.splitext(strip.name)[0] + "_EDIT"
    # Copy edited file if choosen so
    if strip.sound_strip_additionals.al_import_copy or copyImportRequired(strip):
        edit = 1
        dirname = os.path.dirname(strip.filepath)
        name = os.path.splitext(strip.name)[0]
        ext = os.path.splitext(src_path)[1]
        while os.path.isfile(os.path.join(dirname,name+'_EDIT'*edit+ext)):
            edit += 1
        
        dest_path=os.path.join(dirname,name+'_EDIT'*edit+ext)
        copy2(src_path, dest_path)
        
    while context.scene.sequence_editor.sequences_all.find(name) > 0:
        name += "_EDIT"
        
    if not os.path.isfile(dest_path):
        self.report(
            type = {"ERROR"},
            message = lang_al_stripnotfound % dest_path)
        return {'CANCELLED'}
    newstrip = context.scene.sequence_editor.sequences.new_sound(name, dest_path, channel, frame_start)
    bpy.ops.sequencer.select_all(action='DESELECT')
    newstrip.select = True
    bpy.ops.sequencer.copy()
    bpy.ops.sequencer.delete()
    bpy.ops.sequencer.paste()


def copyImportRequired(strip):
    """Returns whether the import path requires copying the file before importing

    true if import path is same as export path (al_import_fromsame==True) and export path is TEMP
    """
    return (not strip.sound_strip_additionals.al_export=='CUSTOM' \
        and strip.sound_strip_additionals.al_import_fromsame)


def act_strip(context):
    """Get selected/active strip

    Copyed from space_sequencer.py
    """
    try:
        return context.scene.sequence_editor.active_strip
    except AttributeError:
        return None


def getExportPath(strip_additionals):
    """Get configured export path"""
    type = strip_additionals.al_export
    if(type == 'BLENDER_TEMP'):
        return bpy.app.tempdir
    elif(type == 'SYSTEM_TEMP'):
        return tempfile.gettempdir()+os.sep
    else:
        return bpy.path.abspath(strip_additionals.al_exportcustom)


def getImportPath(strip_additionals):
    """Get configured import path"""
    src_path = ''
    if strip_additionals.al_import_fromsame:
        src_path = getExportPath(strip_additionals)
    else:
        src_path = bpy.path.abspath(strip_additionals.al_importcustom)
    if os.path.basename(src_path) == '':
        src_path = os.path.join(src_path, str(strip.sound_strip_additionals.al_tmpID)+".wav")
    return src_path
        
def add_to_menu_exporttemp(self, context) :
    self.layout.operator("audacitylink.exporttemp", icon = "MODIFIER")
        
def add_to_menu_importtemp(self, context) :
    self.layout.operator("audacitylink.importtemp", icon = "FILE_TICK")

    
# DEFAULT ADDON REGISTER/UNREGISTER METHODS (nothing special to see here, move along)
def register():
    bpy.utils.register_module(__name__)
    bpy.types.SoundSequence.sound_strip_additionals = bpy.props.PointerProperty(type=SoundStripAdditionals)

def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    print("[REGISTERING AUDACITYLINK]")
    register()
    print("[REGISTERING AUDACITYLINK DONE]")
