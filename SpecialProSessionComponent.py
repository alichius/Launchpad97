import Live
from _Framework.SessionComponent import SessionComponent
from ClipSlotMK2 import ClipSlotMK2
from _Framework.SceneComponent import SceneComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.SubjectSlot import subject_slot
from _Framework.ClipSlotComponent import ClipSlotComponent
from _Framework import Task
from _Framework.Util import in_range
from _Framework.SubjectSlot import subject_slot_group
import time
from SpecialProSessionRecordingComponent import SpecialProSessionRecordingComponent
from TargetTrackComponent import TargetTrackComponent
_Q = Live.Song.Quantization
Rec_Q = Live.Song.RecordingQuantization

REC_QNTZ_RATES = [
Rec_Q.rec_q_quarter,
Rec_Q.rec_q_eight,
Rec_Q.rec_q_eight_triplet,
Rec_Q.rec_q_eight_eight_triplet,
Rec_Q.rec_q_sixtenth,
Rec_Q.rec_q_sixtenth_triplet,
Rec_Q.rec_q_sixtenth_sixtenth_triplet,
Rec_Q.rec_q_thirtysecond]

REC_QNTZ_FIXED_RATES = [
Rec_Q.rec_q_quarter,
Rec_Q.rec_q_eight,
Rec_Q.rec_q_eight_triplet,
Rec_Q.rec_q_sixtenth,
Rec_Q.rec_q_sixtenth_triplet]

REC_QNTZ_NAMES = ('1/4', '1/8', '1/8t', '1/8+t', '1/16', '1/16t', '1/16+t', '1/32')
REC_QNTZ_RATES_LEN = len(REC_QNTZ_RATES)


LAUNCH_QNTZ_RATES = [
_Q.q_8_bars,
_Q.q_4_bars,
_Q.q_2_bars,
_Q.q_bar,
_Q.q_half,
_Q.q_half_triplet,
_Q.q_quarter,
_Q.q_quarter_triplet,
_Q.q_eight,
_Q.q_eight_triplet,
_Q.q_sixtenth,
_Q.q_sixtenth_triplet,
_Q.q_thirtytwoth
]

LAUNCH_QNTZ_FIXED_RATES = [
_Q.q_2_bars,
_Q.q_bar,
_Q.q_quarter,
_Q.q_eight,
_Q.q_sixtenth
]
LAUNCH_QNTZ_NAMES = ('8 Bars', '4 Bars', '2 Bars', '1 Bar', '1/2', '1/2t', '1/4', '1/4t', '1/8', '1/8t', '1/16', '1/16t', '1/32')
LAUNCH_QNTZ_RATES_LEN = len(LAUNCH_QNTZ_RATES)

FIXED_LENGTH_VALUES = [0, 1, 3, 7, 15]
MAX_FIXED_LENGTH = 31


