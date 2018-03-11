#Embedded file name: /Users/versonator/Jenkins/live/output/mac_64_static/Release/python-bundle/MIDI Remote Scripts/Launchpad_Pro/SpecialSessionRecordingComponent.py
import Live
from _Framework.ClipCreator import ClipCreator
from _Framework.SessionRecordingComponent import SessionRecordingComponent, track_playing_slot, track_is_recording

class SpecialProSessionRecordingComponent(SessionRecordingComponent):

    def __init__(self, target_track_component, *a, **k):
        self._target_track_component = target_track_component
        super(SpecialProSessionRecordingComponent, self).__init__(ClipCreator(), True, *a, **k)
        self._is_record_mode = False
        self._is_fixed_length_mode = False
        
    def _set_parent(self, parent):        
        self._parent = parent        

    def set_record_mode(self, record_mode):
        #Live.Base.log("SpecialSessionRecordingComponent - set_record_mode:  " + str(record_mode))
        self._is_record_mode = record_mode
        
    def set_fixed_length_mode(self, fixed_length_mode):
        #Live.Base.log("SpecialSessionRecordingComponent - set_record_mode:  " + str(record_mode))
        self._is_fixed_length_mode = fixed_length_mode        

    def set_enabled(self, enable):
        #Live.Base.log("SpecialSessionRecordingComponent - set_enabled:  " + str(enable))
        super(SpecialProSessionRecordingComponent, self).set_enabled(enable)
        
    def _get_fixed_length(self):
        return self._parent._get_fixed_length()        
        
    def _on_record_button_value(self):
        if self.is_enabled():
            if self._is_record_mode:
                self._handle_note_mode_record_behavior()
            elif not self._stop_recording():
                self._start_recording()

    def _handle_note_mode_record_behavior(self):
        Live.Base.log("SpecialSessionRecordingComponent - _handle_note_mode_record_behavior")
        track = self._target_track_component.target_track
        
        if self._track_can_record(track):
            playing_slot = track_playing_slot(track)
            should_overdub = not track_is_recording(track) and playing_slot != None
            if should_overdub:
                self.song().overdub = not self.song().overdub
                if not self.song().is_playing:
                    self.song().is_playing = True
            elif not self._stop_recording():
                self._prepare_new_slot(track)
                if self._is_fixed_length_mode:
                    self.song().trigger_session_record(self._get_fixed_length())
                else:
                    self.song().trigger_session_record()
        elif not self._stop_recording():
            self._start_recording()

    def _prepare_new_slot(self, track):
        song = self.song()
        song.overdub = False
        view = song.view
        try:
            slot_index = list(song.scenes).index(view.selected_scene)
            track.stop_all_clips(False)
            self._jump_to_next_slot(track, slot_index)
        except Live.Base.LimitationError:
            self._handle_limitation_error_on_scene_creation()

    def _track_can_record(self, track):
        #trk_can_record = trk.can_be_armed and (trk.arm or trk.implicit_arm) and not slot.has_clip and self.song().session_record_status == Live.Song.SessionRecordStatus.off
        return track in self.song().tracks and track.can_be_armed
            