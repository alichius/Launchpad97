#Embedded file name: /Users/versonator/Jenkins/live/output/mac_64_static/Release/python-bundle/MIDI Remote Scripts/Launchpad_Pro/SpecialSessionRecordingComponent.py
import Live
from _Framework.ClipCreator import ClipCreator
from _Framework.SessionRecordingComponent import SessionRecordingComponent, track_playing_slot, track_is_recording
_Q = Live.Song.Quantization

class SpecialProSessionRecordingComponent(SessionRecordingComponent):

    def __init__(self, target_track_component, control_surface, *a, **k):
        self._control_surface = control_surface
        self._target_track_component = target_track_component
        super(SpecialProSessionRecordingComponent, self).__init__(ClipCreator(), True, *a, **k)
        self._is_record_mode = False
        
    def _set_parent(self, parent):        
        self._parent = parent        

    def set_record_mode(self, record_mode):
        #Live.Base.log("SpecialSessionRecordingComponent - set_record_mode:  " + str(record_mode))
        self._is_record_mode = record_mode
        
    def _is_fixed_length_on(self):
        #Live.Base.log("SpecialSessionRecordingComponent - _is_fixed_length_on:  " + str(self._parent._is_fixed_length_on()))
        return self._parent._is_fixed_length_on()    

    def set_enabled(self, enable):
        #Live.Base.log("SpecialSessionRecordingComponent - set_enabled:  " + str(enable))
        super(SpecialProSessionRecordingComponent, self).set_enabled(enable)
        
    def _get_fixed_length(self):
        return self._parent._get_fixed_length()   

    def _get_launch_quant(self):
        return self._parent._get_launch_quant()      
    
    def _on_record_button_value(self):
        if self.is_enabled():
            if self._is_record_mode:
                self._handle_pro_mode_record_behavior()
            else:
                if not self._stop_recording():
                    self._start_recording()
                    self._control_surface.show_message("SESSION RECORD ON")
                    #Live.Base.log("SpecialSessionRecordingComponent show_message SESSION RECORD ON")
                else:
                    self._control_surface.show_message("SESSION RECORD OFF")
                    #Live.Base.log("SpecialSessionRecordingComponent show_message SESSION RECORD OFF")
                    

    def _handle_pro_mode_record_behavior(self):
        #Live.Base.log("SpecialSessionRecordingComponent - _handle_pro_mode_record_behavior")
        track = self._target_track_component.target_track #Selected Track
        status = self.song().session_record_status
        was_recording = status != Live.Song.SessionRecordStatus.off or self.song().session_record
        if self._track_can_record(track) and not was_recording:
            #Live.Base.log("SpecialSessionRecordingComponent - REC IN NEW SLOT")
            if self._is_fixed_length_on():
                #Live.Base.log("SpecialProSessionRecordingComponent Not should_overdub" + str(self._get_fixed_length()))
                self.song().trigger_session_record(self._get_fixed_length())
            else:
                self.song().trigger_session_record()
            #scene_index = list(self.song().scenes).index(self.song().view.selected_scene)
        elif not self._stop_recording():
            self._start_recording()
            self._control_surface.show_message("SESSION RECORD ON")
        else:
            self._control_surface.show_message("SESSION RECORD OFF")

    def _track_can_record(self, track):
        return track.can_be_armed and (track.arm or track.implicit_arm) and track in self.song().tracks
            