class SpecialClipSlotComponent(ClipSlotComponent):
    quantization_component = None
    device = True
    
    def __init__(self, should_arm = None, *a, **k):
        super(SpecialClipSlotComponent, self).__init__(*a, **k)
        
    def _set_parent(self, parent):        
        self._parent = parent
    
    def _do_select_clip(self, clip_slot):
        super(SpecialClipSlotComponent, self)._do_select_clip(clip_slot)
        if self._clip_slot is not None:
            clip = clip_slot.clip
            
            if not self.application().view.is_view_visible('Detail'):
                self.application().view.show_view('Detail')
                self.device = True
            
            if clip:
                if not self.application().view.is_view_visible('Detail/Clip') and self.device:
                    self.application().view.show_view('Detail/Clip')
            else:
                self.device = False
                    
            if not self.application().view.is_view_visible('Detail/DeviceChain') and not self.device and not self._is_doubling():
                self.application().view.show_view('Detail/DeviceChain')            
            
            self.device = not self.device    

    def _do_duplicate_clip(self):
        if self._clip_slot:
            slot = self._clip_slot
            should_launch = True
            song = self._get_song()
            try:
                clip = slot.clip if slot is not None else None
                if clip is not None:
                    track = slot.canonical_parent
                    view = song.view
                    try:
                        start_duplicate = should_launch and clip.is_playing
                        target_index = list(track.clip_slots).index(slot)
                        destination_index = track.duplicate_clip_slot(target_index)
                        view.highlighted_clip_slot = track.clip_slots[destination_index]
                        view.detail_clip = view.highlighted_clip_slot.clip
                        if start_duplicate:
                            view.highlighted_clip_slot.fire(force_legato=True, launch_quantization=_Q.q_no_q)
                    except Live.Base.LimitationError:
                        pass
                    except RuntimeError:
                        pass
            except (AttributeError, TypeError):
                pass
            
    def _do_double_loop(self, clip_slot):
        self._do_select_clip(clip_slot)
        if self._can_duplicate_loop():
            try:
                self._get_song().view.detail_clip.duplicate_loop()
            except (AttributeError, TypeError):
                pass
            except RuntimeError:
                pass

    def _can_duplicate_loop(self):
        clip = self.song().view.detail_clip
        return clip and clip.is_midi_clip

    def _do_quantize_clip(self, clip_slot):
        clip = clip_slot.clip
        if clip:
            assert isinstance(clip, Live.Clip.Clip)
            clip.quantize(self._get_record_quantization(), 1.0) 
            
    def _do_track_arm(self):
        if self._clip_slot:
            track = self._clip_slot.canonical_parent
            if track.can_be_armed and not track.arm:
                if self._get_song().exclusive_arm:
                    for t in self._get_song().tracks:
                        if t.can_be_armed and t.arm:
                            t.arm = False

                track.arm = True
                if self._get_song().view.selected_track != track:
                    self._get_song().view.selected_track = track
            if not self._get_song().session_record and self._clip_slot.has_clip:
                self._get_song().session_record = True            

    def _do_launch_clip(self, value):
        #Live.Base.log("SpecialClipSlotComponent _do_launch_clip")
        button = self._launch_button_value.subject # MATRIX BUTTON
        object_to_launch = self._clip_slot # BUTTON SLOT
        launch_pressed = value or not button.is_momentary() # LAUNCH MSG
        
        if self.has_clip(): #Have CLIP
            #Live.Base.log("SpecialClipSlotComponent has_clip")
            object_to_launch = self._clip_slot.clip
        else:
            self._has_fired_slot = True
            
        if button.is_momentary():
            if(self._is_fixed_length_on() and not self.has_clip()):
                #Live.Base.log("SpecialClipSlotComponent fire _get_fixed_length")
                object_to_launch.fire(record_length=self._get_fixed_length())
            else:
                #Live.Base.log("SpecialClipSlotComponent set_fire_button_state")
                object_to_launch.set_fire_button_state(value != 0)
        elif launch_pressed:
            if(self._is_fixed_length_on() and  self.has_clip()):
                #Live.Base.log("SpecialClipSlotComponent fire _get_fixed_length")
                object_to_launch.fire(record_length=self._get_fixed_length())
            else:
                #Live.Base.log("SpecialClipSlotComponent fire")
                object_to_launch.fire()    
        if launch_pressed and self.song().select_on_launch:
            #Live.Base.log("SpecialClipSlotComponent select_on_launch")
            self.song().view.highlighted_clip_slot = self._clip_slot
            self.application().view.show_view('Detail/Clip')

    def _is_shifting(self):
        return self._parent._is_shifting()
    
    def _is_deleting(self):
        return self._parent._is_deleting()
    
    def _is_duplicating(self):
        return self._parent._is_duplicating()
        
    def _is_doubling(self):
        return self._parent._is_doubling()
    
    def _is_quantizing(self):
        return self._parent._is_quantizing()  
    
    def _get_song(self):
        return self._parent._get_song()
    
    def _get_record_quantization(self):
        return self._parent._get_record_quantization()
    
    def _is_fixed_length_on(self):
        return self._parent._is_fixed_length_on()
        
    def _get_fixed_length(self):
        return self._parent._get_fixed_length()
    
    def _should_arm(self):
        return self._parent._should_arm()

    @subject_slot('value')
    def _launch_button_value(self, value):
        if self.is_enabled() and self._clip_slot is not None:
            if self._is_deleting() and value:
                if self._is_shifting():
                    #Live.Base.log("SpecialClipSlotComponent _do_delete_scene")
                    self._parent._do_delete_scene(self._parent)
                else:
                    #Live.Base.log("SpecialClipSlotComponent _do_delete_clip")
                    self._do_delete_clip()
            elif self._is_duplicating() and value:
                if self._is_shifting():
                    #Live.Base.log("SpecialClipSlotComponent _do_duplicate_scene")
                    self._parent._do_duplicate_scene()
                else:
                    #Live.Base.log("SpecialClipSlotComponent _do_duplicate_clip")
                    self._do_duplicate_clip()          
            elif self._is_doubling() and value:
                #Live.Base.log("SpecialClipSlotComponent _do_double_loop")
                self._do_double_loop(self._clip_slot)
            elif self._is_quantizing() and value:
                #Live.Base.log("SpecialClipSlotComponent _do_quantize_clip")
                self._do_quantize_clip(self._clip_slot)
            elif self._is_shifting() and value:
                #Live.Base.log("SpecialClipSlotComponent _do_select_clip")
                self._do_select_clip(self._clip_slot)            
            else:
                if value:
                    if self._should_arm():
                        self._do_track_arm()
                    #Live.Base.log("SpecialClipSlotComponent _do_launch_clip")
                    self._do_launch_clip(value)

class SpecialSceneComponent(SceneComponent):
    clip_slot_component_type = SpecialClipSlotComponent

    def __init__(self, *a, **k):
        super(SpecialSceneComponent, self).__init__(*a, **k)
            
    def _set_parent(self, parent):        
        self._parent = parent
        
    def _is_shifting(self):
        return self._parent._is_shifting()

    def _is_deleting(self):
        return self._parent._is_deleting()
    
    def _is_duplicating(self):
        return self._parent._is_duplicating()
    
    def _is_doubling(self):
        return self._parent._is_doubling()    
    
    def _is_quantizing(self):
        return self._parent._is_quantizing()  
    
    def _get_song(self):
        return self._parent._get_song()
    
    def _get_record_quantization(self):
        return self._parent._get_record_quantization()
    
    def _should_arm(self):
        return self._parent._should_arm()
    
    def _is_fixed_length_on(self):
        return self._parent._is_fixed_length_on()
        
    def _get_fixed_length(self):
        return self._parent._get_fixed_length()
    
    def _do_duplicate_scene(self):
        try:
            song = self._get_song()
            song.duplicate_scene(list(song.scenes).index(self._scene))
        except Live.Base.LimitationError:
            pass
        except RuntimeError:
            pass
        except IndexError:
            pass
        
