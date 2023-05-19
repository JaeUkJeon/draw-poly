from vtkmodules.vtkInteractionStyle import vtkInteractorStyleImage
from vtkmodules.vtkRenderingCore import vtkPointPicker


class MouseInteractorStyle2(vtkInteractorStyleImage):
    def __init__(self, select_callback, change_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.AddObserver('LeftButtonPressEvent', self.left_button_press_event)
        # self.AddObserver('LeftButtonReleaseEvent', self.left_button_release_event)
        self.AddObserver('RightButtonPressEvent', self.right_button_press_event)
        # self.AddObserver('MouseMoveEvent', self.mouse_move_event)
        self.AddObserver('MouseWheelForwardEvent', self.scroll_event)
        self.AddObserver('MouseWheelBackwardEvent', self.scroll_event)
        # self.AddObserver('KeyPressEvent', self.key_press_event)
        self.AddObserver('CharEvent', self.char_event)
        self.callback_select = select_callback
        self.callback_change = change_callback

    def pick_point(self):
        # Get the location of the click (in window coordinates)
        pos = self.GetInteractor().GetEventPosition()

        picker = vtkPointPicker()
        picker.SetTolerance(0.01)

        # Pick from this location.
        picker.Pick(pos[0], pos[1], 0, self.GetDefaultRenderer())

        return picker.GetPointId(), picker.GetActor()

    def scroll_event(self, obj, event):
        scale = self.GetDefaultRenderer().GetActiveCamera().GetParallelScale()
        if event == 'MouseWheelForwardEvent':
            if scale < 2:
                return
            self.OnMouseWheelForward()
        elif event == 'MouseWheelBackwardEvent':
            if scale > 20:
                return
            self.OnMouseWheelBackward()

    def right_button_press_event(self, obj, event):
        if self.GetInteractor().GetShiftKey() or self.GetInteractor().GetControlKey():
            return
        point_id, actor = self.pick_point()

        if point_id != -1:
            self.callback_change(point_id)

        # self.OnRightButtonDown()

    def left_button_press_event(self, obj, event):
        if self.GetInteractor().GetShiftKey():
            return

        remove_mode = False
        if self.GetInteractor().GetControlKey():
            remove_mode = True

        # self.mouse_clicked = True

        point_id, actor = self.pick_point()

        if point_id != -1:

            self.callback_select(point_id, remove_mode)
        # Forward events
        # self.OnLeftButtonDown()

    def char_event(self, obj, event):
        return