class SpecialProSessionComponent(SessionComponent):
    scene_component_type = SpecialSceneComponent
    """ Special session subclass that handles ConfigurableButtons """

    def __init__(self, num_tracks, num_scenes, stop_clip_buttons, side_buttons, control_surface, main_selector, livesong = None):
        self._stop_clip_buttons = stop_clip_buttons
        self._control_surface = control_surface
        self._main_selector = main_selector
        self._side_buttons = side_buttons
        self._osd = None
        self._song = livesong
        
        self._shift_button = None
        self._click_button = None
        self._undo_button = None
        self._delete_button = None
        self._duplicate_button = None
        self._double_button = None
        self._quantize_button = None
        self._record_button = None
        
        self._shift_pressed = False
        self._delete_pressed = False
        self._duplicate_pressed = False
        self._double_pressed = False
        self._quantize_pressed = False
        self._record_pressed = False
        self._record_mode_on = False
        
        self._last_button_time = time.time()
        self._last_record_time = time.time()
        self._end_undo_step_task = self._tasks.add(Task.sequence(Task.wait(1.5), Task.run(self.song().end_undo_step)))
        self._end_undo_step_task.kill()
        
        self._record_quantization =Rec_Q.rec_q_sixtenth
        self._record_quantization_on = False
        self._song.add_midi_recording_quantization_listener(self._on_record_quantization_changed_in_live)
        
        self._song.add_clip_trigger_quantization_listener(self._on_clip_trigger_quantization_changed_in_live)
        
        self._fixed_length_on = False
        self._fixed_length = 0
        
        self._song.add_metronome_listener(self._on_metronome_status_changed)
        
        self._session_record = SpecialProSessionRecordingComponent(target_track_component = TargetTrackComponent())
        self._session_record._set_parent(self)
        
        if self._control_surface._mk2_rgb:
            #use custom clip colour coding : blink and pulse for trig and play 
            SceneComponent.clip_slot_component_type = ClipSlotMK2
        SessionComponent.__init__(self, num_tracks = num_tracks, num_scenes = num_scenes, enable_skinning = True, name='Session', is_root=True)
        if self._control_surface._mk2_rgb:
            from .ColorsMK2 import CLIP_COLOR_TABLE, RGB_COLOR_TABLE
            self.set_rgb_mode(CLIP_COLOR_TABLE, RGB_COLOR_TABLE)
            
        self._setup_actions_buttons()    
        self._set_shift_button(self._side_buttons[0]) #Shift + Double Clic  + Clip
        self._set_click_button(self._side_buttons[1]) #Shiftable(Metronome) + Instant
        self._set_undo_button(self._side_buttons[2]) #Shiftable(redo) + Instant
        self._set_quantize_button(self._side_buttons[3]) #Shiftable(Quant Rec)  + Clip
        self._set_double_button(self._side_buttons[4]) #Modifier (Solo) + Clip(Midi)
        self._set_delete_button(self._side_buttons[5])  #Shiftable (scene)  + Clip
        self._set_duplicate_button(self._side_buttons[6]) #Shiftable (scene) + Modifier (Mute) + Clip
        self._set_record_button(self._side_buttons[7]) #Shiftable + Modifier (Arm) + Instant + Clip
        self.update()
        
    def disconnect(self):
        self._song.remove_midi_recording_quantization_listener(self._on_record_quantization_changed_in_live)
        self._song.remove_clip_trigger_quantization_listener(self._on_clip_trigger_quantization_changed_in_live)
        self._end_undo_step_task.kill()
        self._end_undo_step_task = None
        self._record_quantization_on = False
        self._shift_pressed = False
        self._delete_pressed = False
        self._duplicate_pressed = False
        self._double_pressed = False
        self._quantize_pressed = False
        
        self._click_button = None
        self._undo_button = None
        self._shift_button = None
        self._delete_button = None
        self._duplicate_button = None
        self._double_button = None
        self._quantize_button = None
        self._record_button = None
        
    def _is_shifting(self):
        #Live.Base.log("SpecialProSessionComponent _is_shifting: " + str(self._shift_pressed))
        return self._shift_pressed
    
    def _is_deleting(self):
        #Live.Base.log("SpecialProSessionComponent _is_deleting: " + str(self._delete_pressed))
        return self._delete_pressed
    
    def _is_duplicating(self):
        #Live.Base.log("SpecialProSessionComponent _is_duplicating: " + str(self._duplicate_pressed))
        return self._duplicate_pressed
    
    def _is_doubling(self):
        #Live.Base.log("SpecialProSessionComponent _is_doubling: " + str(self._double_pressed))
        return self._double_pressed
    
    def _is_quantizing(self):
        #Live.Base.log("SpecialProSessionComponent _is_quantizing: " + str(self._quantize_pressed))
        return self._quantize_pressed 
    
    def _is_fixed_length_on(self):
        #Live.Base.log("SpecialProSessionComponent _is_fixed_length_on: " + str(self._fixed_length_on))
        return self._fixed_length_on
    
    def _should_arm(self):
        #Live.Base.log("SpecialProSessionComponent _should_arm: " + str(self._record_pressed or self._record_mode_on))
        return self._record_pressed or self._record_mode_on
    
    def _is_enabled(self):
        return self.is_enabled()
    
    def _get_song(self):
        return self._song
    
    def _get_record_quantization(self):
        return self._record_quantization

    def _setup_actions_buttons(self):
        for scene_index in xrange(self._num_scenes):
            scene = self.scene(scene_index)
            scene._set_parent(self)
            for track_index in xrange(self._num_tracks):
                slot = scene.clip_slot(track_index)
                slot._set_parent(scene)

# SHIFT Button
    def _set_shift_button(self, button=None):
        assert (isinstance(button, (ButtonElement, type(None))))
        if (self._shift_button != button):
            if (self._shift_button != None):
                self._shift_button.remove_value_listener(self._shift_button_value)
            self._shift_button = button
            if (self._shift_button != None):
                assert isinstance(button, ButtonElement)
                self._shift_button.add_value_listener(self._shift_button_value, identify_sender=True)

    def _shift_button_value(self, value, sender):
        #Live.Base.log("SpecialProSessionComponent _shift_button_value: " + str(value) + " - enabled:" + str(self.is_enabled()))
        assert (self._shift_button != None)
        assert (value in range(128))
        if self.is_enabled():
            if ((value is not 0) or (not sender.is_momentary())):
                self._control_surface.show_message("SELECT/VIEW CLIP (SET LAUNCH QUANTIZATION)?")
                self._shift_pressed = True
            else:
                self._shift_pressed = False
                if (time.time() - self._last_button_time) < 0.25:
                    self.application().view.hide_view('Detail')
                self._last_button_time = time.time()
            self._update_shift_button()
            self._update_stop_track_clip_buttons()
            
    def _update_shift_button(self):
        #Live.Base.log("SpecialProSessionComponent _update_shift_button")
        if self.is_enabled() and self._shift_button != None:
            self._shift_button.set_on_off_values("ProSession.Shift")
            if self._shift_pressed:
                self._shift_button.turn_on()
            else:
                self._shift_button.turn_off()
                
    def _increment_launch_qntz_value(self):
        #Live.Base.log("SpecialProSessionComponent _increment_launch_qntz_value")
        quant_value = self._get_song().clip_trigger_quantization
        quant_on = quant_value != _Q.q_no_q
        if(quant_on):
            quant_idx = LAUNCH_QNTZ_RATES.index(quant_value)
            if(quant_idx<LAUNCH_QNTZ_RATES_LEN-1):
                self.song().clip_trigger_quantization = LAUNCH_QNTZ_RATES[quant_idx+1]
        else:
            self.song().clip_trigger_quantization = _Q.q_8_bars
            
    def _decrement_launch_qntz_value(self):
        #Live.Base.log("SpecialProSessionComponent _decrement_launch_qntz_value")        
        quant_value = self._get_song().clip_trigger_quantization
        quant_on = quant_value != _Q.q_no_q
        if(quant_on):
            quant_idx = LAUNCH_QNTZ_RATES.index(quant_value)
            if(quant_idx>0):
                self.song().clip_trigger_quantization = LAUNCH_QNTZ_RATES[quant_idx-1]              
            else:
                self.song().clip_trigger_quantization = _Q.q_no_q
                
# CLICK button and its listener
    def _set_click_button(self, button=None):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._click_button != None:
            self._click_button.remove_value_listener(self._click_value)
        self._click_button = button
        if self._click_button != None:
            self._click_button.add_value_listener(self._click_value)

    def _click_value(self, value):
        #Live.Base.log("SpecialProSessionComponent _click_value: " + str(value) + " - enabled:" + str(self.is_enabled()))
        assert (self._click_button != None)
        assert (value in range(128))
        if self.is_enabled():
            if self._shift_pressed:
                if value != 0 or not self._click_button.is_momentary():
                    self.song().metronome = not self.song().metronome
                    if self.song().metronome :
                        self._control_surface.show_message("METRONOME ON")
                    else:
                        self._control_surface.show_message("METRONOME OFF")
            else:
                self._tap_tempo_value(value)
            self.update()
            
    def _tap_tempo_value(self, value):
        #Live.Base.log("SpecialProSessionComponent _tap_tempo_value")
        if self.is_enabled():
            if value or not self._click_button.is_momentary():
                if not self._end_undo_step_task.is_running:
                    self.song().begin_undo_step()
                self._end_undo_step_task.restart()
                self.song().tap_tempo()
         
    def _update_click_button(self):
        #Live.Base.log("SpecialProSessionComponent _update_click_button")
        if self.is_enabled() and self._click_button != None:
            self._click_button.set_on_off_values("ProSession.Click")
            if self.song().metronome:
                self._click_button.turn_on()
            else:
                self._click_button.turn_off()   
                
    def _on_metronome_status_changed(self):
        #Live.Base.log("SpecialProSessionComponent _on_metronome_status_changed")
        if self.is_enabled():
            self._update_click_button()            

# UNDO button and its listener
    def _set_undo_button(self, button=None):
        assert isinstance(button, (ButtonElement, type(None)))
        if (self._undo_button != None):
            self._undo_button.remove_value_listener(self._undo_button_value)
        self._undo_button = button
        if (self._undo_button != None):
            self._undo_button.add_value_listener(self._undo_button_value, identify_sender=True)

    def _undo_button_value(self, value, sender):
        #Live.Base.log("SpecialProSessionComponent _undo_button_value: " + str(value) + " - enabled:" + str(self.is_enabled()))
        if self.is_enabled():
            if value != 0:
                if self._shift_pressed:
                    if self.song().can_redo:
                        self.song().redo()
                        self._control_surface.show_message("REDO")
                    else:
                        self._control_surface.show_message("CAN`T REDO!!") 
                else:
                    if self.song().can_undo:
                        self.song().undo()
                        self._control_surface.show_message("UNDO")
                    else:
                        self._control_surface.show_message("CAN`T UNDO!!") 
            self._update_undo_button()                    

    def _update_undo_button(self):
        #Live.Base.log("SpecialProSessionComponent _update_undo_button")
        if self.is_enabled() and self._undo_button != None:
            self._undo_button.set_on_off_values("ProSession.Undo")
            if self.song().can_undo:
                self._undo_button.turn_on()
            else:
                self._undo_button.turn_off()

# QUANTIZE button and its listener
    def _set_quantize_button(self, button=None):
        assert (isinstance(button, (ButtonElement, type(None))))
        if (self._quantize_button != button):
            if (self._quantize_button != None):
                self._quantize_button.remove_value_listener(self._quantize_button_value)
            self._quantize_button = button
            if (self._quantize_button != None):
                assert isinstance(button, ButtonElement)
                self._quantize_button.add_value_listener(self._quantize_button_value, identify_sender=True)

    def _quantize_button_value(self, value, sender):
        #Live.Base.log("SpecialProSessionComponent _quantize_button_value: " + str(value) + " - enabled:" + str(self.is_enabled()))
        assert (self._quantize_button != None)
        assert (value in range(128))
        if self.is_enabled():
            
            if self._shift_pressed:
                if ((value is not 0) or (not sender.is_momentary())):
                    self._record_quantization_on = not self._record_quantization_on
                    self.song().midi_recording_quantization = self._record_quantization if self._record_quantization_on else Rec_Q.rec_q_no_q                    
            else:    
                if ((value is not 0) or (not sender.is_momentary())):
                    self._control_surface.show_message("QUANTIZE CLIP (SET REC QUANTIZATION)?")
                    self._quantize_pressed = True
                else:
                    self._quantize_pressed = False
            self._update_stop_track_clip_buttons()
     
    def _update_quantize_button(self):
        #Live.Base.log("SpecialProSessionComponent _update_quantize_button")
        if self.is_enabled() and self._quantize_button != None:
            self._quantize_button.set_on_off_values("ProSession.Quantize")
            if self._record_quantization_on:
                self._quantize_button.turn_on()
            else:
                self._quantize_button.turn_off()
            
    def _increment_rec_qntz_value(self):
        #Live.Base.log("SpecialProSessionComponent _increment_rec_qntz_value")
        quant_value = self._get_song().midi_recording_quantization
        quant_on = quant_value !=Rec_Q.rec_q_no_q
        if(quant_on):
            quant_idx = REC_QNTZ_RATES.index(quant_value)
            if(quant_idx<REC_QNTZ_RATES_LEN-1):
                self.song().midi_recording_quantization = REC_QNTZ_RATES[quant_idx+1]

    def _decrement_rec_qntz_value(self):
        #Live.Base.log("SpecialProSessionComponent _decrement_rec_qntz_value")        
        quant_value = self._get_song().midi_recording_quantization
        quant_on = quant_value !=Rec_Q.rec_q_no_q
        if(quant_on):
            quant_idx = REC_QNTZ_RATES.index(quant_value)
            if(quant_idx>0):
                self.song().midi_recording_quantization = REC_QNTZ_RATES[quant_idx-1]
    
    def _on_record_quantization_changed_in_live(self):
        #Live.Base.log("SpecialProSessionComponent _on_record_quantization_changed_in_live") 
        quant_value = self._get_song().midi_recording_quantization
        quant_on = quant_value !=Rec_Q.rec_q_no_q
        if quant_on:
            self._record_quantization = quant_value
        self._record_quantization_on = quant_on
        if(self._record_quantization_on):
            self._control_surface.show_message("RECORD QUANTIZATION ON: " + str(REC_QNTZ_NAMES[REC_QNTZ_RATES.index(quant_value)]))
        else: 
            self._control_surface.show_message("RECORD QUANTIZATION OFF")
        self._update_quantize_button()
        self._update_stop_track_clip_buttons()
   
    def _on_clip_trigger_quantization_changed_in_live(self):
        #Live.Base.log("SpecialProSessionComponent _on_clip_trigger_quantization_changed_in_live")         quant_value = self._get_song().clip_trigger_quantization
        if(quant_value != _Q.q_no_q):
            self._control_surface.show_message("LAUNCH QUANTIZATION ON: " + str(LAUNCH_QNTZ_NAMES[LAUNCH_QNTZ_RATES.index(quant_value)]))
        else: 
            self._control_surface.show_message("LAUNCH QUANTIZATION OFF")
        self._update_stop_track_clip_buttons() 
    
# DOUBLE button and its listener
    def _set_double_button(self, button=None):
        assert (isinstance(button, (ButtonElement, type(None))))
        if (self._double_button != button):
            if (self._double_button != None):
                self._double_button.remove_value_listener(self._double_button_value)
            self._double_button = button
            if (self._double_button != None):
                assert isinstance(button, ButtonElement)
                self._double_button.add_value_listener(self._double_button_value, identify_sender=True)

    def _double_button_value(self, value, sender):
        #Live.Base.log("SpecialProSessionComponent _double_button_value: " + str(value) + " - enabled:" + str(self.is_enabled()))
        assert (self._double_button != None)
        assert (value in range(128))
        if self.is_enabled():
            if self._shift_pressed:
                    if ((value is not 0) or (not sender.is_momentary())):
                        self._fixed_length_on = not self._fixed_length_on
                        self._display_fixed_length_info()
            else:    
                if ((value is not 0) or (not sender.is_momentary())):
                    self._control_surface.show_message("DOUBLE MIDI CLIP (SET FIXED LENGHT)?")
                    self._double_pressed = True
                else:
                    self._double_pressed = False
            self._update_double_button()
            self._update_stop_track_clip_buttons()
    
    def _update_double_button(self):
        #Live.Base.log("SpecialProSessionComponent _update_double_button")
        if self.is_enabled() and self._double_button != None:
            self._double_button.set_on_off_values("ProSession.Double")
            if self._fixed_length_on:
                self._double_button.turn_on()
            else:
                self._double_button.turn_off()
                
    def _increment_fixed_length_value(self):
        #Live.Base.log("SpecialProSessionComponent _increment_rec_qntz_value")
        if(self._fixed_length_on):
            if(self._fixed_length<MAX_FIXED_LENGTH):
                self._fixed_length += 1

    def _decrement_fixed_length_value(self):
        #Live.Base.log("SpecialProSessionComponent _decrement_rec_qntz_value")        
        if(self._fixed_length_on):
            if(self._fixed_length>0):
                self._fixed_length -= 1               
                
# DELETE button and its listener
    def _set_delete_button(self, button=None):
        assert (isinstance(button, (ButtonElement, type(None))))
        if (self._delete_button != button):
            if (self._delete_button != None):
                self._delete_button.remove_value_listener(self._delete_button_value)
            self._delete_button = button
            if (self._delete_button != None):
                assert isinstance(button, ButtonElement)
                self._delete_button.add_value_listener(self._delete_button_value, identify_sender=True)

    def _delete_button_value(self, value, sender):
        #Live.Base.log("SpecialProSessionComponent _delete_button_value: " + str(value) + " - enabled:" + str(self.is_enabled()))
        assert (self._delete_button != None)
        assert (value in range(128))
        if self.is_enabled():
            if ((value is not 0) or (not sender.is_momentary())):
                self._delete_pressed = True
                if self._shift_pressed:
                    self._control_surface.show_message("DELETE SCENE (MUTE TRACK)?")
                else:
                    self._control_surface.show_message("DELETE CLIP (MUTE TRACK)?")
            else:
                self._delete_pressed = False
            self._update_stop_track_clip_buttons()
            self._update_delete_button()
    
    def _update_delete_button(self):
        #Live.Base.log("SpecialProSessionComponent _update_delete_button")
        if self.is_enabled() and self._delete_button != None:
            self._delete_button.set_on_off_values("ProSession.Delete")
            if self._delete_pressed:
                self._delete_button.turn_on()
            else:
                self._delete_button.turn_off()

# DUPLICATE button and its listener
    def _set_duplicate_button(self, button=None):
        assert (isinstance(button, (ButtonElement, type(None))))
        if (self._duplicate_button != button):
            if (self._duplicate_button != None):
                self._duplicate_button.remove_value_listener(self._duplicate_button_value)
            self._duplicate_button = button
            if (self._duplicate_button != None):
                assert isinstance(button, ButtonElement)
                self._duplicate_button.add_value_listener(self._duplicate_button_value, identify_sender=True)

    def _duplicate_button_value(self, value, sender):
        #Live.Base.log("SpecialProSessionComponent _duplicate_button_value: " + str(value) + " - enabled:" + str(self.is_enabled()))
        assert (self._duplicate_button != None)
        assert (value in range(128))
        if self.is_enabled():
            if ((value is not 0) or (not sender.is_momentary())):
                self._duplicate_pressed = True
                if self._shift_pressed:
                    self._control_surface.show_message("DUPLICATE SCENE (SOLO TRACK)?")
                else:
                    self._control_surface.show_message("DUPLICATE CLIP (SOLO TRACK)?")
            else:
                self._duplicate_pressed = False
            self._update_stop_track_clip_buttons()
            self._update_duplicate_button()
    
    def _update_duplicate_button(self):
        #Live.Base.log("SpecialProSessionComponent _update_duplicate_button")
        if self.is_enabled() and self._duplicate_button != None:
            self._duplicate_button.set_on_off_values("ProSession.Duplicate")
            if self._duplicate_pressed:
                self._duplicate_button.turn_on()
            else:
                self._duplicate_button.turn_off()

# RECORD button and its listener
    def _set_record_button(self, button=None):
        assert (isinstance(button, (ButtonElement, type(None))))
        if (self._record_button != button):
            if (self._record_button != None):
                self._record_button.remove_value_listener(self._record_button_value)
            self._record_button = button
            if (self._record_button != None):
                assert isinstance(button, ButtonElement)
                self._record_button.add_value_listener(self._record_button_value, identify_sender=True)

    def _record_button_value(self, value, sender):
        #Live.Base.log("SpecialProSessionComponent _record_button_value: " + str(value) + " - enabled:" + str(self.is_enabled()))
        assert (self._record_button != None)
        assert (value in range(128))
        if self.is_enabled():
            if self._shift_pressed:
                if value != 0 or not self._record_button.is_momentary():
                    self._record_mode_on = not self._record_mode_on
                    self._session_record.set_record_mode(self._record_mode_on)
                    if(self._record_mode_on):
                        self._control_surface.show_message("AUTORECORD ON")
                    else:
                        self._control_surface.show_message("AUTORECORD OFF")
            else:
                if ((value is not 0) or (not sender.is_momentary())):
                    self._record_pressed = True
                    self._last_record_time = time.time()
                    self._control_surface.show_message("ARM TRACK (REC CLIP)?")
                else:
                    self._record_pressed = False
                    if (time.time() - self._last_record_time) < 0.5:
                        self._session_record._on_record_button_value()
                self._update_stop_track_clip_buttons()
            self._update_record_button()

    def _update_record_button(self):
        #Live.Base.log("SpecialProSessionComponent _update_record_button")
        if self.is_enabled():
            if self._record_mode_on:
                self._record_button.set_on_off_values("ProSession.SessionRecMode")
            else:
                self._record_button.set_on_off_values("ProSession.SessionRec")
            song = self.song()
            status = song.session_record_status
            if status == Live.Song.SessionRecordStatus.on or song.session_record:
                self._record_button.turn_on()
            else:
                self._record_button.turn_off()


# STOP TRACK button and its listener
    def _update_stop_track_clip_buttons(self):
        #Live.Base.log("SpecialProSessionComponent _update_stop_track_clip_buttons")
        if self.is_enabled():
            for index in xrange(self._num_tracks):
                self._update_stop_clips_led(index)

    def _update_stop_clips_led(self, index):
        #Live.Base.log("SpecialProSessionComponent _update_stop_clips_led index: " + str(index))
        if ((self.is_enabled()) and (self._stop_track_clip_buttons != None) and (index < len(self._stop_track_clip_buttons))):
            button = self._stop_track_clip_buttons[index]
            tracks_to_use = self.tracks_to_use()
            track_index = index + self.track_offset()
            if 0 <= track_index < len(tracks_to_use):
                track = tracks_to_use[track_index]
                if(self._quantize_pressed):
                    #Live.Base.log("SpecialProSessionComponent _update_rec_qntz_leds")
                    self._update_rec_qntz_leds(index)
                elif(self._double_pressed):
                    #Live.Base.log("SpecialProSessionComponent _update_fixed_lenght_leds")
                    self._update_fixed_lenght_leds(index)            
                elif(self._shift_pressed):
                    pass
                    #Live.Base.log("SpecialProSessionComponent _update_clip_trigger_leds")
                    self._update_clip_trigger_leds(index)            
                elif(self._record_pressed):
                    #Live.Base.log("SpecialProSessionComponent _record_pressed")
                    if track.arm:
                        button.send_value("Recording.On")
                    else:
                        button.send_value("Recording.Off")
                elif(self._duplicate_pressed):
                    #Live.Base.log("SpecialProSessionComponent _duplicate_pressed")
                    if track.solo:
                        button.send_value("Device.Bank.On")
                    else:
                        button.send_value("Device.Bank.Off")    
                elif(self._delete_pressed):
                    #Live.Base.log("SpecialProSessionComponent _delete_pressed")
                    if track.mute:
                        button.send_value("TrackController.Mute.Off")
                    else:
                        button.send_value("TrackController.Mute.On")  
                else:
                    #Live.Base.log("SpecialProSessionComponent firedSolt")
                    if track.fired_slot_index == -2:
                        button.send_value(self._stop_clip_triggered_value)
                    elif track.playing_slot_index >= 0:
                        button.send_value(self._stop_clip_value)
                    else:
                        button.turn_off()
            else:
                button.send_value(4)
         
    def _update_clip_trigger_leds(self, index):
        #Live.Base.log("SpecialProSessionComponent _update_clip_trigger_leds: " + str(index))
        button = self._stop_track_clip_buttons[index]
        if(index==0):
            if(self._get_song().clip_trigger_quantization == _Q.q_no_q):
                button.send_value("LaunchQuant.On")
            else:
                button.send_value("LaunchQuant.Off")  
        elif(index==1):
            if(self._get_song().clip_trigger_quantization != _Q.q_no_q):
                button.send_value("ProSession.On")
            else:
                button.send_value("ProSession.Off")
        elif(index==2):
            if(self._get_song().clip_trigger_quantization != _Q.q_thirtytwoth):
                button.send_value("ProSession.On")
            else:
                button.send_value("ProSession.Off")
        else:
            quant_value = self._get_song().clip_trigger_quantization
                
            if(quant_value in LAUNCH_QNTZ_FIXED_RATES):
                quant_idx = LAUNCH_QNTZ_FIXED_RATES.index(quant_value)
                #LaunchQuant values 2 Bars, 1 bar, 1/4, 1/8, 1/16
                if((index-3) == quant_idx):
                    button.send_value("LaunchQuant.Value.On")
                else:
                    button.send_value("LaunchQuant.Value.Off")
            else:
                button.send_value("LaunchQuant.Value.Off")            
               
    def _update_rec_qntz_leds(self, index):
        #Live.Base.log("SpecialProSessionComponent _update_rec_qntz_leds: " + str(index))
        button = self._stop_track_clip_buttons[index]
        if(index==0):
            if(self._record_quantization_on):
                button.send_value("RecQuant.On")
            else:
                button.send_value("RecQuant.Off")  
        elif(index==1 and (self._get_song().midi_recording_quantization != Rec_Q.rec_q_quarter)):
            if(self._record_quantization_on):
                button.send_value("ProSession.On")
            else:
                button.send_value("ProSession.Off")
        elif(index==2 and (self._get_song().midi_recording_quantization!= Rec_Q.rec_q_thirtysecond)):
            if(self._record_quantization_on):
                button.send_value("ProSession.On")
            else:
                button.send_value("ProSession.Off")
        else:
            if(self._record_quantization_on):
                quant_value = self._get_song().midi_recording_quantization
                sendValue = "RecQuant.Value.On"
            else:
                quant_value = self._record_quantization    
                sendValue = "RecQuant.Value.Idle"
                
            if(quant_value in REC_QNTZ_FIXED_RATES):
                quant_idx = REC_QNTZ_FIXED_RATES.index(quant_value)
                #RecQuant values 1/4, 1/8, 1/8+t, 1/16, 1/16+t
                if((index-3) == quant_idx):
                    button.send_value(sendValue)
                else:
                    button.send_value("RecQuant.Value.Off")
            else:
                button.send_value("RecQuant.Value.Off")                
                    
    def _update_fixed_lenght_leds(self, index):
        #Live.Base.log("SpecialProSessionComponent _update_fixed_lenght_leds: " + str(index))
        button = self._stop_track_clip_buttons[index]
        if(index==0):
            if(self._fixed_length_on):
                button.send_value("FixedLenght.On")
            else:
                button.send_value("FixedLenght.Off")  
        elif(index==1):
            if(self._fixed_length == 0):
                button.send_value("ProSession.Off")
            else:
                button.send_value("ProSession.On")
        elif(index==2):
            if(self._fixed_length == 31):
                button.send_value("ProSession.Off")
            else:
                button.send_value("ProSession.On")
        else:
            if(self._fixed_length in FIXED_LENGTH_VALUES):
                fl_idx = FIXED_LENGTH_VALUES.index(self._fixed_length)
                #Fixed Lenght values 1, 2, 4, 8, 16
                if((index-3) == fl_idx):
                    if(self._fixed_length_on):
                        button.send_value("FixedLenght.Value.On")
                    else:
                        button.send_value("FixedLenght.Value.Idle")
                else:
                    button.send_value("FixedLenght.Value.Off")    
            else:
                button.send_value("FixedLenght.Value.Off")                          

    @subject_slot_group('value')
    def _on_stop_track_value(self, value, button):
        #Live.Base.log("SpecialProSessionComponent _on_stop_track_value")
        if self.is_enabled():
            if(self._quantize_pressed):
                self._set_rec_qntz_value(value, button)
            elif(self._double_pressed):
                self._set_fixed_lenght_value(value, button)
            elif(self._shift_pressed):
                self._set_launch_qntz_value(value, button)               
            elif self._record_pressed:
                self._do_arm_track(value, button)                
            elif self._duplicate_pressed:
                self._do_solo_track(value, button)
            elif self._delete_pressed:
                self._do_mute_track(value, button)
            else:
                super(SpecialProSessionComponent, self)._on_stop_track_value(value, button)
            self._update_stop_track_clip_buttons()
            
    def _set_fixed_lenght_value(self, value, button):        
        if value is not 0 or not button.is_momentary():
            index = list(self._stop_track_clip_buttons).index(button)
            if(index==0):
                self._fixed_length_on = not self._fixed_length_on
            elif(index==1):
                self._decrement_fixed_length_value()
            elif(index==2):
                self._increment_fixed_length_value()
            else:
                self._fixed_length = FIXED_LENGTH_VALUES[index-3]   
            self._display_fixed_length_info()                       
                
    def _set_rec_qntz_value(self, value, button):        
        if value is not 0 or not button.is_momentary():
            index = list(self._stop_track_clip_buttons).index(button)
            if(index==0):
                self._record_quantization_on = not self._record_quantization_on
                self.song().midi_recording_quantization = self._record_quantization if self._record_quantization_on else Rec_Q.rec_q_no_q    
            elif(index==1):
                self._decrement_rec_qntz_value()
            elif(index==2):
                self._increment_rec_qntz_value()
            else:
                self.song().midi_recording_quantization = REC_QNTZ_FIXED_RATES[index-3]   
                
    def _set_launch_qntz_value(self, value, button):        
        if value is not 0 or not button.is_momentary():
            index = list(self._stop_track_clip_buttons).index(button)
            if(index==0):
                self.song().clip_trigger_quantization = _Q.q_no_q    
            elif(index==1):
                self._decrement_launch_qntz_value()
            elif(index==2):
                self._increment_launch_qntz_value()
            else:
                self.song().clip_trigger_quantization = LAUNCH_QNTZ_FIXED_RATES[index-3]                   
                                               
            
    def _do_arm_track(self, value, button):        
        if value is not 0 or not button.is_momentary():
            tracks = self.tracks_to_use()
            track_index = list(self._stop_track_clip_buttons).index(button) + self.track_offset()
            if in_range(track_index, 0, len(tracks)) and tracks[track_index] in self.song().tracks:
                track = tracks[track_index]                    
                if track.arm:
                    track.arm = False
                elif track.can_be_armed:
                    if self._get_song().exclusive_arm:
                        for t in self._get_song().tracks:
                            if t.can_be_armed and t.arm:
                                t.arm = False
        
                    track.arm = True
                    if self._get_song().view.selected_track != track:
                        self._get_song().view.selected_track = track         
            
    def _do_mute_track(self, value, button):        
        if value is not 0 or not button.is_momentary():
            tracks = self.tracks_to_use()
            track_index = list(self._stop_track_clip_buttons).index(button) + self.track_offset()
            if in_range(track_index, 0, len(tracks)) and tracks[track_index] in self.song().tracks:
                track = tracks[track_index]                    
                track.mute = not track.mute  
                
    def _do_solo_track(self, value, button):        
        if value is not 0 or not button.is_momentary():
            tracks = self.tracks_to_use()
            track_index = list(self._stop_track_clip_buttons).index(button) + self.track_offset()
            if in_range(track_index, 0, len(tracks)) and tracks[track_index] in self.song().tracks:
                track = tracks[track_index]                    
                track.solo = not track.solo              

    def set_osd(self, osd):
        self._osd = osd

    def _update_OSD(self):
        if self._osd != None:
            self._osd.mode = "Session"
            for i in range(self._num_tracks):
                self._osd.attribute_names[i] = " "
                self._osd.attributes[i] = " "

            tracks = self.tracks_to_use()
            idx = 0
            for i in range(len(tracks)):
                if idx < self._num_tracks and len(tracks) > i + self._track_offset:
                    track = tracks[i + self._track_offset]
                    if track != None:
                        self._osd.attribute_names[idx] = str(track.name)
                    else:
                        self._osd.attribute_names[idx] = " "
                    self._osd.attributes[idx] = " "
                idx += 1

            self._osd.info[0] = " "
            self._osd.info[1] = " "
            self._osd.update()

    def link_with_track_offset(self, track_offset):
        assert (track_offset >= 0)
        if self._is_linked():
            self._unlink()
        self.set_offsets(track_offset, 0)
        self._link()

    def unlink(self):
        if self._is_linked():
            self._unlink()

    def update(self):
        #Live.Base.log("SpecialProSessionComponent update")
        SessionComponent.update(self)
        self._update_shift_button()
        self._update_undo_button()
        self._update_click_button()
        self._update_delete_button()
        self._update_quantize_button()
        self._update_duplicate_button()
        self._update_double_button()
        self._update_record_button()
        self._update_stop_track_clip_buttons()
            
        if self._main_selector._main_mode_index == 0:
            self._update_OSD()

    def set_enabled(self, enabled):
        #Live.Base.log("SpecialProSessionComponent set_enabled: " + str(enabled))
        SessionComponent.set_enabled(self, enabled)
        self._session_record.set_enabled(enabled)
        if self._main_selector._main_mode_index == 0:
            self._update_OSD()

    def _reassign_tracks(self):
        SessionComponent._reassign_tracks(self)
        if self._main_selector._main_mode_index == 0:
            self._update_OSD()

    def _get_fixed_length(self):
        """ Returns the fixed length to use for recording or creating clips. """
        return 4.0 / self.song().signature_denominator * self.song().signature_numerator * (self._fixed_length + 1)

    def _display_fixed_length_info(self):
        """ Displays the current fixed recording length/state in the status bar. """
        if self.is_enabled():
            if self._fixed_length_on:
                tag = ' Bar'
                if self._fixed_length > 0:
                    tag = ' Bars'
                self._control_surface.show_message('FIXED LENGTH:  ' + str(int(self._get_fixed_length() / self.song().signature_denominator)) + tag)
            else:
                self._control_surface.show_message('FIXED LENGTH:  OFF')
